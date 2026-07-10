from __future__ import annotations

import pytest

from backend.models.job_models import JobStatus
from backend.services import job_service
from backend.services.job_service import JobError


def setup_function():
    job_service.reset_jobs()


def test_submit_generic_job_inline_succeeds():
    job = job_service.submit_job(job_type="generic", payload={"echo": "hi", "steps": 3}, inline=True)
    assert job.status == JobStatus.succeeded
    assert job.result is not None and job.result.success is True
    assert job.result.data["echo"] == "hi"
    assert job.progress.percent == 100.0


def test_submit_queued_without_inline_then_drain():
    from backend.workers.worker import Worker

    job = job_service.submit_job(job_type="generic", payload={"echo": "x"})
    assert job.status == JobStatus.queued
    processed = Worker().drain()
    assert processed >= 1
    reloaded = job_service.get_job(job.job_id)
    assert reloaded.status == JobStatus.succeeded


def test_progress_tracking_updates():
    job = job_service.submit_job(job_type="generic", payload={"steps": 5}, inline=True)
    # On completion the runner sets a clean 100% marker.
    assert job.status.value == "succeeded"
    assert job.progress.percent == 100.0
    assert job.result.data["steps"] == 5


def test_retry_then_dead_letter_on_persistent_failure():
    job = job_service.submit_job(
        job_type="generic",
        payload={"fail": True, "fail_message": "boom"},
        max_retries=1,
        inline=True,
    )
    assert job.status == JobStatus.failed
    assert job.dead_lettered is True
    assert job.attempts == 2  # initial + 1 retry
    # Dead-letter queue recorded it.
    from backend.queue.factory import get_queue

    assert job.job_id in get_queue().dead_letter_ids()


def test_manual_retry_of_failed_job():
    job = job_service.submit_job(job_type="generic", payload={"fail": True}, max_retries=0, inline=True)
    assert job.status == JobStatus.failed
    retried = job_service.retry_job(job.job_id, inline=True)
    # Still fails (handler always fails), but the retry path executed.
    assert retried.status == JobStatus.failed
    assert retried.attempts >= 1


def test_cancel_pending_job():
    job = job_service.submit_job(job_type="generic", payload={"echo": "x"})
    cancelled = job_service.cancel_job(job.job_id)
    assert cancelled.status == JobStatus.cancelled

    # A cancelled job is skipped by the runner.
    from backend.workers.worker import Worker

    Worker().drain()
    reloaded = job_service.get_job(job.job_id)
    assert reloaded.status == JobStatus.cancelled


def test_cancel_terminal_job_rejected():
    job = job_service.submit_job(job_type="generic", payload={"echo": "x"}, inline=True)
    with pytest.raises(JobError) as exc:
        job_service.cancel_job(job.job_id)
    assert exc.value.status_code == 409


def test_list_and_statistics():
    job_service.submit_job(job_type="generic", payload={"echo": "a"}, inline=True)
    job_service.submit_job(job_type="generic", payload={"fail": True}, max_retries=0, inline=True)
    stats = job_service.job_statistics()
    assert stats["total_jobs"] == 2
    assert stats["by_status"].get("succeeded") == 1
    assert stats["by_status"].get("failed") == 1
    assert stats["backend"] == "memory"
    succeeded = job_service.list_jobs(status="succeeded")
    assert len(succeeded) == 1


def test_priority_ordering_dequeue():
    from backend.queue.factory import get_queue, get_store

    job_service.submit_job(job_type="generic", payload={"echo": "low"}, priority="low")
    high = job_service.submit_job(job_type="generic", payload={"echo": "high"}, priority="critical")
    # Critical should dequeue first despite being submitted second.
    first_id = get_queue().dequeue()
    assert first_id == high.job_id
