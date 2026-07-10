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
from backend.models.prediction_validation_models import (
    PREDICTION_VALIDATION_FUTURE_EXTENSION_KEYS,
    EvaluationStatus,
    ObservedResult,
)
from backend.services.ai_validation_service import validate_insight
from backend.services.decision_intelligence_service import build_decision, build_decision_collection
from backend.services.executive_reasoning_service import build_executive_reasoning, build_reasoning_collection
from backend.services.intelligence_bundle_service import build_intelligence_bundle
from backend.services.intelligence_registry_service import build_registry
from backend.services.prediction_engine_service import build_prediction, build_prediction_collection
from backend.services.prediction_validation_service import (
    build_learning_record,
    calculate_error,
    evaluate_accuracy,
    learning_summary,
    prediction_statistics,
    rank_prediction_quality,
    validate_collection,
    validate_prediction,
)
from backend.services.root_cause_analysis_service import build_root_cause, build_root_cause_collection
from backend.services.storyboard_engine_service import build_executive_storyboard_from_reasoning


def _base_insight(**overrides) -> UniversalAIInsight:
    insight = UniversalAIInsight(
        id="insight_pred_val",
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
    predictions = build_prediction_collection(
        insights=insights,
        validations=[report],
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
        bundle=bundle,
        registry=registry,
        dataset_id="sales_q1",
        domain="Sales",
    )
    return predictions, [report], decisions, root_causes, bundle, registry


def test_error_and_accuracy_calculation():
    errors = calculate_error(100, 80)
    assert errors["absolute_error"] == 20
    assert errors["percentage_error"] == 25.0

    accuracy = evaluate_accuracy(
        predicted_value=110,
        observed_value=100,
        prediction_confidence=0.9,
        baseline_value=90,
    )
    assert accuracy.absolute_error == 10
    assert accuracy.percentage_error == 10.0
    assert accuracy.direction_correct is True
    assert accuracy.prediction_bias == 10
    assert accuracy.prediction_drift == 0.1
    assert accuracy.validation_score is not None
    assert accuracy.learning_score is not None
    assert accuracy.confidence_calibration is not None

    wrong_dir = evaluate_accuracy(
        predicted_value=80,
        observed_value=110,
        baseline_value=100,
    )
    assert wrong_dir.direction_correct is False

    no_baseline = evaluate_accuracy(predicted_value=100, observed_value=90)
    assert no_baseline.direction_correct is None


def test_prediction_validation_and_traceability():
    predictions, validations, decisions, root_causes, bundle, registry = _full_pipeline()
    prediction = predictions.predictions[0]
    # Ensure numeric predicted value for evaluation (use evidence value if present)
    if prediction.predicted_value is None:
        prediction = prediction.model_copy(update={"predicted_value": 42000}, deep=True)

    observation = ObservedResult(
        observation_id="obs_1",
        prediction_id=prediction.prediction_id,
        observed_value=40000,
        observed_metric=prediction.predicted_metric or "total_revenue",
        baseline_value=45000,
        observed_at=utc_now_iso(),
        source="actuals",
    )
    result = validate_prediction(
        prediction,
        observation,
        bundle=bundle,
        registry=registry,
        validations=validations,
        decisions=decisions,
        root_causes=root_causes,
    )
    assert result.evaluation.evaluation_status == EvaluationStatus.evaluated
    assert result.accuracy.absolute_error is not None
    assert result.learning_record.prediction_id == prediction.prediction_id
    assert result.traceability.prediction_id == prediction.prediction_id
    assert result.traceability.bundle_reference == bundle.bundle_id
    assert result.traceability.observation_id == "obs_1"
    assert result.traceability.registry_reference
    assert result.traceability.decision_reference
    assert result.traceability.root_cause_reference


def test_pending_validation():
    predictions, *_ = _full_pipeline()
    prediction = predictions.predictions[0]
    result = validate_prediction(prediction, None)
    assert result.evaluation.evaluation_status == EvaluationStatus.pending_validation
    assert result.learning_record.evaluation_status == EvaluationStatus.pending_validation
    assert "missing" in result.evaluation.notes.lower() or "pending" in result.learning_record.improvement_notes[0].lower()


def test_collection_validation_statistics_summary():
    predictions, validations, decisions, root_causes, bundle, registry = _full_pipeline()
    pred = predictions.predictions[0]
    predicted_value = pred.predicted_value if pred.predicted_value is not None else 42000
    # Normalize collection so predicted_value is numeric for evaluation
    fixed_preds = []
    for item in predictions.predictions:
        if item.predicted_value is None:
            fixed_preds.append(item.model_copy(update={"predicted_value": 42000}, deep=True))
        else:
            fixed_preds.append(item)
    predictions = predictions.model_copy(update={"predictions": fixed_preds}, deep=True)
    pred = predictions.predictions[0]
    predicted_value = pred.predicted_value

    observations = [
        ObservedResult(
            observation_id="obs_coll_1",
            prediction_id=pred.prediction_id,
            observed_value=float(predicted_value) * 0.95 if _is_number(predicted_value) else 40000,
            baseline_value=float(predicted_value) * 1.05 if _is_number(predicted_value) else 45000,
            observed_at=utc_now_iso(),
            source="actuals",
        )
    ]
    collection = validate_collection(
        predictions,
        observations,
        bundle=bundle,
        registry=registry,
        validations=validations,
        decisions=decisions,
        root_causes=root_causes,
    )
    assert collection.validations
    assert collection.learning_records
    assert collection.statistics.total == len(collection.validations)
    assert collection.statistics.with_observation >= 1
    assert collection.summary.evaluated_count >= 1
    assert collection.summary.best_predictions

    ranked = rank_prediction_quality(collection.validations)
    assert ranked
    summary = learning_summary(collection.validations)
    assert summary.evaluated_count >= 1
    stats = prediction_statistics(collection.validations)
    assert stats.total == len(collection.validations)


def _is_number(value) -> bool:
    try:
        float(value)
        return not isinstance(value, bool)
    except (TypeError, ValueError):
        return False


def test_learning_record_builder():
    predictions, *_ = _full_pipeline()
    prediction = predictions.predictions[0].model_copy(update={"predicted_value": 100}, deep=True)
    accuracy = evaluate_accuracy(
        predicted_value=100,
        observed_value=90,
        prediction_confidence=0.8,
        baseline_value=80,
    )
    observation = ObservedResult(
        observation_id="obs_lr",
        prediction_id=prediction.prediction_id,
        observed_value=90,
        baseline_value=80,
        observed_at=utc_now_iso(),
    )
    record = build_learning_record(
        prediction=prediction,
        observation=observation,
        accuracy=accuracy,
        evaluation_status=EvaluationStatus.evaluated,
        validated_at=utc_now_iso(),
    )
    assert record.learning_id
    assert record.absolute_error == accuracy.absolute_error
    assert record.validation_score == accuracy.validation_score
    assert record.improvement_notes


def test_future_buckets():
    predictions, *_ = _full_pipeline()
    result = validate_prediction(predictions.predictions[0], None)
    for key in PREDICTION_VALIDATION_FUTURE_EXTENSION_KEYS:
        assert key in result.metadata.future_extensions
        assert result.metadata.future_extensions[key] == {}

    collection = validate_collection(predictions, None)
    for key in PREDICTION_VALIDATION_FUTURE_EXTENSION_KEYS:
        assert key in collection.metadata.future_extensions


def test_immutability():
    predictions, validations, decisions, root_causes, bundle, registry = _full_pipeline()
    snapshots = (
        predictions.model_dump(),
        validations[0].model_dump(),
        decisions.model_dump(),
        root_causes.model_dump(),
        bundle.model_dump(),
        registry.model_dump(),
    )
    observation = ObservedResult(
        observation_id="obs_immut",
        prediction_id=predictions.predictions[0].prediction_id,
        observed_value=40000,
        baseline_value=45000,
        observed_at=utc_now_iso(),
    )
    validate_collection(
        predictions,
        [observation],
        bundle=bundle,
        registry=registry,
        validations=validations,
        decisions=decisions,
        root_causes=root_causes,
    )
    assert predictions.model_dump() == snapshots[0]
    assert validations[0].model_dump() == snapshots[1]
    assert decisions.model_dump() == snapshots[2]
    assert root_causes.model_dump() == snapshots[3]
    assert bundle.model_dump() == snapshots[4]
    assert registry.model_dump() == snapshots[5]
