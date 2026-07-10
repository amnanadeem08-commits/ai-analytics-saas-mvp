from __future__ import annotations

import time

from backend.models.job_models import JobStatus
from backend.services import job_service
from backend.workers.worker import Worker, get_worker, reset_worker


def setup_function():
    job_service.reset_jobs()
    reset_worker()


def teardown_function():
    reset_worker()


def test_worker_heartbeat_and_health():
    worker = Worker()
    hb = worker.heartbeat()
    assert hb
    health = worker.health()
    assert health["worker_id"] == worker.worker_id
    assert health["last_heartbeat"] == hb


def test_worker_run_once_returns_none_when_empty():
    worker = Worker()
    assert worker.run_once() is None


def test_background_worker_processes_and_shuts_down_gracefully():
    worker = get_worker()
    worker.start()
    assert worker.is_running()
    try:
        job = job_service.submit_job(job_type="generic", payload={"echo": "bg", "steps": 2})
        # Wait for the background worker to process the job.
        deadline = time.time() + 5.0
        status = None
        while time.time() < deadline:
            reloaded = job_service.get_job(job.job_id)
            status = reloaded.status if reloaded else None
            if status in {JobStatus.succeeded, JobStatus.failed, JobStatus.dead_letter}:
                break
            time.sleep(0.05)
        assert status == JobStatus.succeeded
        assert worker.processed_count >= 1
    finally:
        worker.stop(timeout=5.0)
    assert not worker.is_running()
    assert worker.status == "stopped"


def test_reset_worker_stops_running_worker():
    worker = get_worker()
    worker.start()
    assert worker.is_running()
    fresh = reset_worker()
    assert fresh is not worker
    assert not worker.is_running()
