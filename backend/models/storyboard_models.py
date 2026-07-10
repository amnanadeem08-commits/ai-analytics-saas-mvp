from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.models.ai_insight_models import ValidationStatus

STORYBOARD_SCHEMA_VERSION = "1.0.0"

# Reserved empty buckets for export / presentation consumers. Placeholders only.
# Owners:
#   ppt               → PowerPoint export
#   pdf               → PDF export
#   dashboard         → Interactive dashboard
#   board_pack        → Board pack packaging
#   executive_brief   → Executive brief export
#   interactive_story → Interactive story experience
STORYBOARD_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "ppt",
    "pdf",
    "dashboard",
    "board_pack",
    "executive_brief",
    "interactive_story",
)


def empty_storyboard_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in STORYBOARD_FUTURE_EXTENSION_KEYS}


class StoryboardSlideType(str, Enum):
    executive_summary = "Executive Summary"
    business_health = "Business Health"
    key_findings = "Key Findings"
    root_causes = "Root Causes"
    business_risks = "Business Risks"
    business_opportunities = "Business Opportunities"
    recommended_decisions = "Recommended Decisions"
    priority_roadmap = "Priority Roadmap"
    kpi_highlights = "KPI Highlights"
    supporting_evidence = "Supporting Evidence"
    appendix = "Appendix"


# Canonical presentation order — do not invent slides outside this sequence.
STORYBOARD_SLIDE_ORDER: tuple[StoryboardSlideType, ...] = (
    StoryboardSlideType.executive_summary,
    StoryboardSlideType.business_health,
    StoryboardSlideType.key_findings,
    StoryboardSlideType.root_causes,
    StoryboardSlideType.business_risks,
    StoryboardSlideType.business_opportunities,
    StoryboardSlideType.recommended_decisions,
    StoryboardSlideType.priority_roadmap,
    StoryboardSlideType.kpi_highlights,
    StoryboardSlideType.supporting_evidence,
    StoryboardSlideType.appendix,
)


class StoryboardSectionId(str, Enum):
    overview = "overview"
    analysis = "analysis"
    actions = "actions"
    evidence = "evidence"
    appendix = "appendix"


class StoryboardMetadata(BaseModel):
    """Presentation metadata with reserved future_extensions for export engines."""

    legacy: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    future_extensions: dict[str, Any] = Field(default_factory=empty_storyboard_future_extensions)
    linked_insight_ids: list[str] = Field(default_factory=list)
    linked_decision_ids: list[str] = Field(default_factory=list)
    linked_root_cause_ids: list[str] = Field(default_factory=list)
    linked_validation_report_ids: list[str] = Field(default_factory=list)
    linked_reasoning_ids: list[str] = Field(default_factory=list)


class StoryboardSlide(BaseModel):
    """One presentation slide. Content is copied from validated upstream objects only."""

    model_config = ConfigDict(extra="allow")

    slide_id: str
    slide_type: StoryboardSlideType
    title: str
    order: int
    bullets: list[str] = Field(default_factory=list)
    body: str = ""
    linked_insight_ids: list[str] = Field(default_factory=list)
    linked_decision_ids: list[str] = Field(default_factory=list)
    linked_root_cause_ids: list[str] = Field(default_factory=list)
    linked_validation_report_ids: list[str] = Field(default_factory=list)
    linked_reasoning_ids: list[str] = Field(default_factory=list)
    metadata: StoryboardMetadata = Field(default_factory=StoryboardMetadata)


class StoryboardSection(BaseModel):
    model_config = ConfigDict(extra="allow")

    section_id: StoryboardSectionId
    title: str
    order: int
    slides: list[StoryboardSlide] = Field(default_factory=list)
    metadata: StoryboardMetadata = Field(default_factory=StoryboardMetadata)


class StoryboardSummary(BaseModel):
    headline: str = ""
    slide_count: int = 0
    section_count: int = 0
    domain: str | None = None
    validation_status: ValidationStatus = ValidationStatus.pending
    top_priority_action: str = ""
    top_risk: str = ""
    top_opportunity: str = ""
    top_root_cause: str = ""
    executive_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ExecutiveStoryboard(BaseModel):
    """Presentation orchestration of executive intelligence. Consumer only."""

    model_config = ConfigDict(extra="allow")

    storyboard_id: str
    schema_version: str = STORYBOARD_SCHEMA_VERSION
    dataset_id: str | None = None
    domain: str | None = None
    title: str = ""
    sections: list[StoryboardSection] = Field(default_factory=list)
    slides: list[StoryboardSlide] = Field(default_factory=list)
    summary: StoryboardSummary = Field(default_factory=StoryboardSummary)
    generated_at: str
    metadata: StoryboardMetadata = Field(default_factory=StoryboardMetadata)


class StoryboardCollection(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str = STORYBOARD_SCHEMA_VERSION
    dataset_id: str | None = None
    storyboards: list[ExecutiveStoryboard] = Field(default_factory=list)
    generated_at: str
    metadata: StoryboardMetadata = Field(default_factory=StoryboardMetadata)
