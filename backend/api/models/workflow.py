from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkflowExecuteRequest(BaseModel):
    """Execute a workflow definition or a built-in analyst pipeline."""

    model_config = ConfigDict(extra="allow")

    workflow_name: str = "Intelligence Pipeline"
    stage_ids: list[str] | None = None
    initial_context: dict[str, Any] = Field(default_factory=dict)
    dataset_id: str | None = None
    domain: str | None = None
    stop_on_error: bool = True
    # Optional analyst shortcut: when query is set, run make_analyst_stage pipeline.
    query: str | None = None
    include_evaluation: bool = True


class WorkflowExecuteResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool = True
    execution_id: str
    workflow_id: str = ""
    workflow_name: str = ""
    status: str = ""
    duration_ms: float | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    context_keys: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowStatusResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool = True
    execution_id: str
    workflow_id: str = ""
    workflow_name: str = ""
    status: str = ""
    started_at: str = ""
    finished_at: str = ""
    duration_ms: float | None = None
    completed_stages: int = 0
    failed_stages: int = 0
    error_count: int = 0


class WorkflowResultsResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool = True
    execution_id: str
    status: str = ""
    stage_results: list[dict[str, Any]] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    context_keys: list[str] = Field(default_factory=list)


class WorkflowStatisticsResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool = True
    execution_id: str | None = None
    total_stages: int = 0
    completed_stages: int = 0
    failed_stages: int = 0
    skipped_stages: int = 0
    blocked_stages: int = 0
    pending_stages: int = 0
    log_count: int = 0
    error_count: int = 0
    execution_count: int = 0
