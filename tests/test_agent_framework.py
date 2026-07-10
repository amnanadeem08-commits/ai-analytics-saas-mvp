from __future__ import annotations

from backend.models.agent_models import AgentDefinition, AgentRole, AgentStatus
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
    agent_summary,
    assign_task,
    build_agent_registry,
    ensure_builtin_agents,
    execute_agent,
    get_agent,
    get_agent_status,
    list_agents,
    register_agent,
    update_agent_status,
    validate_agent_definition,
)
from backend.services.llm_service import reset_llm_provider
from backend.services.tool_registry_service import ensure_builtin_tools
from backend.services.workflow_engine_service import (
    CTX_AGENT_RESULTS,
    CTX_RAW_INSIGHTS,
    execute_workflow,
    make_agent_stage,
)


def _sample_insight() -> UniversalAIInsight:
    return UniversalAIInsight(
        id="insight_agent",
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


def test_agent_creation_and_listing():
    registry = build_agent_registry(reset=True)
    ids = {a.agent_id for a in registry.agents}
    assert {
        "data_analyst_agent",
        "insight_agent",
        "validation_agent",
        "reporting_agent",
    }.issubset(ids)
    assert get_agent("data_analyst_agent") is not None
    assert len(list_agents(role=AgentRole.validation)) == 1
    assert validate_agent_definition(get_agent("insight_agent"))["valid"] is True
    summary = agent_summary()
    assert summary["agent_count"] == 4


def test_agent_lifecycle_and_tool_calling():
    task = assign_task(
        "validation_agent",
        objective="Validate the insight",
        payload={},
    )
    assert get_agent_status("validation_agent") == AgentStatus.assigned

    execution = execute_agent(
        "validation_agent",
        task,
        context={"raw_insights": [_sample_insight()]},
    )
    assert execution.status == AgentStatus.completed
    assert execution.result is not None
    assert "validation" in execution.result.tool_calls
    assert execution.result.context_updates.get("agent_validated_insight") is not None
    assert get_agent_status("validation_agent") == AgentStatus.completed
    assert any("Tool validation" in line for line in execution.logs)


def test_data_analyst_and_reporting_agents():
    analyst = execute_agent(
        "data_analyst_agent",
        objective="Profile dataset context",
        context={"dataset_id": "sales_q1"},
    )
    assert analyst.status == AgentStatus.completed
    assert analyst.result is not None
    assert set(analyst.result.tool_calls) & {
        "data_profiling",
        "kpi_detection",
        "visualization_recommendation",
    }

    reporting = execute_agent(
        "reporting_agent",
        objective="Prepare executive outputs",
        context={"dataset_id": "sales_q1"},
        payload={"tools": ["governance_validation"]},
    )
    assert reporting.status == AgentStatus.completed
    assert "governance_validation" in reporting.result.tool_calls
    assert reporting.result.context_updates.get("governance") is not None


def test_agent_failure_handling():
    register_agent(
        AgentDefinition(
            agent_id="broken_agent",
            agent_name="Broken",
            role=AgentRole.custom,
            allowed_tools=["validation"],
            max_tool_calls=1,
        )
    )
    execution = execute_agent(
        "broken_agent",
        objective="Validate without insight",
        context={},
        payload={"fail_fast": True, "tools": ["validation"]},
    )
    assert execution.status == AgentStatus.failed
    assert execution.error_message
    assert get_agent_status("broken_agent") == AgentStatus.failed


def test_workflow_calls_agents_and_merges_context():
    now = utc_now_iso()
    definition = WorkflowDefinition(
        workflow_id=f"wf_agents_{now.replace(':', '')}",
        workflow_name="Agent Pipeline",
        stages=[
            make_agent_stage(
                stage_id="analyze",
                agent_ids="data_analyst_agent",
                execution_order=10,
                objective="Analyze available context",
            ),
            make_agent_stage(
                stage_id="validate_agent_stage",
                agent_ids="validation_agent",
                dependencies=["analyze"],
                execution_order=20,
                objective="Validate insight quality",
            ),
            make_agent_stage(
                stage_id="report",
                agent_ids="reporting_agent",
                dependencies=["validate_agent_stage"],
                execution_order=30,
                objective="Prepare governance output",
                metadata={"payloads": {"reporting_agent": {"tools": ["governance_validation"]}}},
            ),
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
    assert CTX_AGENT_RESULTS in context
    assert "validation_agent" in context[CTX_AGENT_RESULTS]
    assert context.get("governance") is not None or context.get("agent_validated_insight") is not None
    assert len(context.get("agent_executions") or []) == 3


def test_update_status_and_summary():
    update_agent_status("insight_agent", AgentStatus.running)
    assert get_agent_status("insight_agent") == AgentStatus.running
    summary = agent_summary("insight_agent")
    assert summary["found"] is True
    assert summary["role"] == "insight"
