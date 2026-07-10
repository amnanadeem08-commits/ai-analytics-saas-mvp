from __future__ import annotations

from backend.logging.logger import bind_context, get_logger

_log = get_logger("ai_analytics.job")


def log_job_event(event: str, *, job_id: str = "", job_type: str = "", **fields) -> None:
    bind_context(job_id=job_id or None)
    _log.info(event, extra={"event": event, "job_type": job_type, **fields})


def log_job_started(job_id: str, job_type: str = "", **fields) -> None:
    log_job_event("job_started", job_id=job_id, job_type=job_type, **fields)


def log_job_completed(job_id: str, job_type: str = "", status: str = "", **fields) -> None:
    log_job_event("job_completed", job_id=job_id, job_type=job_type, status=status, **fields)
