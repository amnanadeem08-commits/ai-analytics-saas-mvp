from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

FORECAST_EXPLAINABILITY_SCHEMA_VERSION = "1.0.0"

# Reserved empty buckets for future explanation engines. Placeholders only.
FORECAST_EXPLAINABILITY_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "shap",
    "lime",
    "feature_importance",
    "attention_maps",
    "counterfactuals",
    "causal_reasoning",
    "uncertainty_analysis",
    "probabilistic_explanations",
    "model_cards",
    "decision_trace",
    "llm_explanations",
)

REQUIRED_SECTION_TYPES: tuple[str, ...] = (
    "overview",
    "assumptions",
    "drivers",
    "evidence",
    "limitations",
    "confidence",
    "traceability",
    "references",
)


def empty_forecast_explainability_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in FORECAST_EXPLAINABILITY_FUTURE_EXTENSION_KEYS}


class ExplanationStatus(str, Enum):
    planned = "planned"
    available = "available"
    partial = "partial"
    insufficient = "insufficient"
    deprecated = "deprecated"


class SectionType(str, Enum):
    overview = "overview"
    assumptions = "assumptions"
    drivers = "drivers"
    evidence = "evidence"
    limitations = "limitations"
    confidence = "confidence"
    traceability = "traceability"
    references = "references"


# Canonical default sections in display order — representation only.
DEFAULT_EXPLANATION_SECTION_SPECS: tuple[tuple[str, str, SectionType], ...] = (
    ("sec_overview", "Overview", SectionType.overview),
    ("sec_forecast_horizon", "Forecast Horizon", SectionType.overview),
    ("sec_confidence", "Confidence", SectionType.confidence),
    ("sec_key_drivers", "Key Drivers", SectionType.drivers),
    ("sec_supporting_evidence", "Supporting Evidence", SectionType.evidence),
    ("sec_assumptions", "Assumptions", SectionType.assumptions),
    ("sec_limitations", "Limitations", SectionType.limitations),
    ("sec_traceability", "Traceability", SectionType.traceability),
    ("sec_references", "References", SectionType.references),
)


class ExplanationSection(BaseModel):
    """One explainability section. Metadata / template only — never computes attributions."""

    model_config = ConfigDict(extra="allow")

    section_id: str
    section_name: str
    section_type: SectionType
    display_order: int = 0
    content: str = ""
    references: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExplanationTraceability(BaseModel):
    """Trace links only. No execution or model introspection."""

    prediction_id: str | None = None
    dataset_id: str | None = None
    scenario_id: str | None = None
    adapter_id: str | None = None
    related_predictions: list[str] = Field(default_factory=list)
    related_decisions: list[str] = Field(default_factory=list)
    related_root_causes: list[str] = Field(default_factory=list)
    section_ids: list[str] = Field(default_factory=list)


class ExplanationMetadata(BaseModel):
    legacy: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    future_extensions: dict[str, Any] = Field(
        default_factory=empty_forecast_explainability_future_extensions
    )


class ExplanationStatistics(BaseModel):
    total_sections: int = 0
    completed_sections: int = 0
    empty_sections: int = 0
    reference_count: int = 0
    driver_count: int = 0
    assumption_count: int = 0
    limitation_count: int = 0


class ExplanationSummary(BaseModel):
    explanation_status: str = ""
    forecast_horizon: str = ""
    confidence_level: str = ""
    section_count: int = 0
    reference_count: int = 0
    driver_count: int = 0
    overall_completeness: str = "unknown"


class ForecastExplanation(BaseModel):
    """Canonical forecast explanation object. Metadata only — never explains models."""

    model_config = ConfigDict(extra="allow")

    explanation_id: str
    prediction_id: str | None = None
    dataset_id: str | None = None
    scenario_id: str | None = None
    adapter_id: str | None = None
    explanation_status: ExplanationStatus = ExplanationStatus.planned
    summary: str = ""
    forecast_horizon: str = ""
    confidence_level: str = ""
    key_drivers: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    related_predictions: list[str] = Field(default_factory=list)
    related_decisions: list[str] = Field(default_factory=list)
    related_root_causes: list[str] = Field(default_factory=list)
    sections: list[ExplanationSection] = Field(default_factory=list)
    traceability: ExplanationTraceability = Field(default_factory=ExplanationTraceability)
    created_at: str = ""
    updated_at: str = ""
    metadata: ExplanationMetadata = Field(default_factory=ExplanationMetadata)
    schema_version: str = FORECAST_EXPLAINABILITY_SCHEMA_VERSION
