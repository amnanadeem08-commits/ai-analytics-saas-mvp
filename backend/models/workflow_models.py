from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

WORKFLOW_SCHEMA_VERSION = "1.0.0"

# Reserved empty buckets for future runtime / agent / LLM wiring. Placeholders only.
WORKFLOW_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "llm",
    "agents",
    "tool_calling",
    "scheduler",
    "parallel_execution",
    "distributed_execution",
    "approvals",
    "rbac",
    "ui",
    "rest",
    "retry_policy",
    "compensation",
)


def empty_workflow_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in WORKFLOW_FUTURE_EXTENSION_KEYS}


class WorkflowStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    partial = "partial"


class StageRunStatus(str, Enum):
    pending = "pending"
    ready = "ready"
    running = "running"
    completed = "completed"
    skipped = "skipped"
    failed = "failed"
    blocked = "blocked"


class LogLevel(str, Enum):
    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"


class WorkflowStageDefinition(BaseModel):
    """One stage in a workflow definition. References orchestrator stage_id by default."""

    model_config = ConfigDict(extra="allow")

    stage_id: str
    stage_name: str = ""
    dependencies: list[str] = Field(default_factory=list)
    optional_dependencies: list[str] = Field(default_factory=list)
    execution_order: int = 0
    enabled: bool = True
    required: bool = True
    runner_key: str = ""
    timeout_seconds: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowDefinition(BaseModel):
    """Executable workflow blueprint derived from the intelligence orchestrator catalog."""

    model_config = ConfigDict(extra="allow")

    workflow_id: str
    workflow_name: str = "Intelligence Pipeline"
    schema_version: str = WORKFLOW_SCHEMA_VERSION
    stages: list[WorkflowStageDefinition] = Field(default_factory=list)
    stop_on_error: bool = True
    created_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowLogEntry(BaseModel):
    log_id: str
    timestamp: str
    level: LogLevel = LogLevel.info
    stage_id: str | None = None
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class WorkflowError(BaseModel):
    error_id: str
    stage_id: str | None = None
    error_type: str = ""
    message: str = ""
    recoverable: bool = False
    timestamp: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class StageRunResult(BaseModel):
    """Lifecycle + I/O summary for one stage run. Does not store large payloads by default."""

    model_config = ConfigDict(extra="allow")

    stage_id: str
    stage_name: str = ""
    status: StageRunStatus = StageRunStatus.pending
    started_at: str = ""
    finished_at: str = ""
    duration_ms: float | None = None
    input_keys: list[str] = Field(default_factory=list)
    output_keys: list[str] = Field(default_factory=list)
    produced_asset_refs: list[str] = Field(default_factory=list)
    error_message: str = ""
    logs: list[WorkflowLogEntry] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowExecution(BaseModel):
    """One concrete workflow run with stage lifecycle, context refs, logs, and errors."""

    model_config = ConfigDict(extra="allow")

    execution_id: str
    workflow_id: str
    workflow_name: str = ""
    status: WorkflowStatus = WorkflowStatus.pending
    dataset_id: str | None = None
    domain: str | None = None
    stage_results: list[StageRunResult] = Field(default_factory=list)
    context_keys: list[str] = Field(default_factory=list)
    logs: list[WorkflowLogEntry] = Field(default_factory=list)
    errors: list[WorkflowError] = Field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""
    duration_ms: float | None = None
    schema_version: str = WORKFLOW_SCHEMA_VERSION
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowStatistics(BaseModel):
    total_stages: int = 0
    completed_stages: int = 0
    failed_stages: int = 0
    skipped_stages: int = 0
    blocked_stages: int = 0
    pending_stages: int = 0
    log_count: int = 0
    error_count: int = 0


class WorkflowSummary(BaseModel):
    execution_id: str = ""
    workflow_name: str = ""
    status: str = ""
    completed_stages: int = 0
    failed_stages: int = 0
    duration_ms: float | None = None
    context_key_count: int = 0
