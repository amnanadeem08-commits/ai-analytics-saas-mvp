from __future__ import annotations

import pytest

from backend.models.ai_insight_models import (
    AI_INSIGHT_SCHEMA_VERSION,
    DataQualityScore,
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
from backend.models.decision_models import DecisionCategory, DecisionStatus, DecisionTimeHorizon
from backend.services.ai_validation_service import validate_insight
from backend.services.decision_intelligence_service import (
    build_decision,
    build_decision_collection,
    group_by_category,
    infer_category,
    prioritize_decisions,
    rank_decisions,
    summarize_decisions,
)


def _validated_insight(**overrides) -> UniversalAIInsight:
    insight = UniversalAIInsight(
        id="insight_revenue",
        schema_version=AI_INSIGHT_SCHEMA_VERSION,
        title="Revenue growth opportunity in East",
        summary="East region revenue outperformed other segments.",
        insight="East region revenue outperformed other segments.",
        reason="East segment totals are consistently higher.",
        supporting_evidence=[
            SupportingEvidenceItem(
                label="East revenue total",
                value=120000,
                evidence_type="metric",
                source="validated_kpi",
                confidence_score=0.9,
            )
        ],
        affected_metrics=["revenue"],
        business_impact="Focus can improve overall revenue growth.",
        expected_outcome="Increase total revenue by prioritizing the East playbook.",
        risk_level=RiskLevel.low,
        priority=InsightPriority.high,
        recommended_actions=[
            RecommendedAction(
                action="Scale the East region sales playbook.",
                rationale="East is the strongest validated segment.",
                expected_outcome="Higher revenue growth within one quarter.",
                expected_impact="Revenue growth",
                estimated_effort="medium",
                urgency="high",
            ),
            RecommendedAction(
                action="Pilot the playbook in one adjacent region.",
                rationale="Lower-risk expansion option.",
                expected_outcome="Test transferability before broad rollout.",
                estimated_effort="low",
                urgency="medium",
            ),
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
        metadata=InsightMetadata(
            custom={
                "dataset_id": "sales_q1",
                "target_value": 150000,
                "estimated_value": "high",
            }
        ),
    )
    insight = insight.model_copy(update=overrides)
    # Preserve explicit pending/rejected overrides for decision-gate tests.
    if insight.validation_status in {ValidationStatus.pending, ValidationStatus.rejected}:
        return insight
    validated, _ = validate_insight(insight)
    return validated


def test_valid_decision_is_complete_with_audit_fields():
    insight = _validated_insight()
    decision = build_decision(insight, source_dataset="sales_q1")

    assert decision.status == DecisionStatus.complete
    assert decision.decision_score > 0
    assert decision.source_dataset == "sales_q1"
    assert decision.source_schema_version == AI_INSIGHT_SCHEMA_VERSION
    assert decision.source_validation_report is not None
    assert decision.decision_path
    assert decision.expected_outcome_target is not None
    assert decision.expected_outcome_target.target_metric == "revenue"
    assert decision.metadata.future_extensions["prediction"] == {}


def test_missing_evidence_marks_decision_incomplete():
    insight = _validated_insight(supporting_evidence=[])
    validated, _ = validate_insight(insight)
    decision = build_decision(validated)

    assert decision.status == DecisionStatus.incomplete
    assert not decision.supporting_evidence


def test_missing_recommendation_marks_decision_incomplete():
    insight = _validated_insight(recommended_actions=[])
    validated, _ = validate_insight(insight)
    decision = build_decision(validated)

    assert decision.status == DecisionStatus.incomplete
    assert decision.recommended_action == ""


def test_rejected_insight_produces_blocked_decision():
    insight = _validated_insight(validation_status=ValidationStatus.rejected)
    decision = build_decision(insight)

    assert decision.status == DecisionStatus.blocked
    assert decision.decision_score == 0.0


def test_pending_insight_raises():
    insight = _validated_insight(validation_status=ValidationStatus.pending)
    with pytest.raises(ValueError, match="validated"):
        build_decision(insight)


def test_priority_ranking_assigns_decision_rank():
    high = build_decision(_validated_insight(id="high", priority=InsightPriority.high))
    low = build_decision(
        _validated_insight(
            id="low",
            priority=InsightPriority.low,
            title="Data quality completeness warning",
            summary="Missing values remain in key fields.",
            insight="Missing values remain in key fields.",
            recommended_actions=[
                RecommendedAction(
                    action="Improve completeness before acting on growth decisions.",
                    rationale="Data quality must be improved.",
                    expected_outcome="Higher confidence in downstream decisions.",
                    urgency="medium",
                )
            ],
            metadata=InsightMetadata(custom={"decision_category": "Data Quality", "dataset_id": "sales_q1"}),
        )
    )

    ranked = rank_decisions([low, high])
    assert ranked[0].decision_rank == 1
    assert ranked[0].decision_score >= ranked[1].decision_score


def test_category_grouping():
    growth = build_decision(_validated_insight(id="growth_one"))
    risk = build_decision(
        _validated_insight(
            id="risk_one",
            title="Risk: churn increasing",
            summary="Churn risk is rising.",
            insight="Churn risk is rising.",
            risk_level=RiskLevel.high,
            metadata=InsightMetadata(custom={"decision_category": "Risk Mitigation"}),
        )
    )
    grouped = group_by_category([growth, risk])

    assert DecisionCategory.revenue_growth.value in grouped
    assert DecisionCategory.risk_mitigation.value in grouped


def test_category_inference_order_metadata_domain_risk_keywords():
    metadata_insight = UniversalAIInsight(
        id="meta",
        title="Generic",
        summary="Generic",
        insight="Generic",
        generated_by=InsightProvenance(engine="test"),
        generated_at=utc_now_iso(),
        metadata=InsightMetadata(custom={"decision_category": "Compliance"}),
    )
    category, source = infer_category(metadata_insight)
    assert category == DecisionCategory.compliance
    assert source == "metadata"

    domain_insight = metadata_insight.model_copy(
        update={"metadata": InsightMetadata(), "domain": "Healthcare"}
    )
    category, source = infer_category(domain_insight)
    assert category == DecisionCategory.customer_experience
    assert source == "domain"

    risk_insight = domain_insight.model_copy(
        update={"domain": None, "risk_level": RiskLevel.critical}
    )
    category, source = infer_category(risk_insight)
    assert category == DecisionCategory.risk_mitigation
    assert source == "risk"

    keyword_insight = risk_insight.model_copy(
        update={"risk_level": RiskLevel.low, "title": "Forecast readiness for revenue"}
    )
    category, source = infer_category(keyword_insight)
    assert category == DecisionCategory.forecasting
    assert source == "keywords"


def test_alternative_generation():
    decision = build_decision(_validated_insight())
    assert len(decision.alternatives) == 1
    assert decision.alternatives[0].action.startswith("Pilot")


def test_dependency_fields_supported():
    insight = _validated_insight(
        metadata=InsightMetadata(
            custom={
                "depends_on": ["decision_data_quality"],
                "blocks": ["decision_forecast"],
                "dataset_id": "sales_q1",
            }
        )
    )
    decision = build_decision(insight)
    assert "decision_data_quality" in decision.depends_on
    assert "decision_forecast" in decision.blocks


def test_decision_collection_and_summary():
    collection = build_decision_collection(
        [
            _validated_insight(id="one"),
            _validated_insight(
                id="two",
                title="Risk: margin compression",
                summary="Margin compression detected.",
                insight="Margin compression detected.",
                risk_level=RiskLevel.high,
                metadata=InsightMetadata(custom={"decision_category": "Risk Mitigation"}),
            ),
        ],
        dataset_id="sales_q1",
        domain="Sales",
    )

    assert collection.dataset_id == "sales_q1"
    assert len(collection.decisions) == 2
    assert collection.summary.total_decisions == 2
    assert collection.summary.overall_business_health
    assert collection.summary.top_risks
    assert collection.summary.category_breakdown


def test_original_insight_not_mutated():
    insight = _validated_insight()
    snapshot = insight.model_dump()
    build_decision(insight)
    assert insight.model_dump() == snapshot


def test_prioritize_decisions_matches_rank_decisions():
    decisions = [
        build_decision(_validated_insight(id="a", priority=InsightPriority.medium)),
        build_decision(_validated_insight(id="b", priority=InsightPriority.critical)),
    ]
    ranked = rank_decisions(decisions)
    prioritized = prioritize_decisions(decisions)
    assert [item.decision_id for item in ranked] == [item.decision_id for item in prioritized]


def test_summarize_decisions_identifies_quick_wins_and_strategic_actions():
    immediate = build_decision(
        _validated_insight(
            id="quick",
            recommended_actions=[
                RecommendedAction(
                    action="Call top at-risk accounts this week.",
                    rationale="Immediate retention action.",
                    expected_outcome="Reduce near-term churn.",
                    urgency="immediate",
                )
            ],
            metadata=InsightMetadata(custom={"decision_category": "Risk Mitigation"}),
        )
    )
    strategic = build_decision(
        _validated_insight(
            id="strategic",
            title="Strategic planning for expansion",
            summary="Plan expansion into new markets.",
            insight="Plan expansion into new markets.",
            recommended_actions=[
                RecommendedAction(
                    action="Launch a 12-month strategic expansion review.",
                    rationale="Long-term growth planning.",
                    expected_outcome="Clear expansion roadmap.",
                    urgency="low",
                )
            ],
            metadata=InsightMetadata(custom={"decision_category": "Strategic Planning"}),
        )
    )
    summary = summarize_decisions([immediate, strategic])
    assert summary.quick_wins
    assert summary.strategic_actions
