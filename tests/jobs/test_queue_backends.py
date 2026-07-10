from __future__ import annotations

from backend.queue.config import get_queue_config, reset_queue_config
from backend.queue.factory import active_backend, build_queue, build_store, reset_queue_backends
from backend.queue.memory import InMemoryJobQueue, InMemoryJobStore
from backend.models.job_models import Job, JobType


def setup_function():
    reset_queue_config()
    reset_queue_backends()


def teardown_function():
    import os

    os.environ.pop("QUEUE_BACKEND", None)
    os.environ.pop("REDIS_URL", None)
    reset_queue_config()
    reset_queue_backends()


def test_default_backend_is_memory():
    assert active_backend() == "memory"
    assert isinstance(build_queue(), InMemoryJobQueue)
    assert isinstance(build_store(), InMemoryJobStore)


def test_redis_backend_falls_back_safely_when_unavailable(monkeypatch):
    monkeypatch.setenv("QUEUE_BACKEND", "redis")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:65534/0")  # unreachable
    reset_queue_config()
    reset_queue_backends()
    # redis not installed / unreachable -> safe fallback to in-memory.
    queue = build_queue()
    store = build_store()
    assert isinstance(queue, InMemoryJobQueue)
    assert isinstance(store, InMemoryJobStore)


def test_memory_queue_priority_and_dlq():
    q = InMemoryJobQueue()
    q.enqueue("low", priority=3)
    q.enqueue("high", priority=0)
    q.enqueue("normal", priority=2)
    assert q.dequeue() == "high"
    assert q.dequeue() == "normal"
    assert q.dequeue() == "low"
    assert q.dequeue() is None
    q.dead_letter("dead1")
    assert q.dead_letter_ids() == ["dead1"]


def test_memory_store_crud_and_filter():
    store = InMemoryJobStore()
    store.save(Job(job_id="j1", job_type=JobType.generic, created_at="t1"))
    store.save(Job(job_id="j2", job_type=JobType.analysis, created_at="t2"))
    assert store.get("j1").job_type == JobType.generic
    assert len(store.list()) == 2
    assert len(store.list(job_type="analysis")) == 1
    assert store.delete("j1") is True
    assert store.get("j1") is None


def test_config_reads_environment(monkeypatch):
    monkeypatch.setenv("QUEUE_BACKEND", "redis")
    monkeypatch.setenv("JOB_MAX_RETRIES", "7")
    reset_queue_config()
    config = get_queue_config()
    assert config.uses_redis is True
    assert config.default_max_retries == 7
