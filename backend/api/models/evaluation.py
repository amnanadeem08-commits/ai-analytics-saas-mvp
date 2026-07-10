from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvaluationRequest(BaseModel):
    """Optional body for triggering evaluation of a completed session."""

    model_config = ConfigDict(extra="allow")

    session_id: str | None = None
    workflow_id: str | None = None
    weights: dict[str, float] = Field(default_factory=dict)


class ScoreSummary(BaseModel):
    model_config = ConfigDict(extra="allow")

    overall_score: float = 0.0
    grade: str = "F"
    category_scores: dict[str, float] = Field(default_factory=dict)
    metric_count: int = 0


class EvaluationResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool = True
    evaluation_id: str
    workflow_id: str = ""
    session_id: str = ""
    status: str = ""
    overall_score: float = 0.0
    grade: str = "F"
    score_summary: ScoreSummary = Field(default_factory=ScoreSummary)
    created_at: str = ""


class EvaluationDetailResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool = True
    evaluation_id: str
    workflow_id: str = ""
    session_id: str = ""
    status: str = ""
    overall_score: float = 0.0
    grade: str = "F"
    report: dict[str, Any] = Field(default_factory=dict)
    metrics: list[dict[str, Any]] = Field(default_factory=list)
    category_scores: dict[str, float] = Field(default_factory=dict)
    created_at: str = ""


class EvaluationExportResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool = True
    evaluation_id: str
    export: dict[str, Any] = Field(default_factory=dict)
