from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

AGENT_SCHEMA_VERSION = "1.0.0"

AGENT_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "memory",
    "multi_turn",
    "planning",
    "collaboration",
    "autonomy",
    "prompt_guardrails",
)


def empty_agent_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in AGENT_FUTURE_EXTENSION_KEYS}


class AgentRole(str, Enum):
    data_analyst = "data_analyst"
    insight = "insight"
    validation = "validation"
    reporting = "reporting"
    custom = "custom"


class AgentStatus(str, Enum):
    created = "created"
    assigned = "assigned"
    running = "running"
    tool_execution = "tool_execution"
    completed = "completed"
    failed = "failed"


class AgentDefinition(BaseModel):
    """Specialized agent that selects approved tools and returns structured results."""

    model_config = ConfigDict(extra="allow")

    agent_id: str
    agent_name: str
    role: AgentRole
    description: str = ""
    allowed_tools: list[str] = Field(default_factory=list)
    system_prompt: str = ""
    enabled: bool = True
    max_tool_calls: int = 5
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentTask(BaseModel):
    model_config = ConfigDict(extra="allow")

    task_id: str
    agent_id: str
    objective: str = ""
    input_context_keys: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = 0
    created_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    result_id: str
    agent_id: str
    task_id: str
    status: AgentStatus = AgentStatus.completed
    summary: str = ""
    findings: list[str] = Field(default_factory=list)
    tool_calls: list[str] = Field(default_factory=list)
    outputs: dict[str, Any] = Field(default_factory=dict)
    context_updates: dict[str, Any] = Field(default_factory=dict)
    error_message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentExecution(BaseModel):
    """Lifecycle record for one agent run."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    execution_id: str
    agent_id: str
    task_id: str
    status: AgentStatus = AgentStatus.created
    started_at: str = ""
    finished_at: str = ""
    duration_ms: float | None = None
    tool_request_ids: list[str] = Field(default_factory=list)
    result: AgentResult | None = None
    logs: list[str] = Field(default_factory=list)
    error_message: str = ""
    schema_version: str = AGENT_SCHEMA_VERSION
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentRegistry(BaseModel):
    model_config = ConfigDict(extra="allow")

    registry_id: str
    agents: list[AgentDefinition] = Field(default_factory=list)
    generated_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
