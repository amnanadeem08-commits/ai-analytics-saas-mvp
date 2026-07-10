from typing import Any

from pydantic import BaseModel, ConfigDict


class ReportPreviewResponse(BaseModel):
    """Loose schema for the JSON report preview endpoint."""

    model_config = ConfigDict(extra="allow")

    dataset_id: str
    branding: dict[str, Any]
    theme: dict[str, Any]
    overview: dict[str, Any]
    kpi_cards: list[dict[str, Any]]
    executive_summary: dict[str, Any]
    business_story: dict[str, Any]
    domain_intelligence: dict[str, Any] = {}
    regional_analytics: dict[str, Any] = {}
    analysis_guardrails: dict[str, Any] = {}
    data_quality_score: dict[str, Any] = {}
    suggested_questions: list[str] = []
    chart_specs: list[dict[str, Any]]
    chart_count: int
