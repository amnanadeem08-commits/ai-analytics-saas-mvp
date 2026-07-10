from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.models.ai_insight_models import InsightPriority, RiskLevel, ValidationStatus

EXECUTIVE_REASONING_SCHEMA_VERSION = "1.0.0"

# Reserved empty buckets for downstream consumers. Placeholders only.
# Owners:
#   storyboard      → Executive Storyboard
#   chat            → AI Analyst Chat
#   prediction      → Prediction Engine
#   workflow        → Workflow Engine
#   automation      → Automation Engine
#   knowledge_graph → Knowledge Graph Engine
#   agent_memory    → Multi-Agent Memory Layer
#   llm_planning    → LLM Planning / Executive Reasoning extensions
EXECUTIVE_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "storyboard",
    "chat",
    "prediction",
    "workflow",
    "automation",
    "knowledge_graph",
    "agent_memory",
    "llm_planning",
)


def empty_executive_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in EXECUTIVE_FUTURE_EXTENSION_KEYS}


class ExecutiveFindingType(str, Enum):
    what_happened = "what_happened"
    why_it_happened = "why_it_happened"
    business_impact = "business_impact"
    validation = "validation"
    other = "other"


class ExecutiveMetadata(BaseModel):
    """Structured metadata with reserved future_extensions for Sprint 5.8+ consumers."""

    legacy: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    future_extensions: dict[str, Any] = Field(default_factory=empty_executive_future_extensions)
    # Provenance references for every executive statement
    linked_insight_ids: list[str] = Field(default_factory=list)
    linked_decision_ids: list[str] = Field(default_factory=list)
    linked_root_cause_ids: list[str] = Field(default_factory=list)
    linked_validation_report_ids: list[str] = Field(default_factory=list)


class ExecutiveFinding(BaseModel):
    finding_id: str
    finding_type: ExecutiveFindingType = ExecutiveFindingType.other
    title: str
    statement: str
    source_insight_ids: list[str] = Field(default_factory=list)
    source_decision_ids: list[str] = Field(default_factory=list)
    source_root_cause_ids: list[str] = Field(default_factory=list)
    source_validation_report_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ExecutiveRisk(BaseModel):
    risk_id: str
    title: str
    description: str
    severity: RiskLevel = RiskLevel.info
    source_decision_ids: list[str] = Field(default_factory=list)
    source_root_cause_ids: list[str] = Field(default_factory=list)
    source_validation_warnings: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ExecutiveOpportunity(BaseModel):
    opportunity_id: str
    title: str
    description: str
    expected_outcome: str = ""
    source_decision_ids: list[str] = Field(default_factory=list)
    source_insight_ids: list[str] = Field(default_factory=list)
    time_horizon: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ExecutiveRecommendation(BaseModel):
    """Prioritized view of an existing DecisionRecommendation — never newly invented."""

    recommendation_id: str
    decision_id: str
    title: str
    recommended_action: str
    business_reason: str = ""
    expected_outcome: str = ""
    business_impact: str = ""
    priority: InsightPriority = InsightPriority.medium
    decision_score: float = Field(default=0.0, ge=0.0, le=100.0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    rank: int | None = None


class ExecutivePriority(BaseModel):
    priority_id: str
    label: str
    rationale: str
    linked_decision_ids: list[str] = Field(default_factory=list)
    order: int = 0


class ExecutiveNarrative(BaseModel):
    what_happened: str = ""
    why_it_happened: str = ""
    business_impact: str = ""
    recommended_priority: str = ""
    confidence_statement: str = ""
    validation_status: ValidationStatus = ValidationStatus.pending
    top_risks: list[str] = Field(default_factory=list)
    top_opportunities: list[str] = Field(default_factory=list)


class ExecutiveReasoningSummary(BaseModel):
    total_reasonings: int = 0
    domains: list[str] = Field(default_factory=list)
    headline: str = ""
    top_priority_action: str = ""
    top_risk: str = ""
    top_opportunity: str = ""
    average_executive_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    validation_status_breakdown: dict[str, int] = Field(default_factory=dict)


class ExecutiveReasoning(BaseModel):
    """Orchestrated executive intelligence object. Does not regenerate upstream engines."""

    model_config = ConfigDict(extra="allow")

    reasoning_id: str
    schema_version: str = EXECUTIVE_REASONING_SCHEMA_VERSION
    dataset_id: str | None = None
    domain: str | None = None
    headline: str = ""
    executive_summary: str = ""
    business_context: str = ""
    narrative: ExecutiveNarrative = Field(default_factory=ExecutiveNarrative)
    key_findings: list[ExecutiveFinding] = Field(default_factory=list)
    key_risks: list[ExecutiveRisk] = Field(default_factory=list)
    key_opportunities: list[ExecutiveOpportunity] = Field(default_factory=list)
    recommended_priorities: list[ExecutivePriority] = Field(default_factory=list)
    prioritized_recommendations: list[ExecutiveRecommendation] = Field(default_factory=list)
    executive_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    overall_validation_status: ValidationStatus = ValidationStatus.pending
    linked_insight_ids: list[str] = Field(default_factory=list)
    linked_decision_ids: list[str] = Field(default_factory=list)
    linked_root_cause_ids: list[str] = Field(default_factory=list)
    reasoning_rank: int | None = None
    generated_at: str
    metadata: ExecutiveMetadata = Field(default_factory=ExecutiveMetadata)


class ExecutiveReasoningCollection(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str = EXECUTIVE_REASONING_SCHEMA_VERSION
    dataset_id: str | None = None
    domain: str | None = None
    reasonings: list[ExecutiveReasoning] = Field(default_factory=list)
    summary: ExecutiveReasoningSummary = Field(default_factory=ExecutiveReasoningSummary)
    generated_at: str
    metadata: ExecutiveMetadata = Field(default_factory=ExecutiveMetadata)
