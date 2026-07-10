from __future__ import annotations

"""Job service (Sprint 8.3).

Submit / cancel / retry / query jobs. Business logic in the reused services is
untouched — handlers simply call them. Execution is either enqueued for a
background worker or run inline (deterministic, used by tests and the sync API).
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from backend.models.job_models import (
    JOB_PRIORITY_ORDER,
    Job,
    JobPriority,
    JobStatus,
    JobType,
    TERMINAL_STATUSES,
)
from backend.queue.config import get_queue_config
from backend.queue.factory import active_backend, get_queue, get_store, reset_queue_backends


class JobError(Exception):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _uid() -> str:
    return f"job_{uuid.uuid4().hex}"


def _priority_value(priority: JobPriority) -> int:
    return JOB_PRIORITY_ORDER.get(priority.value, 2)


def reset_jobs() -> None:
    """Test helper — clear queue + store and rebuild backends from config."""
    reset_queue_backends()
    get_queue().clear()
    get_store().clear()


def submit_job(
    *,
    job_type: JobType | str,
    payload: dict[str, Any] | None = None,
    priority: JobPriority | str = JobPriority.normal,
    max_retries: int | None = None,
    submitted_by: str = "",
    inline: bool = False,
) -> Job:
    """Create a job, enqueue it, and (optionally) run it inline."""
    jtype = job_type if isinstance(job_type, JobType) else JobType(str(job_type))
    prio = priority if isinstance(priority, JobPriority) else JobPriority(str(priority))
    config = get_queue_config()
    now = _now_iso()
    job = Job(
        job_id=_uid(),
        job_type=jtype,
        status=JobStatus.queued,
        priority=prio,
        payload=dict(payload or {}),
        max_retries=config.default_max_retries if max_retries is None else int(max_retries),
        submitted_by=submitted_by,
        created_at=now,
        updated_at=now,
    )
    store = get_store()
    queue = get_queue()
    store.save(job)
    queue.enqueue(job.job_id, priority=_priority_value(prio))
    try:
        from backend.logging.job_logger import log_job_started
        from backend.monitoring.metrics import record_job

        log_job_started(job.job_id, job_type=jtype.value)
        record_job(event="submitted", job_type=jtype.value, status=job.status.value)
    except Exception:
        pass

    if inline:
        from backend.workers.runner import run_job

        # Drain this job (and any retries it triggers) synchronously.
        drained = 0
        while drained < (job.max_retries + 2):
            nxt = queue.dequeue()
            if nxt is None:
                break
            run_job(nxt, queue=queue, store=store)
            drained += 1
        return store.get(job.job_id) or job
    return store.get(job.job_id) or job


def get_job(job_id: str) -> Job | None:
    return get_store().get(job_id)


def list_jobs(
    *,
    status: str | None = None,
    job_type: str | None = None,
    submitted_by: str | None = None,
) -> list[Job]:
    return get_store().list(status=status, job_type=job_type, submitted_by=submitted_by)


def cancel_job(job_id: str) -> Job:
    store = get_store()
    job = store.get(job_id)
    if job is None:
        raise JobError(f"Job not found: {job_id}", status_code=404)
    if job.status in TERMINAL_STATUSES:
        raise JobError(f"Job already {job.status.value}; cannot cancel", status_code=409)
    job.status = JobStatus.cancelled
    job.finished_at = _now_iso()
    job.updated_at = job.finished_at
    return store.save(job)


def retry_job(job_id: str, *, inline: bool = False) -> Job:
    store = get_store()
    queue = get_queue()
    job = store.get(job_id)
    if job is None:
        raise JobError(f"Job not found: {job_id}", status_code=404)
    if job.status not in {JobStatus.failed, JobStatus.cancelled, JobStatus.dead_letter}:
        raise JobError(
            f"Only failed/cancelled/dead-letter jobs can be retried (current: {job.status.value})",
            status_code=409,
        )
    job.status = JobStatus.queued
    job.attempts = 0
    job.dead_lettered = False
    job.error = ""
    job.result = None
    job.finished_at = ""
    job.updated_at = _now_iso()
    store.save(job)
    queue.enqueue(job.job_id, priority=_priority_value(job.priority))

    if inline:
        from backend.workers.runner import run_job

        drained = 0
        while drained < (job.max_retries + 2):
            nxt = queue.dequeue()
            if nxt is None:
                break
            run_job(nxt, queue=queue, store=store)
            drained += 1
        return store.get(job.job_id) or job
    return store.get(job.job_id) or job


def job_statistics() -> dict[str, Any]:
    jobs = get_store().list()
    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for job in jobs:
        by_status[job.status.value] = by_status.get(job.status.value, 0) + 1
        by_type[job.job_type.value] = by_type.get(job.job_type.value, 0) + 1
    queue = get_queue()
    return {
        "total_jobs": len(jobs),
        "by_status": by_status,
        "by_type": by_type,
        "queued_depth": queue.size(),
        "dead_letter_depth": len(queue.dead_letter_ids()),
        "backend": active_backend(),
    }


# ---------------------------------------------------------------------------
# Async wrappers — submit typed jobs (reuse existing services via handlers)
# ---------------------------------------------------------------------------


def execute_workflow_async(
    *,
    query: str,
    dataset_id: str | None = None,
    include_evaluation: bool = True,
    priority: JobPriority | str = JobPriority.normal,
    submitted_by: str = "",
    inline: bool = False,
) -> Job:
    return submit_job(
        job_type=JobType.workflow_execution,
        payload={"query": query, "dataset_id": dataset_id, "include_evaluation": include_evaluation},
        priority=priority,
        submitted_by=submitted_by,
        inline=inline,
    )


def execute_analysis_async(
    *,
    query: str,
    user_context: dict[str, Any] | None = None,
    session_id: str | None = None,
    follow_up: bool = False,
    priority: JobPriority | str = JobPriority.normal,
    submitted_by: str = "",
    inline: bool = False,
) -> Job:
    return submit_job(
        job_type=JobType.analysis,
        payload={
            "query": query,
            "user_context": user_context or {},
            "session_id": session_id,
            "follow_up": follow_up,
        },
        priority=priority,
        submitted_by=submitted_by,
        inline=inline,
    )


def evaluate_async(
    *,
    session_id: str,
    weights: dict[str, float] | None = None,
    priority: JobPriority | str = JobPriority.normal,
    submitted_by: str = "",
    inline: bool = False,
) -> Job:
    return submit_job(
        job_type=JobType.evaluation,
        payload={"session_id": session_id, "weights": weights or {}},
        priority=priority,
        submitted_by=submitted_by,
        inline=inline,
    )


def knowledge_ingestion_async(
    *,
    title: str,
    content: str,
    source: str = "text",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    priority: JobPriority | str = JobPriority.normal,
    submitted_by: str = "",
    inline: bool = False,
) -> Job:
    return submit_job(
        job_type=JobType.knowledge_ingestion,
        payload={
            "title": title,
            "content": content,
            "source": source,
            "tags": tags or [],
            "metadata": metadata or {},
        },
        priority=priority,
        submitted_by=submitted_by,
        inline=inline,
    )
