from __future__ import annotations

from typing import Any

from backend.models.ai_insight_models import utc_now_iso
from backend.models.decision_models import DecisionCollection
from backend.models.intelligence_bundle_models import IntelligenceBundle
from backend.models.intelligence_registry_models import IntelligenceRegistry
from backend.models.prediction_models import Prediction, PredictionCollection
from backend.models.prediction_validation_models import (
    PREDICTION_VALIDATION_SCHEMA_VERSION,
    EvaluationStatus,
    LearningSummary,
    ObservedResult,
    PredictionAccuracy,
    PredictionEvaluation,
    PredictionLearningRecord,
    PredictionValidation,
    PredictionValidationCollection,
    PredictionValidationMetadata,
    PredictionValidationStatistics,
    PredictionValidationTraceability,
    empty_prediction_validation_future_extensions,
)
from backend.models.root_cause_models import RootCauseCollection
from backend.models.validation_models import ValidationReport


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _validation_id(report: ValidationReport) -> str:
    return f"validation_{report.validator_version}_{report.validated_at}"


def calculate_error(predicted_value: Any, observed_value: Any) -> dict[str, float | None]:
    """Compute absolute and percentage error from supplied values only."""
    predicted = _as_float(predicted_value)
    observed = _as_float(observed_value)
    if predicted is None or observed is None:
        return {"absolute_error": None, "percentage_error": None}

    absolute_error = abs(predicted - observed)
    if observed == 0:
        percentage_error = None if predicted == 0 else 100.0
    else:
        percentage_error = abs((predicted - observed) / observed) * 100.0
    return {
        "absolute_error": round(absolute_error, 6),
        "percentage_error": None if percentage_error is None else round(percentage_error, 6),
    }


def evaluate_accuracy(
    *,
    predicted_value: Any,
    observed_value: Any,
    prediction_confidence: float | None = None,
    baseline_value: Any = None,
) -> PredictionAccuracy:
    """Derive quality metrics from predicted vs observed. No ML / no fabrication."""
    errors = calculate_error(predicted_value, observed_value)
    absolute_error = errors["absolute_error"]
    percentage_error = errors["percentage_error"]

    predicted = _as_float(predicted_value)
    observed = _as_float(observed_value)
    baseline = _as_float(baseline_value)

    direction_correct: bool | None = None
    if predicted is not None and observed is not None and baseline is not None:
        pred_dir = predicted - baseline
        obs_dir = observed - baseline
        if pred_dir == 0 and obs_dir == 0:
            direction_correct = True
        elif pred_dir == 0 or obs_dir == 0:
            direction_correct = pred_dir == obs_dir
        else:
            direction_correct = (pred_dir > 0) == (obs_dir > 0)
    elif predicted is not None and observed is not None:
        # Without baseline, direction is correct when signs of values match relative to zero delta.
        direction_correct = (predicted - observed) == 0 or True  # value present; directional check needs baseline
        if baseline is None:
            direction_correct = None

    prediction_bias = None
    if predicted is not None and observed is not None:
        prediction_bias = round(predicted - observed, 6)

    prediction_drift = None
    if percentage_error is not None:
        prediction_drift = round(percentage_error / 100.0, 6)

    # Confidence calibration: how close stated confidence is to inverse normalized error.
    confidence_calibration = None
    if prediction_confidence is not None and percentage_error is not None:
        realized = max(0.0, min(1.0, 1.0 - min(percentage_error, 100.0) / 100.0))
        confidence_calibration = round(1.0 - abs(prediction_confidence - realized), 4)

    validation_score = None
    if percentage_error is not None:
        validation_score = round(max(0.0, 100.0 - min(percentage_error, 100.0)), 4)
    elif absolute_error is not None and absolute_error == 0:
        validation_score = 100.0

    learning_score = None
    if validation_score is not None:
        bonus = 0.0
        if direction_correct is True:
            bonus += 5.0
        if confidence_calibration is not None:
            bonus += confidence_calibration * 10.0
        learning_score = round(min(100.0, validation_score + bonus), 4)

    return PredictionAccuracy(
        absolute_error=absolute_error,
        percentage_error=percentage_error,
        direction_correct=direction_correct,
        confidence_calibration=confidence_calibration,
        prediction_drift=prediction_drift,
        prediction_bias=prediction_bias,
        validation_score=validation_score,
        learning_score=learning_score,
    )


def build_learning_record(
    *,
    prediction: Prediction,
    observation: ObservedResult | None,
    accuracy: PredictionAccuracy,
    evaluation_status: EvaluationStatus,
    validated_at: str,
) -> PredictionLearningRecord:
    """Build an immutable learning record. Does not mutate the prediction."""
    prediction_c = prediction.model_copy(deep=True)
    observed_value = observation.observed_value if observation is not None else None
    confidence_difference = None
    if (
        prediction_c.prediction_confidence is not None
        and accuracy.confidence_calibration is not None
    ):
        # Difference between stated confidence and calibration quality.
        confidence_difference = round(
            prediction_c.prediction_confidence - accuracy.confidence_calibration,
            4,
        )

    improvement_notes: list[str] = []
    if evaluation_status == EvaluationStatus.pending_validation:
        improvement_notes.append("Observed data is missing; validation pending.")
    elif evaluation_status == EvaluationStatus.insufficient:
        improvement_notes.append("Predicted or observed value is not numeric; evaluation insufficient.")
    else:
        if accuracy.percentage_error is not None and accuracy.percentage_error > 20:
            improvement_notes.append("Percentage error exceeds 20%; review supporting evidence.")
        if accuracy.direction_correct is False:
            improvement_notes.append("Direction incorrect versus baseline; revisit drivers.")
        if accuracy.prediction_bias is not None and abs(accuracy.prediction_bias) > 0:
            if accuracy.prediction_bias > 0:
                improvement_notes.append("Positive bias detected (over-prediction).")
            else:
                improvement_notes.append("Negative bias detected (under-prediction).")
        if accuracy.confidence_calibration is not None and accuracy.confidence_calibration < 0.7:
            improvement_notes.append("Confidence calibration is weak.")
        if not improvement_notes:
            improvement_notes.append("Prediction quality within acceptable bounds.")

    learning_id = f"learn_{prediction_c.prediction_id}_{validated_at.replace(':', '').replace('-', '')}"
    return PredictionLearningRecord(
        learning_id=learning_id,
        prediction_id=prediction_c.prediction_id,
        observed_value=observed_value,
        predicted_value=prediction_c.predicted_value,
        absolute_error=accuracy.absolute_error,
        percentage_error=accuracy.percentage_error,
        direction_correct=accuracy.direction_correct,
        confidence_difference=confidence_difference,
        validation_score=accuracy.validation_score,
        learning_score=accuracy.learning_score,
        evaluation_status=evaluation_status,
        improvement_notes=improvement_notes,
        validated_at=validated_at,
        metadata={
            "observation_id": observation.observation_id if observation else None,
            "predicted_metric": prediction_c.predicted_metric,
            "prediction_confidence": prediction_c.prediction_confidence,
        },
    )


def _build_traceability(
    prediction: Prediction,
    *,
    observation: ObservedResult | None,
    bundle: IntelligenceBundle | None,
    registry: IntelligenceRegistry | None,
    validations: list[ValidationReport] | None,
    decisions: DecisionCollection | None,
    root_causes: RootCauseCollection | None,
) -> PredictionValidationTraceability:
    registry_refs = list(prediction.registry_reference)
    if registry is not None:
        registry_refs.extend(a.reference_id or a.object_id for a in registry.assets)

    validation_refs = list(prediction.validation_reference)
    if validations:
        validation_refs.extend(_validation_id(item) for item in validations)

    decision_refs = list(prediction.supporting_decisions)
    if decisions is not None:
        decision_refs.extend(item.decision_id for item in decisions.decisions)

    root_refs = list(prediction.supporting_root_causes)
    if root_causes is not None:
        root_refs.extend(item.root_cause_id for item in root_causes.root_causes)

    def _unique(values: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            out.append(value)
        return out

    return PredictionValidationTraceability(
        prediction_id=prediction.prediction_id,
        bundle_reference=(
            prediction.bundle_reference
            or (bundle.bundle_id if bundle is not None else None)
        ),
        registry_reference=_unique(registry_refs),
        validation_reference=_unique(validation_refs),
        decision_reference=_unique(decision_refs),
        root_cause_reference=_unique(root_refs),
        observation_id=observation.observation_id if observation is not None else None,
    )


def validate_prediction(
    prediction: Prediction,
    observation: ObservedResult | None = None,
    *,
    bundle: IntelligenceBundle | None = None,
    registry: IntelligenceRegistry | None = None,
    validations: list[ValidationReport] | None = None,
    decisions: DecisionCollection | None = None,
    root_causes: RootCauseCollection | None = None,
) -> PredictionValidation:
    """Validate one prediction against a supplied observation. Never mutates the prediction."""
    prediction_c = prediction.model_copy(deep=True)
    observation_c = observation.model_copy(deep=True) if observation is not None else None
    bundle_c = bundle.model_copy(deep=True) if bundle is not None else None
    registry_c = registry.model_copy(deep=True) if registry is not None else None
    decisions_c = decisions.model_copy(deep=True) if decisions is not None else None
    root_causes_c = root_causes.model_copy(deep=True) if root_causes is not None else None
    validations_c = [item.model_copy(deep=True) for item in (validations or [])]

    now = utc_now_iso()

    if observation_c is None or observation_c.observed_value is None:
        status = EvaluationStatus.pending_validation
        accuracy = PredictionAccuracy()
        notes = "Observed data is missing."
        observed_value = None
        observation_id = None
    else:
        predicted_num = _as_float(prediction_c.predicted_value)
        observed_num = _as_float(observation_c.observed_value)
        if predicted_num is None or observed_num is None:
            status = EvaluationStatus.insufficient
            accuracy = PredictionAccuracy()
            notes = "Predicted or observed value is not numeric."
        else:
            status = EvaluationStatus.evaluated
            accuracy = evaluate_accuracy(
                predicted_value=prediction_c.predicted_value,
                observed_value=observation_c.observed_value,
                prediction_confidence=prediction_c.prediction_confidence,
                baseline_value=observation_c.baseline_value,
            )
            notes = "Prediction evaluated against supplied observation."
        observed_value = observation_c.observed_value
        observation_id = observation_c.observation_id

    evaluation = PredictionEvaluation(
        evaluation_id=f"eval_{prediction_c.prediction_id}_{now.replace(':', '').replace('-', '')}",
        prediction_id=prediction_c.prediction_id,
        observation_id=observation_id,
        predicted_value=prediction_c.predicted_value,
        observed_value=observed_value,
        accuracy=accuracy,
        evaluation_status=status,
        notes=notes,
        evaluated_at=now,
    )
    learning = build_learning_record(
        prediction=prediction_c,
        observation=observation_c,
        accuracy=accuracy,
        evaluation_status=status,
        validated_at=now,
    )
    traceability = _build_traceability(
        prediction_c,
        observation=observation_c,
        bundle=bundle_c,
        registry=registry_c,
        validations=validations_c,
        decisions=decisions_c,
        root_causes=root_causes_c,
    )

    return PredictionValidation(
        validation_id=f"pval_{prediction_c.prediction_id}_{now.replace(':', '').replace('-', '')}",
        prediction_id=prediction_c.prediction_id,
        evaluation=evaluation,
        learning_record=learning,
        accuracy=accuracy,
        traceability=traceability,
        generated_at=now,
        metadata=PredictionValidationMetadata(
            legacy={"schema": PREDICTION_VALIDATION_SCHEMA_VERSION},
            debug={"status": status.value, "has_observation": observation_c is not None},
            custom={},
            future_extensions=empty_prediction_validation_future_extensions(),
        ),
    )


def rank_prediction_quality(
    validations: list[PredictionValidation],
) -> list[PredictionValidation]:
    """Rank by learning_score then validation_score. Deep copies only."""

    def sort_key(item: PredictionValidation) -> tuple:
        learning = item.accuracy.learning_score
        validation = item.accuracy.validation_score
        status_rank = 0 if item.evaluation.evaluation_status == EvaluationStatus.evaluated else 1
        return (
            status_rank,
            -(learning if learning is not None else -1.0),
            -(validation if validation is not None else -1.0),
            item.prediction_id,
        )

    return [item.model_copy(deep=True) for item in sorted(validations, key=sort_key)]


def learning_summary(validations: list[PredictionValidation]) -> LearningSummary:
    evaluated = [
        item
        for item in validations
        if item.evaluation.evaluation_status == EvaluationStatus.evaluated
    ]
    pending = sum(
        1
        for item in validations
        if item.evaluation.evaluation_status == EvaluationStatus.pending_validation
    )
    insufficient = sum(
        1
        for item in validations
        if item.evaluation.evaluation_status == EvaluationStatus.insufficient
    )

    scores = [item.accuracy.validation_score for item in evaluated if item.accuracy.validation_score is not None]
    errors = [item.accuracy.absolute_error for item in evaluated if item.accuracy.absolute_error is not None]
    biases = [item.accuracy.prediction_bias for item in evaluated if item.accuracy.prediction_bias is not None]
    drifts = [item.accuracy.prediction_drift for item in evaluated if item.accuracy.prediction_drift is not None]
    calibrations = [
        item.accuracy.confidence_calibration
        for item in evaluated
        if item.accuracy.confidence_calibration is not None
    ]
    learning_scores = [
        item.accuracy.learning_score for item in evaluated if item.accuracy.learning_score is not None
    ]

    ranked = rank_prediction_quality(evaluated)
    best = [item.prediction_id for item in ranked[:3]]
    worst = [item.prediction_id for item in list(reversed(ranked))[:3]] if ranked else []

    return LearningSummary(
        overall_accuracy=_avg(scores),
        best_predictions=best,
        worst_predictions=worst,
        average_error=_avg(errors),
        bias_indicator=_avg(biases),
        drift_indicator=_avg(drifts),
        confidence_quality=_avg(calibrations),
        learning_statistics={
            "average_learning_score": _avg(learning_scores),
            "evaluated_count": len(evaluated),
            "total_count": len(validations),
        },
        pending_count=pending,
        evaluated_count=len(evaluated),
        insufficient_count=insufficient,
    )


def prediction_statistics(
    validations: list[PredictionValidation],
) -> PredictionValidationStatistics:
    by_status: dict[str, int] = {}
    abs_errors: list[float] = []
    pct_errors: list[float] = []
    val_scores: list[float] = []
    learn_scores: list[float] = []
    direction_flags: list[bool] = []
    with_obs = 0
    without_obs = 0

    for item in validations:
        status = item.evaluation.evaluation_status.value
        by_status[status] = by_status.get(status, 0) + 1
        if item.evaluation.observation_id:
            with_obs += 1
        else:
            without_obs += 1
        if item.accuracy.absolute_error is not None:
            abs_errors.append(item.accuracy.absolute_error)
        if item.accuracy.percentage_error is not None:
            pct_errors.append(item.accuracy.percentage_error)
        if item.accuracy.validation_score is not None:
            val_scores.append(item.accuracy.validation_score)
        if item.accuracy.learning_score is not None:
            learn_scores.append(item.accuracy.learning_score)
        if item.accuracy.direction_correct is not None:
            direction_flags.append(item.accuracy.direction_correct)

    direction_rate = None
    if direction_flags:
        direction_rate = round(sum(1 for flag in direction_flags if flag) / len(direction_flags), 4)

    return PredictionValidationStatistics(
        total=len(validations),
        by_status=by_status,
        average_absolute_error=_avg(abs_errors),
        average_percentage_error=_avg(pct_errors),
        average_validation_score=_avg(val_scores),
        average_learning_score=_avg(learn_scores),
        direction_correct_rate=direction_rate,
        with_observation=with_obs,
        without_observation=without_obs,
    )


def validate_collection(
    predictions: PredictionCollection,
    observations: list[ObservedResult] | None = None,
    *,
    bundle: IntelligenceBundle | None = None,
    registry: IntelligenceRegistry | None = None,
    validations: list[ValidationReport] | None = None,
    decisions: DecisionCollection | None = None,
    root_causes: RootCauseCollection | None = None,
) -> PredictionValidationCollection:
    """Validate a prediction collection against supplied observations. Never mutates inputs."""
    predictions_c = predictions.model_copy(deep=True)
    observations_c = [item.model_copy(deep=True) for item in (observations or [])]
    obs_by_pred = {item.prediction_id: item for item in observations_c}

    results: list[PredictionValidation] = []
    for prediction in predictions_c.predictions:
        results.append(
            validate_prediction(
                prediction,
                obs_by_pred.get(prediction.prediction_id),
                bundle=bundle,
                registry=registry,
                validations=validations,
                decisions=decisions,
                root_causes=root_causes,
            )
        )

    now = utc_now_iso()
    learning_records = [item.learning_record.model_copy(deep=True) for item in results]
    return PredictionValidationCollection(
        collection_id=f"pval_coll_{predictions_c.dataset_id or 'empty'}_{now.replace(':', '').replace('-', '')}",
        dataset_id=predictions_c.dataset_id,
        domain=predictions_c.domain,
        validations=results,
        learning_records=learning_records,
        summary=learning_summary(results),
        statistics=prediction_statistics(results),
        generated_at=now,
        metadata=PredictionValidationMetadata(
            legacy={"schema": PREDICTION_VALIDATION_SCHEMA_VERSION},
            debug={"validation_count": len(results), "observation_count": len(observations_c)},
            custom={},
            future_extensions=empty_prediction_validation_future_extensions(),
        ),
    )
