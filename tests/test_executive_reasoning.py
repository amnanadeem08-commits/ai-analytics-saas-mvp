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
from backend.models.decision_models import DecisionCategory, DecisionStatus
from backend.models.executive_reasoning_models import EXECUTIVE_FUTURE_EXTENSION_KEYS
from backend.models.root_cause_models import CauseSeverity, CauseStatus
from backend.models.validation_models import ValidationReport
from backend.services.ai_validation_service import validate_insight
from backend.services.decision_intelligence_service import build_decision
from backend.services.executive_reasoning_service import (
    build_executive_reasoning,
    build_reasoning_collection,
    compute_executive_confidence,
    extract_executive_findings,
    extract_executive_opportunities,
    extract_executive_risks,
    group_reasoning_by_domain,
    rank_reasoning,
    summarize_reasoning,
)
from backend.services.root_cause_analysis_service import build_root_cause


def _base_insight(**overrides) -> UniversalAIInsight:
    insight = UniversalAIInsight(
        id="insight_exec",
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
        validation_status=ValidationStatus.validated,
        data_quality_score=DataQualityScore(score=90.0, grade="A", completeness_pct=97.0, dimensions={"freshness": "good"}),
        metadata=InsightMetadata(custom={"dataset_id": "sales_q1"}),
    )
    return insight.model_copy(update=overrides)


def _validated_bundle():
    insight = _base_insight()
    validated, report = validate_insight(insight)
    decision = build_decision(validated)
    root_cause = build_root_cause(insight=validated, decision=decision)
    return validated, report, decision, root_cause


def test_valid_executive_reasoning():
    insight, report, decision, root_cause = _validated_bundle()
    reasoning = build_executive_reasoning(
        insight=insight,
        decision=decision,
        root_cause=root_cause,
        validation=report,
        dataset_id="sales_q1",
    )

    assert reasoning.headline
    assert reasoning.executive_summary
    assert "What happened" in reasoning.executive_summary or reasoning.narrative.what_happened
    assert reasoning.linked_insight_ids == [insight.id]
    assert reasoning.linked_decision_ids == [decision.decision_id]
    assert reasoning.linked_root_cause_ids == [root_cause.root_cause_id]
    assert reasoning.prioritized_recommendations
    assert reasoning.prioritized_recommendations[0].decision_id == decision.decision_id
    assert set(EXECUTIVE_FUTURE_EXTENSION_KEYS).issubset(set(reasoning.metadata.future_extensions.keys()))


def test_missing_decision_still_builds():
    insight, report, _, root_cause = _validated_bundle()
    reasoning = build_executive_reasoning(insight=insight, root_cause=root_cause, validation=report)

    assert reasoning.linked_decision_ids == []
    assert reasoning.prioritized_recommendations == []
    assert reasoning.narrative.what_happened


def test_missing_rca_uses_insight_reason():
    insight, report, decision, _ = _validated_bundle()
    reasoning = build_executive_reasoning(insight=insight, decision=decision, validation=report)

    assert reasoning.linked_root_cause_ids == []
    assert reasoning.narrative.why_it_happened == insight.reason


def test_validation_warnings_surface_as_risks_and_findings():
    insight, report, decision, root_cause = _validated_bundle()
    report = report.model_copy(update={"warnings": ["Evidence source missing for one item."]})
    reasoning = build_executive_reasoning(
        insight=insight,
        decision=decision,
        root_cause=root_cause,
        validation=report,
    )

    assert any(item.finding_type.value == "validation" for item in reasoning.key_findings)
    assert any("Validation warning" in item.title or "Evidence source" in item.description for item in reasoning.key_risks)


def test_confidence_never_exceeds_lowest_component():
    insight, report, decision, root_cause = _validated_bundle()
    decision = decision.model_copy(update={"confidence": 0.4})
    root_cause = root_cause.model_copy(update={"confidence": 0.9})
    confidence = compute_executive_confidence(insight, decision, root_cause, report)
    reasoning = build_executive_reasoning(
        insight=insight,
        decision=decision,
        root_cause=root_cause,
        validation=report,
    )

    assert confidence == reasoning.executive_confidence
    assert reasoning.executive_confidence <= 0.4


def test_priority_ordering_from_existing_decisions_only():
    insight, report, decision, root_cause = _validated_bundle()
    low = decision.model_copy(
        update={
            "decision_id": "decision_low",
            "priority": InsightPriority.low,
            "decision_score": 10,
            "recommended_action": "Monitor only.",
            "title": "Low priority monitor",
        }
    )
    high = decision.model_copy(
        update={
            "decision_id": "decision_high",
            "priority": InsightPriority.critical,
            "decision_score": 90,
            "recommended_action": "Escalate North recovery plan.",
            "title": "Critical recovery",
        }
    )
    # build_executive_reasoning accepts one decision; collection path prioritizes lists
    first = build_executive_reasoning(insight=insight, decision=high, root_cause=root_cause, validation=report)
    second = build_executive_reasoning(
        insight=insight.model_copy(update={"id": "insight_low"}),
        decision=low,
        root_cause=root_cause.model_copy(update={"root_cause_id": "rca_low", "source_insight_id": "insight_low"}),
        validation=report,
    )
    ranked = rank_reasoning([second, first])
    assert ranked[0].prioritized_recommendations[0].recommended_action == "Escalate North recovery plan."


def test_risk_and_opportunity_synthesis():
    insight, report, decision, root_cause = _validated_bundle()
    risks = extract_executive_risks(insight, decision, root_cause, report)
    opportunities = extract_executive_opportunities(insight, decision, root_cause)

    assert risks
    assert opportunities
    assert all(item.source_decision_ids or item.source_root_cause_ids or item.source_validation_warnings for item in risks)


def test_summary_and_collection():
    insight, report, decision, root_cause = _validated_bundle()
    reasoning = build_executive_reasoning(
        insight=insight,
        decision=decision,
        root_cause=root_cause,
        validation=report,
        dataset_id="sales_q1",
        domain="Sales",
    )
    collection = build_reasoning_collection(reasonings=[reasoning], dataset_id="sales_q1", domain="Sales")
    summary = summarize_reasoning([reasoning])

    assert collection.summary.total_reasonings == 1
    assert summary.headline == reasoning.headline
    assert collection.reasonings[0].reasoning_rank == 1


def test_group_by_domain():
    insight, report, decision, root_cause = _validated_bundle()
    sales = build_executive_reasoning(insight=insight, decision=decision, root_cause=root_cause, validation=report, domain="Sales")
    finance_insight = insight.model_copy(update={"id": "insight_finance", "domain": "Finance"})
    finance = build_executive_reasoning(insight=finance_insight, domain="Finance")
    grouped = group_reasoning_by_domain([sales, finance])

    assert "Sales" in grouped
    assert "Finance" in grouped


def test_immutability_of_inputs():
    insight, report, decision, root_cause = _validated_bundle()
    snapshots = (
        insight.model_dump(),
        report.model_dump(),
        decision.model_dump(),
        root_cause.model_dump(),
    )
    build_executive_reasoning(insight=insight, decision=decision, root_cause=root_cause, validation=report)
    assert insight.model_dump() == snapshots[0]
    assert report.model_dump() == snapshots[1]
    assert decision.model_dump() == snapshots[2]
    assert root_cause.model_dump() == snapshots[3]


def test_metadata_traceability_and_future_extensions():
    insight, report, decision, root_cause = _validated_bundle()
    reasoning = build_executive_reasoning(
        insight=insight,
        decision=decision,
        root_cause=root_cause,
        validation=report,
    )
    assert insight.id in reasoning.metadata.linked_insight_ids
    assert decision.decision_id in reasoning.metadata.linked_decision_ids
    assert root_cause.root_cause_id in reasoning.metadata.linked_root_cause_ids
    assert reasoning.metadata.linked_validation_report_ids
    for key in EXECUTIVE_FUTURE_EXTENSION_KEYS:
        assert reasoning.metadata.future_extensions[key] == {}


def test_no_fabrication_without_inputs():
    with pytest.raises(ValueError):
        build_executive_reasoning()


def test_findings_only_from_validated_fields():
    insight, report, decision, root_cause = _validated_bundle()
    findings = extract_executive_findings(insight, decision, root_cause, report)
    statements = " ".join(item.statement for item in findings)
    assert insight.insight in statements or insight.summary in statements
    assert root_cause.description in statements or insight.reason in statements
