from __future__ import annotations

"""Abstract queue + store interfaces. Business logic depends only on these."""

from abc import ABC, abstractmethod

from backend.models.job_models import Job


class JobQueue(ABC):
    """FIFO-with-priority queue of job ids, plus a dead-letter queue."""

    @abstractmethod
    def enqueue(self, job_id: str, *, priority: int = 2) -> None: ...

    @abstractmethod
    def dequeue(self) -> str | None:
        """Pop the highest-priority job id, or None when empty."""

    @abstractmethod
    def size(self) -> int: ...

    @abstractmethod
    def dead_letter(self, job_id: str) -> None: ...

    @abstractmethod
    def dead_letter_ids(self) -> list[str]: ...

    @abstractmethod
    def clear(self) -> None: ...


class JobStore(ABC):
    """Persistence for Job records."""

    @abstractmethod
    def save(self, job: Job) -> Job: ...

    @abstractmethod
    def get(self, job_id: str) -> Job | None: ...

    @abstractmethod
    def list(
        self,
        *,
        status: str | None = None,
        job_type: str | None = None,
        submitted_by: str | None = None,
    ) -> list[Job]: ...

    @abstractmethod
    def delete(self, job_id: str) -> bool: ...

    @abstractmethod
    def clear(self) -> None: ...
