from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

AI_INSIGHT_SCHEMA_VERSION = "1.0.0"


class RiskLevel(str, Enum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class InsightPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ValidationStatus(str, Enum):
    pending = "pending"
    validated = "validated"
    insufficient = "insufficient"
    rejected = "rejected"


class EffortLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    unknown = "unknown"


class UrgencyLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    immediate = "immediate"
    unknown = "unknown"


class InsightProvenance(BaseModel):
    """Identifies which engine produced an insight."""

    engine: str
    provider: str = "platform"
    engine_version: str = "1.0.0"
    model: str | None = None
    prompt_id: str | None = None


class SupportingEvidenceItem(BaseModel):
    label: str
    value: Any = None
    evidence_type: str = "text"
    source: str = ""
    confidence_score: float | None = None
    raw: dict[str, Any] | None = None


class RecommendedAction(BaseModel):
    action: str
    rationale: str = ""
    owner: str = ""
    priority: InsightPriority = InsightPriority.medium
    expected_impact: str = ""
    expected_outcome: str = ""
    estimated_effort: EffortLevel = EffortLevel.unknown
    urgency: UrgencyLevel = UrgencyLevel.unknown
    evidence_refs: list[str] = Field(default_factory=list)


class DataQualityScore(BaseModel):
    model_config = ConfigDict(extra="allow")

    score: float | None = None
    grade: str = ""
    completeness_pct: float | None = None
    dimensions: dict[str, Any] = Field(default_factory=dict)


class InsightMetadata(BaseModel):
    """Structured extension buckets for stable long-term evolution."""

    legacy: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    future_extensions: dict[str, Any] = Field(default_factory=dict)


class UniversalAIInsight(BaseModel):
    """Canonical AI insight contract for all platform intelligence outputs."""

    model_config = ConfigDict(extra="allow")

    id: str
    schema_version: str = AI_INSIGHT_SCHEMA_VERSION
    title: str
    summary: str
    insight: str
    reason: str = ""
    supporting_evidence: list[SupportingEvidenceItem] = Field(default_factory=list)
    affected_metrics: list[str] = Field(default_factory=list)
    business_impact: str = ""
    expected_outcome: str = ""
    risk_level: RiskLevel = RiskLevel.info
    priority: InsightPriority = InsightPriority.medium
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    data_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence_reason: str = ""
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    related_charts: list[str] = Field(default_factory=list)
    related_kpis: list[str] = Field(default_factory=list)
    domain: str | None = None
    generated_by: InsightProvenance
    generated_at: str
    validation_status: ValidationStatus = ValidationStatus.pending
    data_quality_score: DataQualityScore | None = None
    metadata: InsightMetadata = Field(default_factory=InsightMetadata)

    @field_validator("generated_at")
    @classmethod
    def validate_generated_at(cls, value: str) -> str:
        if not value:
            raise ValueError("generated_at is required")
        return value


class UniversalAIInsightCollection(BaseModel):
    """Bundle of normalized insights for export, validation, and future APIs."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = AI_INSIGHT_SCHEMA_VERSION
    dataset_id: str | None = None
    domain: str | None = None
    insights: list[UniversalAIInsight] = Field(default_factory=list)
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    metadata: InsightMetadata = Field(default_factory=InsightMetadata)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def compute_overall_confidence(data_confidence: float, reasoning_confidence: float) -> float:
    scores = [score for score in (data_confidence, reasoning_confidence) if score > 0]
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 4)
