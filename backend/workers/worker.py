from __future__ import annotations

"""Background worker (Sprint 8.3).

A worker polls the queue and runs jobs via the shared runner. Supports a
background thread with heartbeat and graceful shutdown, plus synchronous
``drain``/``run_once`` helpers for deterministic tests.
"""

import threading
import time
import uuid
from datetime import datetime, timezone

from backend.queue.config import get_queue_config
from backend.queue.factory import get_queue, get_store
from backend.workers.runner import run_job


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class Worker:
    def __init__(self, *, worker_id: str | None = None):
        self.worker_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        self.status = "idle"
        self.started_at = ""
        self.last_heartbeat = ""
        self.processed_count = 0
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # --- Heartbeat --------------------------------------------------------

    def heartbeat(self) -> str:
        self.last_heartbeat = _now_iso()
        return self.last_heartbeat

    def health(self) -> dict:
        return {
            "worker_id": self.worker_id,
            "status": self.status,
            "started_at": self.started_at,
            "last_heartbeat": self.last_heartbeat,
            "processed_count": self.processed_count,
            "running": self.is_running(),
        }

    # --- Synchronous processing (tests / inline drain) --------------------

    def run_once(self) -> str | None:
        """Process a single queued job. Returns the job id processed, or None."""
        queue = get_queue()
        job_id = queue.dequeue()
        if job_id is None:
            return None
        self.status = "busy"
        self.heartbeat()
        run_job(job_id, queue=queue, store=get_store())
        self.processed_count += 1
        self.status = "idle"
        return job_id

    def drain(self, *, max_jobs: int = 1000) -> int:
        """Process all currently-queued jobs (including requeued retries)."""
        processed = 0
        while processed < max_jobs:
            job_id = self.run_once()
            if job_id is None:
                break
            processed += 1
        return processed

    # --- Background thread lifecycle --------------------------------------

    def start(self) -> None:
        if self.is_running():
            return
        self._stop_event.clear()
        self.started_at = _now_iso()
        self.status = "running"
        self._thread = threading.Thread(target=self._loop, name=self.worker_id, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        config = get_queue_config()
        poll_seconds = max(0.01, config.worker_poll_interval_ms / 1000.0)
        while not self._stop_event.is_set():
            self.heartbeat()
            processed = self.run_once()
            if processed is None:
                time.sleep(poll_seconds)
        self.status = "stopped"

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def stop(self, *, timeout: float = 5.0) -> None:
        """Graceful shutdown: signal stop and join the worker thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        self._thread = None
        self.status = "stopped"


_DEFAULT_WORKER: Worker | None = None


def get_worker() -> Worker:
    global _DEFAULT_WORKER
    if _DEFAULT_WORKER is None:
        _DEFAULT_WORKER = Worker()
    return _DEFAULT_WORKER


def reset_worker() -> Worker:
    global _DEFAULT_WORKER
    if _DEFAULT_WORKER is not None and _DEFAULT_WORKER.is_running():
        _DEFAULT_WORKER.stop()
    _DEFAULT_WORKER = Worker()
    return _DEFAULT_WORKER
