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
from backend.models.prediction_models import (
    PREDICTION_FUTURE_EXTENSION_KEYS,
    PredictionStatus,
    ScenarioKind,
)
from backend.services.ai_analyst_service import build_ai_response
from backend.services.ai_validation_service import validate_insight
from backend.services.analyst_skill_service import build_skill_registry
from backend.services.decision_intelligence_service import build_decision, build_decision_collection
from backend.services.executive_reasoning_service import build_executive_reasoning, build_reasoning_collection
from backend.services.intelligence_bundle_service import build_intelligence_bundle
from backend.services.intelligence_registry_service import build_registry
from backend.services.prediction_engine_service import (
    build_prediction,
    build_prediction_collection,
    find_prediction,
    group_predictions,
    prediction_statistics,
    rank_predictions,
    summarize_predictions,
    validate_predictions,
)
from backend.services.root_cause_analysis_service import build_root_cause, build_root_cause_collection
from backend.services.storyboard_engine_service import build_executive_storyboard_from_reasoning


def _base_insight(**overrides) -> UniversalAIInsight:
    insight = UniversalAIInsight(
        id="insight_prediction",
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
        data_quality_score=DataQualityScore(
            score=90.0, grade="A", completeness_pct=97.0, dimensions={"freshness": "good"}
        ),
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
    bundle = build_intelligence_bundle(
        insights=insights,
        validations=[report],
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
        dataset_id="sales_q1",
        domain="Sales",
    )
    registry = build_registry(
        insights=insights,
        validations=[report],
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
        bundle=bundle,
        dataset_id="sales_q1",
        domain="Sales",
    )
    analyst = build_ai_response(
        bundle=bundle,
        registry=registry,
        reasonings=reasonings,
        decisions=decisions,
        root_causes=root_causes,
        validations=[report],
        insights=insights,
        storyboard=storyboard,
    )
    skills = build_skill_registry()
    return (
        insights,
        [report],
        decisions,
        root_causes,
        reasonings,
        storyboard,
        bundle,
        registry,
        analyst,
        skills,
        validated,
        decision,
        root_cause,
        reasoning,
    )


def test_prediction_creation():
    (
        insights,
        validations,
        decisions,
        root_causes,
        reasonings,
        storyboard,
        bundle,
        registry,
        analyst,
        skills,
        validated,
        decision,
        root_cause,
        reasoning,
    ) = _full_pipeline()
    prediction = build_prediction(
        insight=validated,
        decision=decision,
        root_cause=root_cause,
        validation=validations[0],
        reasoning=reasoning,
        storyboard=storyboard,
        bundle=bundle,
        registry=registry,
        analyst_response=analyst,
        analyst_context=analyst.conversation_context,
        skill_registry=skills,
        dataset_id="sales_q1",
        domain="Sales",
    )
    assert prediction.prediction_status == PredictionStatus.ready
    assert prediction.prediction_confidence is not None
    assert prediction.predicted_metric
    assert prediction.evidence
    assert prediction.supporting_decisions
    assert prediction.supporting_insights
    assert len(prediction.scenarios) == 4


def test_scenario_creation():
    *_, validated, decision, root_cause, reasoning = _full_pipeline()
    prediction = build_prediction(insight=validated, decision=decision, root_cause=root_cause, reasoning=reasoning)
    kinds = {s.kind for s in prediction.scenarios}
    assert kinds == {
        ScenarioKind.baseline,
        ScenarioKind.optimistic,
        ScenarioKind.pessimistic,
        ScenarioKind.expected,
    }
    assert all(s.linked_prediction_id == prediction.prediction_id for s in prediction.scenarios)


def test_prediction_ranking_grouping_statistics():
    insights, validations, decisions, root_causes, reasonings, storyboard, bundle, registry, analyst, skills, *_ = (
        _full_pipeline()
    )
    collection = build_prediction_collection(
        insights=insights,
        validations=validations,
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
        bundle=bundle,
        registry=registry,
        analyst_response=analyst,
        skill_registry=skills,
    )
    ranked = rank_predictions(collection.predictions)
    assert ranked[0].prediction_rank == 1
    groups = group_predictions(collection.predictions)
    assert groups
    summary = summarize_predictions(collection.predictions)
    assert summary.total_predictions >= 1
    stats = prediction_statistics(collection.predictions)
    assert stats.counts["total"] == len(collection.predictions)
    assert stats.with_evidence >= 1
    found = find_prediction(collection, collection.predictions[0].prediction_id)
    assert found is not None


def test_traceability_bundle_registry_references():
    insights, validations, decisions, root_causes, reasonings, storyboard, bundle, registry, analyst, skills, *_ = (
        _full_pipeline()
    )
    collection = build_prediction_collection(
        insights=insights,
        validations=validations,
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
        bundle=bundle,
        registry=registry,
        analyst_response=analyst,
        skill_registry=skills,
    )
    pred = collection.predictions[0]
    assert pred.bundle_reference == bundle.bundle_id
    assert pred.storyboard_reference == storyboard.storyboard_id
    assert pred.registry_reference
    assert pred.analyst_reference
    assert pred.validation_reference
    assert pred.reasoning_reference
    assert pred.supporting_decisions
    assert pred.supporting_insights
    assert pred.supporting_root_causes


def test_validation():
    insights, validations, decisions, root_causes, reasonings, storyboard, bundle, registry, analyst, skills, *_ = (
        _full_pipeline()
    )
    collection = build_prediction_collection(
        insights=insights,
        validations=validations,
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
        bundle=bundle,
        registry=registry,
        analyst_response=analyst,
        skill_registry=skills,
    )
    result = validate_predictions(collection)
    assert result["valid"] is True


def test_missing_evidence_insufficient():
    empty = build_prediction()
    assert empty.prediction_status == PredictionStatus.insufficient
    assert empty.prediction_confidence is None
    assert empty.explanation is not None
    assert empty.explanation.unavailable_note

    collection = build_prediction_collection()
    assert collection.predictions
    assert collection.predictions[0].prediction_status == PredictionStatus.insufficient
    assert collection.summary.insufficient_count >= 1


def test_metadata_and_future_buckets():
    prediction = build_prediction()
    for key in PREDICTION_FUTURE_EXTENSION_KEYS:
        assert key in prediction.metadata.future_extensions
        assert prediction.metadata.future_extensions[key] == {}
    collection = build_prediction_collection()
    for key in PREDICTION_FUTURE_EXTENSION_KEYS:
        assert key in collection.metadata.future_extensions


def test_immutability():
    insights, validations, decisions, root_causes, reasonings, storyboard, bundle, registry, analyst, skills, *_ = (
        _full_pipeline()
    )
    snapshots = (
        insights.model_dump(),
        validations[0].model_dump(),
        decisions.model_dump(),
        root_causes.model_dump(),
        reasonings.model_dump(),
        storyboard.model_dump(),
        bundle.model_dump(),
        registry.model_dump(),
        analyst.model_dump(),
        skills.model_dump(),
    )
    build_prediction_collection(
        insights=insights,
        validations=validations,
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
        bundle=bundle,
        registry=registry,
        analyst_response=analyst,
        skill_registry=skills,
    )
    assert insights.model_dump() == snapshots[0]
    assert validations[0].model_dump() == snapshots[1]
    assert decisions.model_dump() == snapshots[2]
    assert root_causes.model_dump() == snapshots[3]
    assert reasonings.model_dump() == snapshots[4]
    assert storyboard.model_dump() == snapshots[5]
    assert bundle.model_dump() == snapshots[6]
    assert registry.model_dump() == snapshots[7]
    assert analyst.model_dump() == snapshots[8]
    assert skills.model_dump() == snapshots[9]
