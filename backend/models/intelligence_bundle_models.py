from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.models.ai_insight_models import UniversalAIInsightCollection, ValidationStatus
from backend.models.decision_models import DecisionCollection
from backend.models.executive_reasoning_models import ExecutiveReasoningCollection
from backend.models.root_cause_models import RootCauseCollection
from backend.models.storyboard_models import ExecutiveStoryboard
from backend.models.validation_models import ValidationReport

INTELLIGENCE_BUNDLE_SCHEMA_VERSION = "1.0.0"

# Reserved empty buckets for future consumers. Placeholders only.
# Owners:
#   api             → Future REST APIs
#   chat            → AI Analyst Chat
#   prediction      → Prediction Engine
#   workflow        → Workflow Engine
#   automation      → Automation Engine
#   knowledge_graph → Knowledge Graph Engine
#   agent_memory    → Multi-Agent Memory Layer
#   vector_index    → Vector Index Layer
#   semantic_search → Semantic Search Layer
INTELLIGENCE_BUNDLE_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "api",
    "chat",
    "prediction",
    "workflow",
    "automation",
    "knowledge_graph",
    "agent_memory",
    "vector_index",
    "semantic_search",
)


def empty_intelligence_bundle_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in INTELLIGENCE_BUNDLE_FUTURE_EXTENSION_KEYS}


class BundleReferences(BaseModel):
    """Traceability IDs only — no duplicated payloads."""

    insight_ids: list[str] = Field(default_factory=list)
    decision_ids: list[str] = Field(default_factory=list)
    root_cause_ids: list[str] = Field(default_factory=list)
    storyboard_ids: list[str] = Field(default_factory=list)
    validation_ids: list[str] = Field(default_factory=list)
    reasoning_ids: list[str] = Field(default_factory=list)


class BundleStatistics(BaseModel):
    """Aggregated counts and averages from existing objects only."""

    counts: dict[str, int] = Field(default_factory=dict)
    confidence_averages: dict[str, float] = Field(default_factory=dict)
    validation_averages: dict[str, float] = Field(default_factory=dict)
    risk_distribution: dict[str, int] = Field(default_factory=dict)
    priority_distribution: dict[str, int] = Field(default_factory=dict)
    category_distribution: dict[str, int] = Field(default_factory=dict)


class BundleSummary(BaseModel):
    dataset_id: str | None = None
    domain: str | None = None
    overall_health: str = ""
    overall_validation: ValidationStatus = ValidationStatus.pending
    total_insights: int = 0
    total_decisions: int = 0
    total_root_causes: int = 0
    total_storyboards: int = 0
    total_reasonings: int = 0
    total_validations: int = 0
    generated_at: str = ""


class BundleMetadata(BaseModel):
    legacy: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    future_extensions: dict[str, Any] = Field(default_factory=empty_intelligence_bundle_future_extensions)


class IntelligenceBundle(BaseModel):
    """Canonical orchestration entry point. References existing intelligence objects only."""

    model_config = ConfigDict(extra="allow")

    bundle_id: str
    schema_version: str = INTELLIGENCE_BUNDLE_SCHEMA_VERSION
    dataset_id: str | None = None
    domain: str | None = None
    insights: UniversalAIInsightCollection | None = None
    validations: list[ValidationReport] = Field(default_factory=list)
    decisions: DecisionCollection | None = None
    root_causes: RootCauseCollection | None = None
    reasonings: ExecutiveReasoningCollection | None = None
    storyboard: ExecutiveStoryboard | None = None
    summary: BundleSummary = Field(default_factory=BundleSummary)
    statistics: BundleStatistics = Field(default_factory=BundleStatistics)
    references: BundleReferences = Field(default_factory=BundleReferences)
    generated_at: str
    metadata: BundleMetadata = Field(default_factory=BundleMetadata)
