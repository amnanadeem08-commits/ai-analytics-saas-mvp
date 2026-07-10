from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

PLANNING_SCHEMA_VERSION = "1.0.0"

PLANNING_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "multi_agent_collaboration",
    "adaptive_replanning",
    "cost_aware_planning",
    "human_in_the_loop",
)


def empty_planning_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in PLANNING_FUTURE_EXTENSION_KEYS}


class PlanStepStatus(str, Enum):
    pending = "pending"
    ready = "ready"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"
    retried = "retried"


class PlanStatus(str, Enum):
    draft = "draft"
    ready = "ready"
    running = "running"
    completed = "completed"
    failed = "failed"
    partial = "partial"


class PlanStep(BaseModel):
    """One executable step in an agent plan."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    step_id: str
    description: str = ""
    agent_name: str = ""
    tool_name: str = ""
    input_data: dict[str, Any] = Field(default_factory=dict)
    expected_output: str = ""
    status: PlanStepStatus = PlanStepStatus.pending
    alternative_tools: list[str] = Field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 1
    error_message: str = ""
    output: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentPlan(BaseModel):
    """Executable multi-step plan for a task."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    plan_id: str
    task: str
    agent_name: str = ""
    steps: list[PlanStep] = Field(default_factory=list)
    status: PlanStatus = PlanStatus.draft
    created_at: str = ""
    updated_at: str = ""
    task_understanding: str = ""
    intent: str = ""
    schema_version: str = PLANNING_SCHEMA_VERSION
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlanExecutionResult(BaseModel):
    """Outcome of executing an AgentPlan."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    plan_id: str
    completed_steps: list[str] = Field(default_factory=list)
    failed_steps: list[str] = Field(default_factory=list)
    skipped_steps: list[str] = Field(default_factory=list)
    outputs: dict[str, Any] = Field(default_factory=dict)
    final_result: dict[str, Any] = Field(default_factory=dict)
    context_updates: dict[str, Any] = Field(default_factory=dict)
    status: PlanStatus = PlanStatus.completed
    error_message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskAnalysis(BaseModel):
    """Structured task understanding — no hidden chain-of-thought."""

    model_config = ConfigDict(extra="allow")

    task: str
    intent: str = ""
    understanding: str = ""
    suggested_agents: list[str] = Field(default_factory=list)
    suggested_tools: list[str] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
