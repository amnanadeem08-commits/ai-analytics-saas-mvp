from __future__ import annotations

import pytest

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
from backend.models.decision_models import DecisionStatus
from backend.models.root_cause_models import (
    CauseCategory,
    CauseOrigin,
    CauseStatus,
    ProbabilitySource,
)
from backend.services.ai_validation_service import validate_insight
from backend.services.decision_intelligence_service import build_decision
from backend.services.root_cause_analysis_service import (
    build_cause_chain,
    build_root_cause,
    build_root_cause_collection,
    find_contributing_factors,
    find_primary_cause,
    group_by_category,
    rank_root_causes,
    summarize_root_causes,
)


def _base_insight(**overrides) -> UniversalAIInsight:
    insight = UniversalAIInsight(
        id="insight_revenue",
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
        related_charts=["chart_revenue_by_region"],
        domain="Sales",
        generated_by=InsightProvenance(engine="ai_business_insight_service", provider="platform", engine_version="1.0.0"),
        generated_at=utc_now_iso(),
        validation_status=ValidationStatus.validated,
        data_quality_score=DataQualityScore(score=90.0, grade="A", completeness_pct=97.0, dimensions={"freshness": "good"}),
        metadata=InsightMetadata(custom={"dataset_id": "sales_q1"}),
    )
    return insight.model_copy(update=overrides)


def _validated_insight(**overrides) -> UniversalAIInsight:
    forced_status = overrides.get("validation_status")
    if forced_status in {ValidationStatus.pending, ValidationStatus.rejected}:
        return _base_insight(**overrides)
    insight = _base_insight(**{key: value for key, value in overrides.items() if key != "validation_status"})
    validated, _ = validate_insight(insight)
    return validated


def test_valid_rca_with_insight_and_decision():
    insight = _validated_insight()
    decision = build_decision(insight)
    cause = build_root_cause(insight=insight, decision=decision)

    assert cause.status == CauseStatus.identified
    assert cause.cause_score > 0
    assert cause.traceability_score > 0
    assert cause.source_insight_id == insight.id
    assert cause.source_decision_id == decision.decision_id
    assert cause.probability is None
    assert cause.probability_source == ProbabilitySource.unknown
    assert cause.confidence == insight.overall_confidence
    assert cause.cause_origin in {CauseOrigin.mixed, CauseOrigin.insight, CauseOrigin.evidence}


def test_insight_only_rca():
    insight = _validated_insight()
    cause = build_root_cause(insight=insight)

    assert cause.source_decision_id == ""
    assert cause.description
    assert cause.supporting_evidence
    assert cause.probability is None


def test_probability_never_copied_from_confidence():
    insight = _validated_insight(overall_confidence=0.91)
    cause = build_root_cause(insight=insight)

    assert cause.confidence == 0.91
    assert cause.probability is None
    assert cause.probability != cause.confidence


def test_explicit_probability_from_metadata_only():
    insight = _validated_insight(
        metadata=InsightMetadata(
            custom={"dataset_id": "sales_q1", "probability": 0.35, "probability_source": "estimated"}
        )
    )
    cause = build_root_cause(insight=insight)

    assert cause.probability == 0.35
    assert cause.probability_source == ProbabilitySource.estimated
    assert cause.confidence != cause.probability


def test_pending_insight_raises():
    insight = _base_insight(validation_status=ValidationStatus.pending)
    with pytest.raises(ValueError, match="validated"):
        build_root_cause(insight=insight)


def test_rejected_insight_is_blocked():
    insight = _validated_insight(validation_status=ValidationStatus.rejected)
    cause = build_root_cause(insight=insight)

    assert cause.status == CauseStatus.blocked
    assert cause.cause_score == 0.0


def test_blocked_decision_is_blocked():
    insight = _validated_insight()
    decision = build_decision(insight)
    decision = decision.model_copy(update={"status": DecisionStatus.blocked})
    cause = build_root_cause(insight=insight, decision=decision)

    assert cause.status == CauseStatus.blocked


def test_missing_evidence_is_inconclusive():
    insight = _validated_insight(supporting_evidence=[])
    validated, _ = validate_insight(insight)
    cause = build_root_cause(insight=validated)

    assert cause.status == CauseStatus.inconclusive
    assert not cause.supporting_evidence


def test_cause_chain_is_hierarchical_and_graph_ready():
    insight = _validated_insight(
        metadata=InsightMetadata(
            custom={
                "dataset_id": "sales_q1",
                "driver_facts": [
                    {
                        "description": "Retail channel underperformed within North",
                        "label": "Retail channel",
                        "value": "underperformed",
                        "source": "metadata.custom.driver_facts",
                        "confidence": 0.7,
                    }
                ],
            }
        )
    )
    chain = build_cause_chain(insight)

    assert chain.depth >= 2
    assert len(chain.nodes) >= 3
    assert chain.nodes[0].parent_ids == []
    assert isinstance(chain.nodes[0].child_ids, list)
    assert chain.nodes[1].parent_ids == [chain.nodes[0].node_id]
    assert chain.nodes[0].node_id in chain.nodes[1].parent_ids or chain.nodes[1].node_id in chain.nodes[0].child_ids
    for node in chain.nodes:
        assert isinstance(node.parent_ids, list)
        assert isinstance(node.child_ids, list)
    assert chain.depth <= 4


def test_no_fabricated_driver_nodes_without_metadata():
    insight = _validated_insight()
    chain = build_cause_chain(insight)
    roles = [node.metadata.legacy.get("role") for node in chain.nodes]
    assert "driver_fact" not in roles


def test_ranking_and_primary_cause():
    first = build_root_cause(insight=_validated_insight(id="one"))
    second = build_root_cause(
        insight=_validated_insight(
            id="two",
            title="Data quality completeness warning",
            summary="Missing values remain in key fields.",
            insight="Missing values remain in key fields.",
            reason="Completeness is below the executive threshold.",
            risk_level=RiskLevel.medium,
            overall_confidence=0.4,
            metadata=InsightMetadata(custom={"cause_category": "Data Quality"}),
        )
    )
    ranked = rank_root_causes([second, first])
    primary = find_primary_cause([second, first])

    assert ranked[0].cause_rank == 1
    assert ranked[0].is_primary is True
    assert primary is not None
    assert primary.root_cause_id == ranked[0].root_cause_id


def test_grouping_and_summary():
    sales = build_root_cause(insight=_validated_insight(id="sales_one"))
    quality = build_root_cause(
        insight=_validated_insight(
            id="quality_one",
            title="Data quality issue",
            summary="Missing values detected.",
            insight="Missing values detected.",
            reason="Completeness gaps reduce confidence.",
            metadata=InsightMetadata(custom={"cause_category": "Data Quality", "quick_fixes": ["Fill missing values"]}),
        )
    )
    grouped = group_by_category([sales, quality])
    summary = summarize_root_causes([sales, quality])

    assert CauseCategory.sales.value in grouped or CauseCategory.operations.value in grouped
    assert CauseCategory.data_quality.value in grouped
    assert summary.total_causes == 2
    assert summary.top_cause
    assert summary.primary_cause_id
    assert summary.quick_fixes


def test_contributing_factors_exclude_primary():
    causes = [
        build_root_cause(insight=_validated_insight(id="a")),
        build_root_cause(
            insight=_validated_insight(
                id="b",
                title="Secondary margin pressure",
                summary="Margin pressure detected.",
                insight="Margin pressure detected.",
                reason="Cost mix shifted against plan.",
                overall_confidence=0.5,
            )
        ),
    ]
    primary = find_primary_cause(causes)
    contributing = find_contributing_factors(causes)

    assert primary is not None
    assert all(item.root_cause_id != primary.root_cause_id for item in contributing)


def test_collection_builds_ranked_causes_and_chains():
    insights = [
        _validated_insight(id="one"),
        _validated_insight(
            id="two",
            title="Customer churn risk rising",
            summary="Churn indicators increased.",
            insight="Churn indicators increased.",
            reason="Tenure and contract mix shifted toward higher risk.",
            domain="Customer Churn",
        ),
    ]
    decisions = [build_decision(insights[0])]
    collection = build_root_cause_collection(insights=insights, decisions=decisions, dataset_id="sales_q1", domain="Sales")

    assert collection.dataset_id == "sales_q1"
    assert len(collection.root_causes) == 2
    assert len(collection.chains) == 2
    assert collection.summary.total_causes == 2
    assert collection.root_causes[0].cause_rank == 1


def test_original_insight_and_decision_not_mutated():
    insight = _validated_insight()
    decision = build_decision(insight)
    insight_snapshot = insight.model_dump()
    decision_snapshot = decision.model_dump()

    build_root_cause(insight=insight, decision=decision)
    build_cause_chain(insight, decision)

    assert insight.model_dump() == insight_snapshot
    assert decision.model_dump() == decision_snapshot


def test_traceability_score_increases_with_evidence():
    weak = build_root_cause(insight=_validated_insight(id="weak", supporting_evidence=[], reason=""))
    strong = build_root_cause(insight=_validated_insight(id="strong"))

    assert strong.traceability_score > weak.traceability_score
