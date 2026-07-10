from __future__ import annotations

"""Job runner (Sprint 8.3).

Executes a single job with progress tracking + retry/dead-letter handling.
Shared by inline execution (job_service) and background workers.
"""

from datetime import datetime, timezone

from backend.jobs.handlers import get_handler
from backend.models.job_models import Job, JobProgress, JobResult, JobStatus
from backend.queue.factory import get_queue, get_store
from backend.queue.interfaces import JobQueue, JobStore


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _priority_value(job: Job) -> int:
    from backend.models.job_models import JOB_PRIORITY_ORDER

    return JOB_PRIORITY_ORDER.get(job.priority.value, 2)


def run_job(job_id: str, *, queue: JobQueue | None = None, store: JobStore | None = None) -> Job:
    """Execute one job by id. Returns the updated Job record."""
    queue = queue or get_queue()
    store = store or get_store()

    job = store.get(job_id)
    if job is None:
        raise KeyError(f"Job not found: {job_id}")

    # Respect cancellation requested before execution.
    if job.status in {JobStatus.cancelled, JobStatus.succeeded, JobStatus.dead_letter}:
        return job

    job.status = JobStatus.running
    job.started_at = job.started_at or _now_iso()
    job.attempts += 1
    job.updated_at = _now_iso()
    store.save(job)

    def _progress(percent: float, message: str = "", current_step: int = 0, total_steps: int = 0) -> None:
        latest = store.get(job_id) or job
        latest.progress = JobProgress(
            percent=max(0.0, min(100.0, float(percent))),
            message=message,
            current_step=current_step,
            total_steps=total_steps,
            updated_at=_now_iso(),
        )
        latest.updated_at = _now_iso()
        store.save(latest)

    try:
        handler = get_handler(job.job_type)
        data = handler(dict(job.payload), _progress)
        job = store.get(job_id) or job
        job.status = JobStatus.succeeded
        job.result = JobResult(success=True, data=data or {}, completed_at=_now_iso())
        job.progress = JobProgress(percent=100.0, message="completed", updated_at=_now_iso())
        job.error = ""
        job.finished_at = _now_iso()
        job.updated_at = job.finished_at
        store.save(job)
        return job
    except Exception as exc:  # noqa: BLE001
        job = store.get(job_id) or job
        job.error = str(exc)
        job.updated_at = _now_iso()
        if job.attempts <= job.max_retries:
            job.status = JobStatus.retrying
            store.save(job)
            # Re-enqueue for another attempt.
            queue.enqueue(job.job_id, priority=_priority_value(job))
        else:
            job.status = JobStatus.failed
            job.dead_lettered = True
            job.result = JobResult(success=False, error=str(exc), completed_at=_now_iso())
            job.finished_at = _now_iso()
            store.save(job)
            queue.dead_letter(job.job_id)
        return job
