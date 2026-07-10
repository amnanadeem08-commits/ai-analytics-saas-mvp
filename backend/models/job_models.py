from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

JOB_SCHEMA_VERSION = "1.0.0"

JOB_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "docker",
    "kubernetes",
    "billing",
    "deployment",
    "streaming",
    "distributed_scheduler",
)


def empty_job_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in JOB_FUTURE_EXTENSION_KEYS}


class JobStatus(str, Enum):
    pending = "pending"
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"
    retrying = "retrying"
    dead_letter = "dead_letter"


TERMINAL_STATUSES: frozenset[JobStatus] = frozenset(
    {JobStatus.succeeded, JobStatus.failed, JobStatus.cancelled, JobStatus.dead_letter}
)


class JobType(str, Enum):
    workflow_execution = "workflow_execution"
    analysis = "analysis"
    evaluation = "evaluation"
    knowledge_ingestion = "knowledge_ingestion"
    generic = "generic"


class JobPriority(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"
    critical = "critical"


# Lower number = higher scheduling priority.
JOB_PRIORITY_ORDER: dict[str, int] = {
    JobPriority.critical.value: 0,
    JobPriority.high.value: 1,
    JobPriority.normal.value: 2,
    JobPriority.low.value: 3,
}


class JobProgress(BaseModel):
    model_config = ConfigDict(extra="allow")

    percent: float = 0.0
    message: str = ""
    current_step: int = 0
    total_steps: int = 0
    updated_at: str = ""


class JobResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool = False
    data: dict[str, Any] = Field(default_factory=dict)
    error: str = ""
    completed_at: str = ""


class Job(BaseModel):
    model_config = ConfigDict(extra="allow")

    job_id: str
    job_type: JobType = JobType.generic
    status: JobStatus = JobStatus.pending
    priority: JobPriority = JobPriority.normal
    payload: dict[str, Any] = Field(default_factory=dict)
    result: JobResult | None = None
    progress: JobProgress = Field(default_factory=JobProgress)
    attempts: int = 0
    max_retries: int = 3
    retry_delay_seconds: float = 0.0
    error: str = ""
    dead_lettered: bool = False
    submitted_by: str = ""
    created_at: str = ""
    updated_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    schema_version: str = JOB_SCHEMA_VERSION
    metadata: dict[str, Any] = Field(default_factory=dict)
