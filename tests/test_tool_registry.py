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
from backend.models.tool_models import ToolDefinition, ToolExecutionStatus, ToolRequest
from backend.services.tool_registry_service import (
    clear_tool_registry,
    ensure_builtin_tools,
    execute_tool,
    get_tool,
    list_tools,
    register_tool,
    validate_tool,
)


def _sample_insight() -> UniversalAIInsight:
    return UniversalAIInsight(
        id="insight_tool",
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


def test_tool_registration_and_listing():
    ensure_builtin_tools(reset=True)
    tools = list_tools()
    ids = {t.tool_id for t in tools}
    assert {
        "data_profiling",
        "kpi_detection",
        "visualization_recommendation",
        "insight_generation",
        "validation",
        "forecast_explanation",
        "governance_validation",
    }.issubset(ids)
    assert get_tool("validation") is not None
    assert validate_tool(get_tool("validation"))["valid"] is True


def test_tool_execution_validation_and_governance():
    ensure_builtin_tools(reset=True)
    insight = _sample_insight()
    response = execute_tool(
        "validation",
        arguments={},
        context={"raw_insights": [insight]},
        caller="test",
    )
    assert response.status == ToolExecutionStatus.completed
    assert response.result["validation_status"] in {"validated", "pending", "rejected", "needs_review"}
    assert response.result["validated_insight"].id == "insight_tool"

    gov = execute_tool(
        "governance_validation",
        arguments={"forecast_id": "fc_test", "owner": "qa"},
        context={"dataset_id": "sales_q1"},
    )
    assert gov.status == ToolExecutionStatus.completed
    assert gov.result["validation"]["valid"] is True


def test_tool_execution_context_only_analysis_tools():
    ensure_builtin_tools(reset=True)
    profile = execute_tool("data_profiling", context={"dataset_id": "sales_q1"})
    assert profile.status == ToolExecutionStatus.completed
    assert profile.result["has_dataframe"] is False

    kpi = execute_tool(
        "kpi_detection",
        context={"insights": None, "dataset_id": "sales_q1"},
    )
    assert kpi.status == ToolExecutionStatus.completed

    viz = execute_tool("visualization_recommendation", context={})
    assert viz.status == ToolExecutionStatus.completed
    assert viz.result["recommendations"]


def test_unknown_and_custom_tool():
    ensure_builtin_tools(reset=True)
    missing = execute_tool("does_not_exist")
    assert missing.status == ToolExecutionStatus.failed

    def handler(arguments, context):
        return {"echo": arguments.get("value", 0), "ok": True}

    custom = ToolDefinition(
        tool_id="echo_tool",
        name="Echo",
        description="Echo arguments",
        input_schema={"value": "number"},
        output_schema={"echo": "number"},
        permission_flag="internal.read",
        tags=["test"],
    )
    register_tool(custom, handler)
    resp = execute_tool(ToolRequest(tool_id="echo_tool", arguments={"value": 7}, caller="test"))
    assert resp.status == ToolExecutionStatus.completed
    assert resp.result["echo"] == 7
