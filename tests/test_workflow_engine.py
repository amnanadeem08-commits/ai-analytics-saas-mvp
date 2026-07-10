from __future__ import annotations

from backend.models.ai_insight_models import (
    AI_INSIGHT_SCHEMA_VERSION,
    DataQualityScore,
    EffortLevel,
    InsightMetadata,
    InsightPriority,
    InsightProvenance,
    RecommendedAction,
    RiskLevel,
    SupportingEvidenceItem,
    UniversalAIInsight,
    UrgencyLevel,
    ValidationStatus,
    utc_now_iso,
)
from backend.models.workflow_models import (
    WORKFLOW_FUTURE_EXTENSION_KEYS,
    StageRunStatus,
    WorkflowStageDefinition,
    WorkflowStatus,
)
from backend.services.workflow_engine_service import (
    CTX_BUNDLE,
    CTX_DECISIONS,
    CTX_GOVERNANCE,
    CTX_INSIGHTS,
    CTX_PREDICTIONS,
    CTX_RAW_INSIGHTS,
    CTX_VALIDATIONS,
    DEFAULT_STAGE_RUNNERS,
    build_workflow_definition,
    execute_workflow,
    find_stage_result,
    get_stage_runner,
    list_execution_logs,
    validate_workflow_definition,
    workflow_execution_graph,
    workflow_statistics,
    workflow_summary,
)


def _sample_insight(**overrides) -> UniversalAIInsight:
    insight = UniversalAIInsight(
        id="insight_workflow",
        schema_version=AI_INSIGHT_SCHEMA_VERSION,
        title="Revenue decline in North",
        summary="North region revenue declined versus prior period.",
        insight="North region revenue declined versus prior period.",
        reason="North segment totals are consistently lower than East.",
        supporting_evidence=[
            SupportingEvidenceItem(
                label="North revenue total",
                value=42000,
                evidence_type="metric",
                source="validated_kpi",
                confidence_score=0.9,
            )
        ],
        affected_metrics=["revenue"],
        business_impact="Lower revenue concentration increases downside risk.",
        expected_outcome="Stabilize North performance.",
        risk_level=RiskLevel.high,
        priority=InsightPriority.high,
        recommended_actions=[
            RecommendedAction(
                action="Investigate North region sales execution.",
                rationale="North is the weakest validated segment.",
                expected_outcome="Identify operational drivers.",
                estimated_effort=EffortLevel.medium,
                urgency=UrgencyLevel.high,
            )
        ],
        data_confidence=0.88,
        reasoning_confidence=0.84,
        overall_confidence=0.86,
        confidence_reason="Validated KPI and segment evidence.",
        assumptions=["Revenue field is complete."],
        limitations=["No causal experiment has been run."],
        related_kpis=["total_revenue"],
        domain="Sales",
        generated_by=InsightProvenance(engine="test", provider="platform", engine_version="1.0.0"),
        generated_at=utc_now_iso(),
        validation_status=ValidationStatus.pending,
        data_quality_score=DataQualityScore(
            score=90.0, grade="A", completeness_pct=97.0, dimensions={"freshness": "good"}
        ),
        metadata=InsightMetadata(custom={"dataset_id": "sales_q1"}),
    )
    return insight.model_copy(update=overrides)


def test_workflow_definition_from_orchestrator():
    definition = build_workflow_definition()
    assert len(definition.stages) == 18
    assert definition.stages[0].stage_id == "insights"
    assert definition.stages[-1].stage_id == "governance"
    assert validate_workflow_definition(definition)["valid"] is True

    graph = workflow_execution_graph(definition)
    assert graph["ordered_stage_ids"][0] == "insights"
    assert graph["ordered_stage_ids"][-1] == "governance"
    assert any(e["from"] == "insights" and e["to"] == "validation" for e in graph["edges"])


def test_partial_workflow_definition():
    definition = build_workflow_definition(
        stage_ids=["insights", "validation", "decision"],
        workflow_name="Core Intelligence",
    )
    assert [s.stage_id for s in definition.stages] == ["insights", "validation", "decision"]
    # decision depends on validation which is present; optional missing deps not applied
    result = validate_workflow_definition(definition)
    assert result["valid"] is True


def test_stage_runner_interface():
    for stage_id in [
        "insights",
        "validation",
        "decision",
        "bundle",
        "prediction",
        "governance",
        "agent_runner",
        "planner_runner",
        "memory_context_runner",
        "rag_context_runner",
    ]:
        assert get_stage_runner(stage_id) is not None
    assert len(DEFAULT_STAGE_RUNNERS) == 24
    assert get_stage_runner("missing") is None


def test_full_pipeline_execution():
    definition = build_workflow_definition()
    insight = _sample_insight()
    execution, context = execute_workflow(
        definition,
        initial_context={CTX_RAW_INSIGHTS: [insight]},
        dataset_id="sales_q1",
        domain="Sales",
    )
    assert execution.status == WorkflowStatus.completed
    assert CTX_INSIGHTS in context
    assert CTX_VALIDATIONS in context
    assert CTX_DECISIONS in context
    assert CTX_BUNDLE in context
    assert CTX_PREDICTIONS in context
    assert CTX_GOVERNANCE in context

    validation_result = find_stage_result(execution, "validation")
    assert validation_result is not None
    assert validation_result.status == StageRunStatus.completed
    assert validation_result.output_keys

    gov = find_stage_result(execution, "governance")
    assert gov is not None
    assert gov.status == StageRunStatus.completed

    stats = workflow_statistics(execution)
    assert stats.completed_stages == 18
    assert stats.failed_stages == 0
    assert stats.log_count > 0

    summary = workflow_summary(execution)
    assert summary.status == "completed"
    assert summary.completed_stages == 18
    assert summary.context_key_count >= 10


def test_core_intelligence_subset_execution():
    definition = build_workflow_definition(
        stage_ids=["insights", "validation", "decision", "root_cause", "executive_reasoning", "storyboard", "bundle"],
    )
    execution, context = execute_workflow(
        definition,
        initial_context={CTX_RAW_INSIGHTS: [_sample_insight()]},
        dataset_id="sales_q1",
        domain="Sales",
    )
    assert execution.status == WorkflowStatus.completed
    assert CTX_BUNDLE in context
    assert find_stage_result(execution, "prediction") is None


def test_error_handling_and_stop_on_error():
    definition = build_workflow_definition(
        stage_ids=["insights", "validation", "decision"],
        stop_on_error=True,
    )

    def boom(context, stage, *, dataset_id=None, domain=None):
        raise RuntimeError("forced failure")

    execution, context = execute_workflow(
        definition,
        initial_context={CTX_RAW_INSIGHTS: [_sample_insight()]},
        runners={"validation": boom},
        dataset_id="sales_q1",
    )
    assert execution.status in {WorkflowStatus.failed, WorkflowStatus.partial}
    assert find_stage_result(execution, "validation").status == StageRunStatus.failed
    decision = find_stage_result(execution, "decision")
    assert decision is not None
    assert decision.status in {StageRunStatus.skipped, StageRunStatus.blocked}
    assert execution.errors
    assert any(e.stage_id == "validation" for e in execution.errors)
    assert CTX_VALIDATIONS not in context


def test_continue_on_error():
    definition = build_workflow_definition(
        stage_ids=["insights", "validation", "forecast_adapter"],
        stop_on_error=False,
    )

    def boom(context, stage, *, dataset_id=None, domain=None):
        raise RuntimeError("forced failure")

    # validation fails; forecast_adapter has no dep on validation in this subset —
    # rebuild with connected stages: insights -> validation, and a parallel-ish skip path
    # Use insights + failing custom middle + adapter that only needs nothing from validation
    stages = [
        WorkflowStageDefinition(
            stage_id="insights",
            stage_name="Insights",
            dependencies=[],
            execution_order=10,
            runner_key="insights",
        ),
        WorkflowStageDefinition(
            stage_id="validation",
            stage_name="Validation",
            dependencies=["insights"],
            execution_order=20,
            runner_key="validation",
        ),
        WorkflowStageDefinition(
            stage_id="forecast_adapter",
            stage_name="Forecast Adapter",
            dependencies=["insights"],  # still runnable if validation failed when stop_on_error=False
            execution_order=30,
            runner_key="forecast_adapter",
        ),
    ]
    definition.stages = stages
    definition.stop_on_error = False

    execution, context = execute_workflow(
        definition,
        initial_context={CTX_RAW_INSIGHTS: [_sample_insight()]},
        runners={"validation": boom},
        stop_on_error=False,
        dataset_id="sales_q1",
    )
    assert find_stage_result(execution, "validation").status == StageRunStatus.failed
    assert find_stage_result(execution, "forecast_adapter").status == StageRunStatus.completed
    assert execution.status == WorkflowStatus.partial
    assert "forecast_adapters" in context


def test_execution_logs_and_lifecycle():
    definition = build_workflow_definition(stage_ids=["insights", "validation"])
    execution, _ = execute_workflow(
        definition,
        initial_context={CTX_RAW_INSIGHTS: [_sample_insight()]},
        dataset_id="sales_q1",
    )
    all_logs = list_execution_logs(execution)
    assert len(all_logs) >= 3
    stage_logs = list_execution_logs(execution, stage_id="validation")
    assert stage_logs
    assert all(l.stage_id == "validation" for l in stage_logs)

    for stage_id in ("insights", "validation"):
        result = find_stage_result(execution, stage_id)
        assert result is not None
        assert result.status == StageRunStatus.completed
        assert result.started_at
        assert result.finished_at
        assert result.duration_ms is not None


def test_missing_input_fails_stage():
    # Validation alone cannot run — required dependency is absent from the definition.
    blocked_def = build_workflow_definition(stage_ids=["validation"])
    blocked_exec, _ = execute_workflow(blocked_def, initial_context={})
    blocked = find_stage_result(blocked_exec, "validation")
    assert blocked is not None
    assert blocked.status == StageRunStatus.blocked
    assert blocked_exec.errors

    # Dependencies satisfied, but insights never placed in context → runtime failure.
    def no_insights(context, stage, *, dataset_id=None, domain=None):
        return {}

    runtime_def = build_workflow_definition(stage_ids=["insights", "validation"])
    runtime_exec, _ = execute_workflow(
        runtime_def,
        initial_context={},
        runners={"insights": no_insights},
    )
    failed = find_stage_result(runtime_exec, "validation")
    assert failed is not None
    assert failed.status == StageRunStatus.failed
    assert any(e.stage_id == "validation" for e in runtime_exec.errors)


def test_future_extension_buckets():
    definition = build_workflow_definition(stage_ids=["insights"])
    for key in WORKFLOW_FUTURE_EXTENSION_KEYS:
        assert key in definition.metadata["future_extensions"]
        assert definition.metadata["future_extensions"][key] == {}

    execution, _ = execute_workflow(
        definition,
        initial_context={CTX_RAW_INSIGHTS: [_sample_insight()]},
    )
    for key in WORKFLOW_FUTURE_EXTENSION_KEYS:
        assert key in execution.metadata["future_extensions"]
        assert execution.metadata["future_extensions"][key] == {}


def test_immutability():
    definition = build_workflow_definition(stage_ids=["insights", "validation"])
    snap_def = definition.model_dump()
    execution, context = execute_workflow(
        definition,
        initial_context={CTX_RAW_INSIGHTS: [_sample_insight()]},
        dataset_id="sales_q1",
    )
    snap_exec = execution.model_dump()

    found = find_stage_result(execution, "insights")
    assert found is not None
    found.status = StageRunStatus.failed
    logs = list_execution_logs(execution)
    logs[0].message = "mutated"
    stats = workflow_statistics(execution)
    assert stats.completed_stages >= 1
    workflow_summary(execution)

    # Mutating returned context object should not rewrite execution record keys list identity check
    context["mutated"] = True
    assert definition.model_dump() == snap_def
    assert execution.model_dump() == snap_exec
