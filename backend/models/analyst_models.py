from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

ANALYST_RUNTIME_SCHEMA_VERSION = "1.0.0"

ANALYST_RUNTIME_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "rest_api",
    "ui_chat",
    "auth",
    "billing",
    "evaluation",
)


def empty_analyst_runtime_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in ANALYST_RUNTIME_FUTURE_EXTENSION_KEYS}


class AnalystSessionStatus(str, Enum):
    created = "created"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class AnalystRequest(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    query: str
    user_context: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None
    follow_up: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalystResponse(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    answer: str = ""
    insights: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    workflow_results: dict[str, Any] = Field(default_factory=dict)
    structured_output: dict[str, Any] = Field(default_factory=dict)
    validation_status: str = "unchecked"
    provider: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalystSession(BaseModel):
    """Runtime AI Analyst session — functional orchestration record."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    session_id: str
    user_query: str
    context: dict[str, Any] = Field(default_factory=dict)
    workflow_id: str = ""
    status: AnalystSessionStatus = AnalystSessionStatus.created
    result: AnalystResponse | None = None
    previous_queries: list[str] = Field(default_factory=list)
    previous_results: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    schema_version: str = ANALYST_RUNTIME_SCHEMA_VERSION
    metadata: dict[str, Any] = Field(default_factory=dict)
