from __future__ import annotations

"""In-memory queue + store implementations (Sprint 8.3).

Thread-safe, deterministic, dependency-free — the default backend and the one
used by tests.
"""

import heapq
import itertools
import threading

from backend.models.job_models import Job
from backend.queue.interfaces import JobQueue, JobStore


class InMemoryJobQueue(JobQueue):
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._heap: list[tuple[int, int, str]] = []
        self._counter = itertools.count()
        self._dead_letter: list[str] = []

    def enqueue(self, job_id: str, *, priority: int = 2) -> None:
        with self._lock:
            # (priority, insertion_order) keeps FIFO within a priority level.
            heapq.heappush(self._heap, (int(priority), next(self._counter), job_id))

    def dequeue(self) -> str | None:
        with self._lock:
            if not self._heap:
                return None
            return heapq.heappop(self._heap)[2]

    def size(self) -> int:
        with self._lock:
            return len(self._heap)

    def dead_letter(self, job_id: str) -> None:
        with self._lock:
            self._dead_letter.append(job_id)

    def dead_letter_ids(self) -> list[str]:
        with self._lock:
            return list(self._dead_letter)

    def clear(self) -> None:
        with self._lock:
            self._heap.clear()
            self._dead_letter.clear()


class InMemoryJobStore(JobStore):
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: dict[str, Job] = {}

    def save(self, job: Job) -> Job:
        with self._lock:
            self._items[job.job_id] = job.model_copy(deep=True)
        return job.model_copy(deep=True)

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            item = self._items.get(job_id)
            return item.model_copy(deep=True) if item else None

    def list(
        self,
        *,
        status: str | None = None,
        job_type: str | None = None,
        submitted_by: str | None = None,
    ) -> list[Job]:
        with self._lock:
            items = list(self._items.values())
        results = []
        for job in items:
            if status is not None and job.status.value != status:
                continue
            if job_type is not None and job.job_type.value != job_type:
                continue
            if submitted_by is not None and job.submitted_by != submitted_by:
                continue
            results.append(job.model_copy(deep=True))
        results.sort(key=lambda j: j.created_at)
        return results

    def delete(self, job_id: str) -> bool:
        with self._lock:
            return self._items.pop(job_id, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
