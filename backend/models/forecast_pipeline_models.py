from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

FORECAST_PIPELINE_SCHEMA_VERSION = "1.0.0"

# Reserved empty buckets for future orchestration infrastructure. Placeholders only.
FORECAST_PIPELINE_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "scheduler",
    "executor",
    "parallel_execution",
    "distributed_execution",
    "gpu_execution",
    "feature_store",
    "backtesting",
    "live_prediction",
    "monitoring",
    "logging",
    "retry",
    "checkpointing",
    "versioning",
    "resource_manager",
    "queue",
    "cache",
)

# Canonical stage order — metadata representation only, no execution.
CANONICAL_PIPELINE_STAGE_NAMES: tuple[str, ...] = (
    "Dataset",
    "Preparation",
    "Feature Engineering",
    "Forecast Adapter",
    "Prediction",
    "Prediction Validation",
    "Explanation",
    "Cleanup",
    "Output",
)

CANONICAL_PIPELINE_STAGE_IDS: tuple[str, ...] = (
    "dataset",
    "preparation",
    "feature_engineering",
    "forecast_adapter",
    "prediction",
    "prediction_validation",
    "explanation",
    "cleanup",
    "output",
)


def empty_forecast_pipeline_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in FORECAST_PIPELINE_FUTURE_EXTENSION_KEYS}


class PipelineStatus(str, Enum):
    draft = "draft"
    ready = "ready"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    paused = "paused"


class StageStatus(str, Enum):
    pending = "pending"
    waiting = "waiting"
    ready = "ready"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class ExecutionMode(str, Enum):
    manual = "manual"
    scheduled = "scheduled"
    batch = "batch"
    streaming = "streaming"


# Allowed stage status transitions (metadata validation only — no execution).
ALLOWED_STAGE_TRANSITIONS: dict[StageStatus, frozenset[StageStatus]] = {
    StageStatus.pending: frozenset(
        {StageStatus.waiting, StageStatus.ready, StageStatus.skipped}
    ),
    StageStatus.waiting: frozenset({StageStatus.ready, StageStatus.skipped, StageStatus.failed}),
    StageStatus.ready: frozenset({StageStatus.running, StageStatus.skipped, StageStatus.failed}),
    StageStatus.running: frozenset(
        {StageStatus.completed, StageStatus.failed, StageStatus.skipped}
    ),
    StageStatus.completed: frozenset(),
    StageStatus.failed: frozenset({StageStatus.pending, StageStatus.ready}),
    StageStatus.skipped: frozenset(),
}


class PipelineStage(BaseModel):
    """One pipeline stage. Metadata only — never executed in this sprint."""

    model_config = ConfigDict(extra="allow")

    stage_id: str
    stage_name: str
    stage_order: int
    stage_status: StageStatus = StageStatus.pending
    required: bool = True
    dependencies: list[str] = Field(default_factory=list)
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineDependencyEdge(BaseModel):
    """Directed metadata edge between stages. No execution graph."""

    from_stage_id: str
    to_stage_id: str
    edge_kind: str = "depends_on"


class PipelineDependencyGraph(BaseModel):
    """Metadata-only dependency graph for pipeline stages."""

    nodes: list[str] = Field(default_factory=list)
    edges: list[PipelineDependencyEdge] = Field(default_factory=list)
    canonical_order: list[str] = Field(default_factory=lambda: list(CANONICAL_PIPELINE_STAGE_IDS))


class PipelineStatistics(BaseModel):
    total_stages: int = 0
    completed: int = 0
    pending: int = 0
    failed: int = 0
    skipped: int = 0
    waiting: int = 0
    ready: int = 0
    running: int = 0
    completion_percentage: float = 0.0
    required_stage_count: int = 0
    optional_stage_count: int = 0


class PipelineSummary(BaseModel):
    pipeline_name: str = ""
    version: str = ""
    adapter: str = ""
    current_stage: str | None = None
    execution_mode: str = ""
    overall_status: str = ""
    total_stages: int = 0
    completion_percentage: float = 0.0


class ForecastPipelineMetadata(BaseModel):
    legacy: dict[str, Any] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    future_extensions: dict[str, Any] = Field(
        default_factory=empty_forecast_pipeline_future_extensions
    )


class ForecastPipeline(BaseModel):
    """Orchestration metadata for a future forecasting pipeline. No execution."""

    model_config = ConfigDict(extra="allow")

    pipeline_id: str
    pipeline_name: str
    pipeline_version: str = FORECAST_PIPELINE_SCHEMA_VERSION
    dataset_id: str | None = None
    adapter_id: str | None = None
    adapter_type: str | None = None
    execution_mode: ExecutionMode = ExecutionMode.manual
    pipeline_status: PipelineStatus = PipelineStatus.draft
    stages: list[PipelineStage] = Field(default_factory=list)
    current_stage: str | None = None
    completed_stages: list[str] = Field(default_factory=list)
    failed_stages: list[str] = Field(default_factory=list)
    skipped_stages: list[str] = Field(default_factory=list)
    dependencies: PipelineDependencyGraph = Field(default_factory=PipelineDependencyGraph)
    created_at: str = ""
    updated_at: str = ""
    metadata: ForecastPipelineMetadata = Field(default_factory=ForecastPipelineMetadata)
