from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

PREDICTION_SCHEMA_VERSION = "1.0.0"

# Reserved empty buckets for future forecasting layers. Placeholders only.
# Owners:
#   machine_learning       → ML model training / inference
#   time_series            → Time-series forecasting
#   forecasting            → General forecasting engine
#   anomaly_detection      → Anomaly detection
#   reinforcement_learning → RL-based prediction
#   digital_twin           → Digital twin simulation
#   causal_prediction      → Causal prediction
#   simulation             → Simulation engine
#   optimizer              → Optimization layer
#   ensemble_models        → Ensemble model stacking
PREDICTION_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "machine_learning",
    "time_series",
    "forecasting",
    "anomaly_detection",
    "reinforcement_learning",
    "digital_twin",
    "causal_prediction",
    "simulation",
    "optimizer",
    "ensemble_models",
)


def empty_prediction_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in PREDICTION_FUTURE_EXTENSION_KEYS}


class PredictionType(str, Enum):
    revenue = "Revenue"
    sales = "Sales"
    demand = "Demand"
    inventory = "Inventory"
    customer = "Customer"
    risk = "Risk"
    business_kpi = "Business KPI"
    operational = "Operational"
    financial = "Financial"
    custom = "Custom"


class PredictionStatus(str, Enum):
    draft = "draft"
    ready = "ready"
    insufficient = "insufficient"
    rejected = "rejected"


class PredictionTimeHorizon(str, Enum):
    immediate = "Immediate"
    short_term = "ShortTerm"
    medium_term = "MediumTerm"
    long_term = "LongTerm"
    unknown = "Unknown"


class ScenarioKind(str, Enum):
    """Scenario metadata only — no Monte Carlo / ML sampling."""

    baseline = "Baseline"
    optimistic = "Optimistic"
    pessimistic = "Pessimistic"
    expected = "Expected"


class PredictionEvidence(BaseModel):
    """Pointer to existing intelligence. Never invents values."""

    evidence_id: str
    object_type: str
    object_id: str
    label: str = ""
    field: str = ""
    value: Any = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class PredictionExplanation(BaseModel):
    """Human-readable justification assembled from existing fields only."""

    explanation_id: str
    headline: str = ""
    rationale: str = ""
    drivers: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    unavailable_note: str = ""


class PredictionScenario(BaseModel):
    """Named scenario metadata. No stochastic simulation."""

    scenario_id: str
    kind: ScenarioKind
    label: str = ""
    description: str = ""
    predicted_value: Any = None
    prediction_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    assumptions: list[str] = Field(default_factory=list)
    linked_prediction_id: str = ""


class PredictionRange(BaseModel):
    """Optional range copied from existing evidence when available."""

    lower: Any = None
    upper: Any = None
    unit: str = ""
    source: str = ""


class ConfidenceInterval(BaseModel):
    """Interval metadata only — not a statistical CI from ML."""

    lower_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    upper_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    method: str = "existing_intelligence_bounds"
    note: str = ""


class PredictionMetadata(BaseModel):
    legacy: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    future_extensions: dict[str, Any] = Field(default_factory=empty_prediction_future_extensions)


class Prediction(BaseModel):
    """Structured prediction object derived from existing platform intelligence."""

    model_config = ConfigDict(extra="allow")

    prediction_id: str
    schema_version: str = PREDICTION_SCHEMA_VERSION
    prediction_type: PredictionType = PredictionType.custom
    title: str
    summary: str = ""
    predicted_metric: str = ""
    predicted_value: Any = None
    prediction_range: PredictionRange = Field(default_factory=PredictionRange)
    confidence_interval: ConfidenceInterval = Field(default_factory=ConfidenceInterval)
    time_horizon: PredictionTimeHorizon = PredictionTimeHorizon.unknown
    prediction_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    prediction_status: PredictionStatus = PredictionStatus.draft
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    supporting_decisions: list[str] = Field(default_factory=list)
    supporting_root_causes: list[str] = Field(default_factory=list)
    supporting_insights: list[str] = Field(default_factory=list)
    validation_reference: list[str] = Field(default_factory=list)
    reasoning_reference: list[str] = Field(default_factory=list)
    registry_reference: list[str] = Field(default_factory=list)
    analyst_reference: list[str] = Field(default_factory=list)
    bundle_reference: str | None = None
    storyboard_reference: str | None = None
    scenarios: list[PredictionScenario] = Field(default_factory=list)
    explanation: PredictionExplanation | None = None
    evidence: list[PredictionEvidence] = Field(default_factory=list)
    prediction_rank: int | None = None
    dataset_id: str | None = None
    domain: str | None = None
    generated_at: str = ""
    metadata: PredictionMetadata = Field(default_factory=PredictionMetadata)


class PredictionSummary(BaseModel):
    total_predictions: int = 0
    ready_count: int = 0
    insufficient_count: int = 0
    rejected_count: int = 0
    draft_count: int = 0
    type_breakdown: dict[str, int] = Field(default_factory=dict)
    top_prediction_id: str | None = None
    headline: str = ""
    average_confidence: float | None = None
    datasets: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)


class PredictionStatistics(BaseModel):
    counts: dict[str, int] = Field(default_factory=dict)
    by_type: dict[str, int] = Field(default_factory=dict)
    by_status: dict[str, int] = Field(default_factory=dict)
    by_horizon: dict[str, int] = Field(default_factory=dict)
    confidence_average: float | None = None
    scenario_counts: dict[str, int] = Field(default_factory=dict)
    with_evidence: int = 0
    without_evidence: int = 0


class PredictionCollection(BaseModel):
    """Bundle of predictions for a dataset / domain."""

    model_config = ConfigDict(extra="allow")

    collection_id: str
    schema_version: str = PREDICTION_SCHEMA_VERSION
    dataset_id: str | None = None
    domain: str | None = None
    predictions: list[Prediction] = Field(default_factory=list)
    summary: PredictionSummary = Field(default_factory=PredictionSummary)
    statistics: PredictionStatistics = Field(default_factory=PredictionStatistics)
    generated_at: str = ""
    metadata: PredictionMetadata = Field(default_factory=PredictionMetadata)
