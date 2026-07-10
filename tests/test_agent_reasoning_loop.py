from __future__ import annotations

from backend.models.agent_models import AgentStatus
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
from backend.models.workflow_models import WorkflowDefinition, WorkflowStatus
from backend.services.agent_service import (
    analyze_task,
    create_execution_plan,
    ensure_builtin_agents,
    execute_reasoning_loop,
)
from backend.services.llm_service import reset_llm_provider
from backend.services.planning_service import clear_plans
from backend.services.tool_registry_service import ensure_builtin_tools
from backend.services.workflow_engine_service import (
    CTX_AGENT_PLAN,
    CTX_PLAN_RESULT,
    CTX_RAW_INSIGHTS,
    execute_workflow,
    make_planner_stage,
)


def _sample_insight() -> UniversalAIInsight:
    return UniversalAIInsight(
        id="insight_plan",
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


def setup_function():
    reset_llm_provider()
    ensure_builtin_tools(reset=True)
    ensure_builtin_agents(reset=True)
    clear_plans()


def test_analyze_task_and_create_plan():
    analysis = analyze_task("Analyze customer revenue decline")
    assert analysis.task
    assert analysis.understanding
    assert analysis.suggested_tools

    plan = create_execution_plan(
        "Analyze customer revenue decline",
        multi_agent=True,
    )
    assert len(plan.steps) >= 3
    assert plan.task_understanding


def test_agent_executes_multi_step_reasoning_loop():
    execution = execute_reasoning_loop(
        "Analyze customer revenue decline",
        context={"raw_insights": [_sample_insight()], "dataset_id": "sales_q1"},
        multi_agent=True,
    )
    assert execution.status in {AgentStatus.completed, AgentStatus.failed}
    assert execution.result is not None
    assert execution.metadata.get("reasoning_loop") is True
    assert "plan" in execution.result.outputs
    assert execution.result.tool_calls
    # Should have progressed through multiple tools
    assert len(execution.result.tool_calls) >= 2
    plan_result = execution.result.outputs["plan_result"]
    completed = plan_result.get("completed_steps") or plan_result.get("final_result", {}).get("completed_count", 0)
    if isinstance(completed, list):
        assert len(completed) >= 1
    else:
        assert int(completed) >= 1


def test_failed_tool_handled_in_reasoning_loop():
    execution = execute_reasoning_loop(
        "Validate insight quality",
        agent_id="validation_agent",
        context={},  # missing insight → validation fails
        multi_agent=False,
        stop_on_error=True,
    )
    assert execution.status == AgentStatus.failed
    assert execution.error_message or (
        execution.result and execution.result.error_message
    )


def test_workflow_executes_planned_agent_task():
    now = utc_now_iso()
    definition = WorkflowDefinition(
        workflow_id=f"wf_plan_{now.replace(':', '')}",
        workflow_name="Planner Pipeline",
        stages=[
            make_planner_stage(
                stage_id="plan_and_run",
                task="Analyze customer revenue decline",
                execution_order=10,
                multi_agent=True,
            )
        ],
        stop_on_error=True,
        created_at=now,
        metadata={},
    )
    execution, context = execute_workflow(
        definition,
        initial_context={CTX_RAW_INSIGHTS: [_sample_insight()]},
        dataset_id="sales_q1",
        domain="Sales",
    )
    assert execution.status == WorkflowStatus.completed
    assert CTX_AGENT_PLAN in context
    assert CTX_PLAN_RESULT in context
    plan_result = context[CTX_PLAN_RESULT]
    completed = plan_result.get("completed_steps") or []
    assert len(completed) >= 1 or plan_result.get("final_result", {}).get("completed_count", 0) >= 1
