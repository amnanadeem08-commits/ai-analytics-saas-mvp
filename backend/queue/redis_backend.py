from __future__ import annotations

"""Optional Redis-backed queue + store (Sprint 8.3).

Redis is imported lazily and connections are validated at construction. If
``redis`` is not installed or the server is unreachable, callers fall back to
the in-memory backend (see factory.py) — no hard dependency at import time.
"""

import json
from typing import Any

from backend.models.job_models import Job
from backend.queue.interfaces import JobQueue, JobStore


class RedisUnavailableError(RuntimeError):
    pass


def _connect(redis_url: str):
    try:
        import redis  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RedisUnavailableError(f"redis package not installed: {exc}") from exc
    try:
        client = redis.Redis.from_url(redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception as exc:  # noqa: BLE001
        raise RedisUnavailableError(f"cannot connect to Redis at {redis_url}: {exc}") from exc


class RedisJobQueue(JobQueue):
    def __init__(self, redis_url: str, *, namespace: str = "databot"):
        self._client = _connect(redis_url)
        self._key = f"{namespace}:jobq"
        self._dlq = f"{namespace}:jobq:dlq"

    def enqueue(self, job_id: str, *, priority: int = 2) -> None:
        # Sorted set keyed by priority; ties broken by insertion via incrementing score.
        score = float(priority) + (self._client.incr(f"{self._key}:seq") / 1e12)
        self._client.zadd(self._key, {job_id: score})

    def dequeue(self) -> str | None:
        items = self._client.zpopmin(self._key, 1)
        if not items:
            return None
        return items[0][0]

    def size(self) -> int:
        return int(self._client.zcard(self._key))

    def dead_letter(self, job_id: str) -> None:
        self._client.rpush(self._dlq, job_id)

    def dead_letter_ids(self) -> list[str]:
        return list(self._client.lrange(self._dlq, 0, -1))

    def clear(self) -> None:
        self._client.delete(self._key, self._dlq, f"{self._key}:seq")


class RedisJobStore(JobStore):
    def __init__(self, redis_url: str, *, namespace: str = "databot"):
        self._client = _connect(redis_url)
        self._key = f"{namespace}:jobs"

    def save(self, job: Job) -> Job:
        self._client.hset(self._key, job.job_id, json.dumps(job.model_dump(mode="json")))
        return job.model_copy(deep=True)

    def get(self, job_id: str) -> Job | None:
        raw = self._client.hget(self._key, job_id)
        if not raw:
            return None
        return Job(**json.loads(raw))

    def list(
        self,
        *,
        status: str | None = None,
        job_type: str | None = None,
        submitted_by: str | None = None,
    ) -> list[Job]:
        raw_map: dict[str, Any] = self._client.hgetall(self._key)
        results = []
        for raw in raw_map.values():
            job = Job(**json.loads(raw))
            if status is not None and job.status.value != status:
                continue
            if job_type is not None and job.job_type.value != job_type:
                continue
            if submitted_by is not None and job.submitted_by != submitted_by:
                continue
            results.append(job)
        results.sort(key=lambda j: j.created_at)
        return results

    def delete(self, job_id: str) -> bool:
        return int(self._client.hdel(self._key, job_id)) > 0

    def clear(self) -> None:
        self._client.delete(self._key)
