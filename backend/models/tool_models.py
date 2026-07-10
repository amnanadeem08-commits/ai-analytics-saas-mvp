from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

TOOL_SCHEMA_VERSION = "1.0.0"

TOOL_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "remote_tools",
    "mcp",
    "rate_limiting",
    "authz",
    "sandboxing",
)


def empty_tool_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in TOOL_FUTURE_EXTENSION_KEYS}


class ToolExecutionStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    denied = "denied"
    skipped = "skipped"


class ToolDefinition(BaseModel):
    """Callable tool wrapping an existing platform capability."""

    model_config = ConfigDict(extra="allow")

    tool_id: str
    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    permission_flag: str = "internal"
    enabled: bool = True
    version: str = "1.0.0"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    request_id: str = ""
    tool_id: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    caller: str = ""
    context_keys: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolResponse(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    response_id: str = ""
    request_id: str = ""
    tool_id: str
    status: ToolExecutionStatus = ToolExecutionStatus.pending
    result: dict[str, Any] = Field(default_factory=dict)
    error_message: str = ""
    started_at: str = ""
    finished_at: str = ""
    duration_ms: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
