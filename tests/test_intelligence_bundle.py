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
    UniversalAIInsightCollection,
    UrgencyLevel,
    ValidationStatus,
    utc_now_iso,
)
from backend.models.intelligence_bundle_models import INTELLIGENCE_BUNDLE_FUTURE_EXTENSION_KEYS
from backend.services.ai_validation_service import validate_insight
from backend.services.decision_intelligence_service import build_decision, build_decision_collection
from backend.services.executive_reasoning_service import build_executive_reasoning, build_reasoning_collection
from backend.services.intelligence_bundle_service import (
    build_intelligence_bundle,
    bundle_references,
    bundle_statistics,
    bundle_summary,
    validate_bundle,
)
from backend.services.root_cause_analysis_service import build_root_cause, build_root_cause_collection
from backend.services.storyboard_engine_service import build_executive_storyboard_from_reasoning


def _base_insight(**overrides) -> UniversalAIInsight:
    insight = UniversalAIInsight(
        id="insight_bundle",
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


def _full_pipeline():
    insight = _base_insight()
    validated, report = validate_insight(insight)
    decision = build_decision(validated)
    root_cause = build_root_cause(insight=validated, decision=decision)
    reasoning = build_executive_reasoning(
        insight=validated,
        decision=decision,
        root_cause=root_cause,
        validation=report,
        dataset_id="sales_q1",
        domain="Sales",
    )
    insights = UniversalAIInsightCollection(dataset_id="sales_q1", domain="Sales", insights=[validated])
    decisions = build_decision_collection([validated], dataset_id="sales_q1", domain="Sales")
    root_causes = build_root_cause_collection(
        insights=[validated],
        decisions=[decision],
        dataset_id="sales_q1",
        domain="Sales",
    )
    reasonings = build_reasoning_collection(reasonings=[reasoning], dataset_id="sales_q1", domain="Sales")
    storyboard = build_executive_storyboard_from_reasoning(
        reasonings=reasonings,
        decisions=decisions,
        root_causes=root_causes,
        validations=[report],
        dataset_id="sales_q1",
        domain="Sales",
    )
    return insights, [report], decisions, root_causes, reasonings, storyboard


def test_bundle_creation():
    insights, validations, decisions, root_causes, reasonings, storyboard = _full_pipeline()
    bundle = build_intelligence_bundle(
        insights=insights,
        validations=validations,
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
        dataset_id="sales_q1",
        domain="Sales",
    )

    assert bundle.dataset_id == "sales_q1"
    assert bundle.domain == "Sales"
    assert bundle.insights is not None
    assert bundle.decisions is not None
    assert bundle.root_causes is not None
    assert bundle.reasonings is not None
    assert bundle.storyboard is not None
    assert bundle.summary.total_insights == 1
    assert bundle.summary.total_decisions == 1
    assert bundle.summary.total_root_causes == 1
    assert bundle.summary.total_storyboards == 1


def test_statistics_and_summary():
    insights, validations, decisions, root_causes, reasonings, storyboard = _full_pipeline()
    stats = bundle_statistics(
        insights=insights,
        validations=validations,
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
    )
    summary = bundle_summary(
        dataset_id="sales_q1",
        domain="Sales",
        insights=insights,
        validations=validations,
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
        generated_at=utc_now_iso(),
    )

    assert stats.counts["insights"] == 1
    assert stats.counts["decisions"] == 1
    assert stats.confidence_averages["insights"] > 0
    assert "high" in stats.risk_distribution or "critical" in stats.risk_distribution
    assert summary.total_validations == 1
    assert summary.overall_validation == ValidationStatus.validated


def test_references_and_traceability():
    insights, validations, decisions, root_causes, reasonings, storyboard = _full_pipeline()
    refs = bundle_references(
        insights=insights,
        validations=validations,
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
    )
    bundle = build_intelligence_bundle(
        insights=insights,
        validations=validations,
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
    )

    assert insights.insights[0].id in refs.insight_ids
    assert decisions.decisions[0].decision_id in refs.decision_ids
    assert root_causes.root_causes[0].root_cause_id in refs.root_cause_ids
    assert storyboard.storyboard_id in refs.storyboard_ids
    assert refs.validation_ids
    assert refs.reasoning_ids
    assert validate_bundle(bundle)["valid"] is True


def test_empty_bundle():
    bundle = build_intelligence_bundle()
    assert bundle.summary.total_insights == 0
    assert bundle.summary.total_decisions == 0
    assert bundle.statistics.counts["storyboards"] == 0
    assert bundle.references.insight_ids == []
    assert set(INTELLIGENCE_BUNDLE_FUTURE_EXTENSION_KEYS).issubset(set(bundle.metadata.future_extensions.keys()))


def test_partial_bundle():
    insights, validations, _, _, _, _ = _full_pipeline()
    bundle = build_intelligence_bundle(insights=insights, validations=validations, dataset_id="sales_q1")

    assert bundle.insights is not None
    assert bundle.decisions is None
    assert bundle.root_causes is None
    assert bundle.storyboard is None
    assert bundle.summary.total_insights == 1
    assert bundle.summary.total_decisions == 0
    assert validate_bundle(bundle)["valid"] is True


def test_immutability():
    insights, validations, decisions, root_causes, reasonings, storyboard = _full_pipeline()
    snapshots = (
        insights.model_dump(),
        validations[0].model_dump(),
        decisions.model_dump(),
        root_causes.model_dump(),
        reasonings.model_dump(),
        storyboard.model_dump(),
    )
    build_intelligence_bundle(
        insights=insights,
        validations=validations,
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
    )
    assert insights.model_dump() == snapshots[0]
    assert validations[0].model_dump() == snapshots[1]
    assert decisions.model_dump() == snapshots[2]
    assert root_causes.model_dump() == snapshots[3]
    assert reasonings.model_dump() == snapshots[4]
    assert storyboard.model_dump() == snapshots[5]


def test_future_extension_buckets():
    bundle = build_intelligence_bundle()
    for key in INTELLIGENCE_BUNDLE_FUTURE_EXTENSION_KEYS:
        assert key in bundle.metadata.future_extensions
        assert bundle.metadata.future_extensions[key] == {}


def test_validate_bundle_detects_missing_reference():
    insights, validations, decisions, root_causes, reasonings, storyboard = _full_pipeline()
    bundle = build_intelligence_bundle(
        insights=insights,
        validations=validations,
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
    )
    broken = bundle.model_copy(
        update={"references": bundle.references.model_copy(update={"insight_ids": []})},
        deep=True,
    )
    result = validate_bundle(broken)
    assert result["valid"] is False
    assert result["issue_count"] >= 1
