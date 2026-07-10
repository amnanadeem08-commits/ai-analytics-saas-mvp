from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AnalystAnalyzeRequest(BaseModel):
    """Request body for AI Analyst analysis."""

    model_config = ConfigDict(extra="allow")

    query: str = Field(..., min_length=1, description="User analysis query")
    user_context: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None
    follow_up: bool = False
    initial_context: dict[str, Any] = Field(default_factory=dict)


class AnalystAnalyzeResponse(BaseModel):
    """Structured analyst response returned by the runtime."""

    model_config = ConfigDict(extra="allow")

    success: bool = True
    answer: str = ""
    insights: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    session_id: str | None = None
    workflow_id: str | None = None
    validation_status: str = "unchecked"
    provider: str = ""
    evaluation_id: str | None = None
    evaluation_score: float | None = None
    evaluation_grade: str | None = None
    workflow_results: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    query: str = Field(..., min_length=1)
    user_context: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None
    follow_up: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionCreateResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool = True
    session_id: str
    user_query: str = ""
    status: str = "created"
    created_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool = True
    found: bool = False
    session_id: str = ""
    status: str = ""
    user_query: str = ""
    workflow_id: str = ""
    has_result: bool = False
    answer: str = ""
    insight_count: int = 0
    recommendation_count: int = 0
    previous_query_count: int = 0
    validation_status: str = "unchecked"
    updated_at: str = ""
    evaluation_id: str | None = None
    evaluation_grade: str | None = None


class SessionDetailResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool = True
    session_id: str
    user_query: str = ""
    status: str = ""
    workflow_id: str = ""
    context: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    previous_queries: list[str] = Field(default_factory=list)
    previous_results: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    initial_context: dict[str, Any] = Field(default_factory=dict)
