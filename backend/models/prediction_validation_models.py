from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

PREDICTION_VALIDATION_SCHEMA_VERSION = "1.0.0"

# Reserved empty buckets for future learning layers. Placeholders only.
# Owners:
#   automatic_retraining  → Auto model retraining
#   online_learning       → Online / streaming learning
#   adaptive_models       → Adaptive model updates
#   reinforcement_learning → RL feedback
#   feedback_loop         → Closed-loop feedback
#   model_selection       → Model selection
#   ensemble_learning     → Ensemble learning
#   trading_validation    → Trading-domain validation
#   business_validation   → Business outcome validation
PREDICTION_VALIDATION_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "automatic_retraining",
    "online_learning",
    "adaptive_models",
    "reinforcement_learning",
    "feedback_loop",
    "model_selection",
    "ensemble_learning",
    "trading_validation",
    "business_validation",
)


def empty_prediction_validation_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in PREDICTION_VALIDATION_FUTURE_EXTENSION_KEYS}


class EvaluationStatus(str, Enum):
    pending_validation = "pending_validation"
    evaluated = "evaluated"
    insufficient = "insufficient"
    rejected = "rejected"


class ObservedResult(BaseModel):
    """Caller-supplied observed outcome. Never fabricated by this engine."""

    model_config = ConfigDict(extra="allow")

    observation_id: str
    prediction_id: str
    observed_value: Any = None
    observed_metric: str = ""
    baseline_value: Any = None
    observed_at: str = ""
    source: str = ""
    notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class PredictionAccuracy(BaseModel):
    """Numeric quality metrics derived from predicted vs observed values."""

    absolute_error: float | None = None
    percentage_error: float | None = None
    direction_correct: bool | None = None
    confidence_calibration: float | None = Field(default=None, ge=0.0, le=1.0)
    prediction_drift: float | None = None
    prediction_bias: float | None = None
    validation_score: float | None = Field(default=None, ge=0.0, le=100.0)
    learning_score: float | None = Field(default=None, ge=0.0, le=100.0)


class PredictionEvaluation(BaseModel):
    """Evaluation payload for one prediction against one observation."""

    evaluation_id: str
    prediction_id: str
    observation_id: str | None = None
    predicted_value: Any = None
    observed_value: Any = None
    accuracy: PredictionAccuracy = Field(default_factory=PredictionAccuracy)
    evaluation_status: EvaluationStatus = EvaluationStatus.pending_validation
    notes: str = ""
    evaluated_at: str = ""


class PredictionLearningRecord(BaseModel):
    """Immutable learning record. Does not modify the original prediction."""

    model_config = ConfigDict(extra="allow")

    learning_id: str
    prediction_id: str
    observed_value: Any = None
    predicted_value: Any = None
    absolute_error: float | None = None
    percentage_error: float | None = None
    direction_correct: bool | None = None
    confidence_difference: float | None = None
    validation_score: float | None = Field(default=None, ge=0.0, le=100.0)
    learning_score: float | None = Field(default=None, ge=0.0, le=100.0)
    evaluation_status: EvaluationStatus = EvaluationStatus.pending_validation
    improvement_notes: list[str] = Field(default_factory=list)
    validated_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class PredictionValidationTraceability(BaseModel):
    prediction_id: str = ""
    bundle_reference: str | None = None
    registry_reference: list[str] = Field(default_factory=list)
    validation_reference: list[str] = Field(default_factory=list)
    decision_reference: list[str] = Field(default_factory=list)
    root_cause_reference: list[str] = Field(default_factory=list)
    observation_id: str | None = None


class PredictionValidationMetadata(BaseModel):
    legacy: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    future_extensions: dict[str, Any] = Field(
        default_factory=empty_prediction_validation_future_extensions
    )


class PredictionValidation(BaseModel):
    """Full validation result for one prediction. Original prediction unchanged."""

    model_config = ConfigDict(extra="allow")

    validation_id: str
    schema_version: str = PREDICTION_VALIDATION_SCHEMA_VERSION
    prediction_id: str
    evaluation: PredictionEvaluation
    learning_record: PredictionLearningRecord
    accuracy: PredictionAccuracy = Field(default_factory=PredictionAccuracy)
    traceability: PredictionValidationTraceability = Field(
        default_factory=PredictionValidationTraceability
    )
    generated_at: str = ""
    metadata: PredictionValidationMetadata = Field(default_factory=PredictionValidationMetadata)


class LearningSummary(BaseModel):
    overall_accuracy: float | None = None
    best_predictions: list[str] = Field(default_factory=list)
    worst_predictions: list[str] = Field(default_factory=list)
    average_error: float | None = None
    bias_indicator: float | None = None
    drift_indicator: float | None = None
    confidence_quality: float | None = None
    learning_statistics: dict[str, Any] = Field(default_factory=dict)
    pending_count: int = 0
    evaluated_count: int = 0
    insufficient_count: int = 0


class PredictionValidationStatistics(BaseModel):
    total: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)
    average_absolute_error: float | None = None
    average_percentage_error: float | None = None
    average_validation_score: float | None = None
    average_learning_score: float | None = None
    direction_correct_rate: float | None = None
    with_observation: int = 0
    without_observation: int = 0


class PredictionValidationCollection(BaseModel):
    """Collection of prediction validations and learning records."""

    model_config = ConfigDict(extra="allow")

    collection_id: str
    schema_version: str = PREDICTION_VALIDATION_SCHEMA_VERSION
    dataset_id: str | None = None
    domain: str | None = None
    validations: list[PredictionValidation] = Field(default_factory=list)
    learning_records: list[PredictionLearningRecord] = Field(default_factory=list)
    summary: LearningSummary = Field(default_factory=LearningSummary)
    statistics: PredictionValidationStatistics = Field(
        default_factory=PredictionValidationStatistics
    )
    generated_at: str = ""
    metadata: PredictionValidationMetadata = Field(default_factory=PredictionValidationMetadata)
