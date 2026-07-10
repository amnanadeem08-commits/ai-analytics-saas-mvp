from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

AI_ANALYST_SCHEMA_VERSION = "1.0.0"

# Reserved empty buckets for future layers. Placeholders only.
# Owners:
#   llm            → LLM-backed answer generation
#   agents         → Multi-agent analyst execution
#   memory         → Conversation / session memory
#   prediction     → Prediction Engine integration
#   workflow       → Workflow automation hooks
#   automation     → Automation Engine hooks
#   tool_execution → Tool / function calling
#   planning       → Multi-step planning
AI_ANALYST_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "llm",
    "agents",
    "memory",
    "prediction",
    "workflow",
    "automation",
    "tool_execution",
    "planning",
)


def empty_ai_analyst_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in AI_ANALYST_FUTURE_EXTENSION_KEYS}


class AnalystResponseMode(str, Enum):
    """Presentation mode only — underlying intelligence is identical."""

    executive = "executive"
    business = "business"
    analyst = "analyst"
    technical = "technical"
    audit = "audit"


class EvidenceReference(BaseModel):
    """Pointer to an existing intelligence object. Never invents values."""

    reference_id: str
    object_type: str
    label: str = ""
    field: str = ""
    value: str | None = None
    source_object_id: str = ""


class FollowUpQuestion(BaseModel):
    """Rule-based follow-up derived from gaps/warnings in existing intelligence."""

    question_id: str
    question: str
    rationale: str = ""
    source_gap: str = ""
    related_object_ids: list[str] = Field(default_factory=list)
    priority: str = "medium"


class ActionPlan(BaseModel):
    """Actions copied from existing decisions / executive priorities only."""

    plan_id: str
    title: str
    actions: list[str] = Field(default_factory=list)
    decision_ids: list[str] = Field(default_factory=list)
    priority_labels: list[str] = Field(default_factory=list)
    unavailable_note: str = ""


class BusinessExplanation(BaseModel):
    """Business-facing explanation assembled from existing fields only."""

    explanation_id: str
    headline: str = ""
    what_happened: str = ""
    why_it_happened: str = ""
    business_impact: str = ""
    recommended_priority: str = ""
    unavailable_fields: list[str] = Field(default_factory=list)


class ExecutiveAnswer(BaseModel):
    """Primary answer payload for one analyst response."""

    answer_id: str
    mode: AnalystResponseMode = AnalystResponseMode.executive
    question: str = ""
    headline: str = ""
    answer_text: str = ""
    key_points: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    validation_status: str = ""
    unavailable_note: str = ""
    evidence: list[EvidenceReference] = Field(default_factory=list)


class AnalystTraceability(BaseModel):
    """Mandatory source references for every answer."""

    source_bundle: str | None = None
    source_storyboard: str | None = None
    source_reasoning: list[str] = Field(default_factory=list)
    source_decisions: list[str] = Field(default_factory=list)
    source_root_causes: list[str] = Field(default_factory=list)
    source_validation: list[str] = Field(default_factory=list)
    source_insights: list[str] = Field(default_factory=list)
    registry_reference_ids: list[str] = Field(default_factory=list)


class ConversationContext(BaseModel):
    """Lightweight follow-up context. No LLM memory — structured state only."""

    context_id: str
    dataset_id: str | None = None
    domain: str | None = None
    last_question: str = ""
    last_mode: AnalystResponseMode = AnalystResponseMode.executive
    focus_decision_ids: list[str] = Field(default_factory=list)
    focus_root_cause_ids: list[str] = Field(default_factory=list)
    focus_insight_ids: list[str] = Field(default_factory=list)
    open_follow_ups: list[str] = Field(default_factory=list)
    unavailable_topics: list[str] = Field(default_factory=list)


class AnalystMetadata(BaseModel):
    legacy: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    future_extensions: dict[str, Any] = Field(default_factory=empty_ai_analyst_future_extensions)


class AIAnalystResponse(BaseModel):
    """Canonical AI Analyst output. Presentation of existing intelligence only."""

    model_config = ConfigDict(extra="allow")

    response_id: str
    schema_version: str = AI_ANALYST_SCHEMA_VERSION
    dataset_id: str | None = None
    domain: str | None = None
    mode: AnalystResponseMode = AnalystResponseMode.executive
    answer: ExecutiveAnswer
    explanation: BusinessExplanation = Field(default_factory=lambda: BusinessExplanation(explanation_id=""))
    action_plan: ActionPlan = Field(default_factory=lambda: ActionPlan(plan_id=""))
    follow_ups: list[FollowUpQuestion] = Field(default_factory=list)
    traceability: AnalystTraceability = Field(default_factory=AnalystTraceability)
    conversation_context: ConversationContext | None = None
    generated_at: str = ""
    metadata: AnalystMetadata = Field(default_factory=AnalystMetadata)
