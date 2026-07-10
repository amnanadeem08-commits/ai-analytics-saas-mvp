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
from backend.models.memory_models import MemoryType
from backend.models.workflow_models import WorkflowDefinition, WorkflowStatus
from backend.services.agent_service import (
    ensure_builtin_agents,
    execute_reasoning_loop,
    get_agent,
)
from backend.services.llm_service import reset_llm_provider
from backend.services.memory_service import (
    memory_summary,
    reset_memory_store,
    search_memory,
    store_memory,
)
from backend.services.planning_service import clear_plans
from backend.services.tool_registry_service import ensure_builtin_tools
from backend.services.workflow_engine_service import (
    CTX_MEMORY_CONTEXT,
    CTX_MEMORY_IDS,
    CTX_RAW_INSIGHTS,
    execute_workflow,
    make_memory_context_stage,
    make_planner_stage,
)


def _sample_insight() -> UniversalAIInsight:
    return UniversalAIInsight(
        id="insight_memory",
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
    reset_memory_store()


def test_agent_uses_retrieved_context_and_stores_memory():
    agent = get_agent("data_analyst_agent")
    assert agent is not None
    store_memory(
        agent_name=agent.agent_name,
        content={
            "task": "Analyze customer revenue decline",
            "tool_calls": ["data_profiling", "kpi_detection"],
            "summary": "Prior analysis highlighted North weakness",
        },
        memory_type=MemoryType.KNOWLEDGE_MEMORY,
        source="business_insight",
        relevance_score=0.9,
    )

    execution = execute_reasoning_loop(
        "Analyze customer revenue decline",
        context={"raw_insights": [_sample_insight()], "dataset_id": "sales_q1"},
        multi_agent=True,
        use_memory=True,
        store_memory=True,
    )
    assert execution.status == AgentStatus.completed
    assert execution.metadata.get("memory_enabled") is True
    assert execution.metadata.get("memory_count", 0) >= 1
    assert execution.result is not None
    assert execution.result.outputs["memory"]["retrieved_ids"]
    assert execution.result.outputs["memory"]["stored_ids"]

    stored = search_memory(
        "Analyze customer revenue decline",
        agent_name=agent.agent_name,
        limit=10,
    )
    assert any(m.source == "task_summary" for m in stored.memories)
    assert memory_summary(agent.agent_name)["total"] >= 2


def test_workflow_memory_then_planner_stages():
    agent = get_agent("data_analyst_agent")
    assert agent is not None
    store_memory(
        agent_name=agent.agent_name,
        content={
            "task": "Analyze customer revenue decline",
            "tool_calls": ["data_profiling"],
            "summary": "Cached profiling outcome",
        },
        memory_type=MemoryType.EXECUTION_HISTORY,
        source="tool_result",
        relevance_score=0.8,
    )

    now = utc_now_iso()
    definition = WorkflowDefinition(
        workflow_id=f"wf_mem_{now.replace(':', '')}",
        workflow_name="Memory Planner Pipeline",
        stages=[
            make_memory_context_stage(
                stage_id="memory",
                task="Analyze customer revenue decline",
                agent_name=agent.agent_name,
                execution_order=10,
            ),
            make_planner_stage(
                stage_id="plan",
                task="Analyze customer revenue decline",
                dependencies=["memory"],
                execution_order=20,
                multi_agent=True,
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
    assert CTX_MEMORY_CONTEXT in context
    assert CTX_MEMORY_IDS in context
    assert context[CTX_MEMORY_IDS]
    assert context.get("memory_snippets")
