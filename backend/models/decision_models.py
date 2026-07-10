from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.models.ai_insight_models import (
    AI_INSIGHT_SCHEMA_VERSION,
    EffortLevel,
    InsightPriority,
    RiskLevel,
    UrgencyLevel,
    ValidationStatus,
)

DECISION_SCHEMA_VERSION = "1.0.0"


class DecisionCategory(str, Enum):
    revenue_growth = "Revenue Growth"
    cost_reduction = "Cost Reduction"
    operational_improvement = "Operational Improvement"
    risk_mitigation = "Risk Mitigation"
    customer_experience = "Customer Experience"
    compliance = "Compliance"
    forecasting = "Forecasting"
    strategic_planning = "Strategic Planning"
    data_quality = "Data Quality"
    other = "Other"


class DecisionStatus(str, Enum):
    complete = "complete"
    incomplete = "incomplete"
    blocked = "blocked"


class DecisionTimeHorizon(str, Enum):
    immediate = "Immediate"
    short_term = "ShortTerm"
    medium_term = "MediumTerm"
    long_term = "LongTerm"


class DecisionMetadata(BaseModel):
    """Structured metadata with reserved buckets for downstream engines."""

    legacy: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    future_extensions: dict[str, Any] = Field(
        default_factory=lambda: {
            "prediction": {},
            "simulation": {},
            "workflow": {},
            "approval": {},
            "automation": {},
        }
    )


class DecisionEvidence(BaseModel):
    label: str
    value: Any = None
    evidence_type: str = "text"
    source: str = ""
    confidence_score: float | None = None
    raw: dict[str, Any] | None = None


class ExpectedOutcomeTarget(BaseModel):
    target_metric: str = ""
    target_value: Any = None
    target_timeframe: str = ""


class DecisionAlternative(BaseModel):
    action: str
    advantages: list[str] = Field(default_factory=list)
    disadvantages: list[str] = Field(default_factory=list)
    expected_outcome: str = ""
    expected_outcome_target: ExpectedOutcomeTarget | None = None
    estimated_effort: EffortLevel = EffortLevel.unknown
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class DecisionPathStep(BaseModel):
    step_id: str
    label: str
    detail: str
    source_field: str = ""


class DecisionRecommendation(BaseModel):
    model_config = ConfigDict(extra="allow")

    decision_id: str
    schema_version: str = DECISION_SCHEMA_VERSION
    title: str
    summary: str
    recommended_action: str = ""
    business_reason: str = ""
    expected_outcome: str = ""
    expected_outcome_target: ExpectedOutcomeTarget | None = None
    business_impact: str = ""
    priority: InsightPriority = InsightPriority.medium
    urgency: UrgencyLevel = UrgencyLevel.unknown
    risk_level: RiskLevel = RiskLevel.info
    estimated_effort: EffortLevel = EffortLevel.unknown
    estimated_value: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    supporting_evidence: list[DecisionEvidence] = Field(default_factory=list)
    affected_metrics: list[str] = Field(default_factory=list)
    related_kpis: list[str] = Field(default_factory=list)
    related_charts: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    implementation_notes: list[str] = Field(default_factory=list)
    validation_status: ValidationStatus = ValidationStatus.pending
    category: DecisionCategory = DecisionCategory.other
    status: DecisionStatus = DecisionStatus.incomplete
    time_horizon: DecisionTimeHorizon = DecisionTimeHorizon.medium_term
    alternatives: list[DecisionAlternative] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    blocks: list[str] = Field(default_factory=list)
    decision_score: float = Field(default=0.0, ge=0.0, le=100.0)
    decision_rank: int | None = None
    decision_path: list[DecisionPathStep] = Field(default_factory=list)
    source_insight_id: str = ""
    source_dataset: str | None = None
    source_validation_report: dict[str, Any] | None = None
    source_schema_version: str = AI_INSIGHT_SCHEMA_VERSION
    generated_at: str
    metadata: DecisionMetadata = Field(default_factory=DecisionMetadata)


class DecisionSummary(BaseModel):
    total_decisions: int = 0
    complete_count: int = 0
    incomplete_count: int = 0
    blocked_count: int = 0
    top_priority_decision_id: str | None = None
    category_breakdown: dict[str, int] = Field(default_factory=dict)
    headline: str = ""
    executive_note: str = ""
    overall_business_health: str = ""
    top_risks: list[str] = Field(default_factory=list)
    top_opportunities: list[str] = Field(default_factory=list)
    quick_wins: list[str] = Field(default_factory=list)
    strategic_actions: list[str] = Field(default_factory=list)


class DecisionCollection(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str = DECISION_SCHEMA_VERSION
    dataset_id: str | None = None
    domain: str | None = None
    decisions: list[DecisionRecommendation] = Field(default_factory=list)
    summary: DecisionSummary = Field(default_factory=DecisionSummary)
    generated_at: str
    metadata: DecisionMetadata = Field(default_factory=DecisionMetadata)
