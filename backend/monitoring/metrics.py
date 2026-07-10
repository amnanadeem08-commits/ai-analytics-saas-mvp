from __future__ import annotations

"""Metrics facade (Sprint 8.5)."""

from backend.monitoring.counters import export_metrics, inc_counter, observe_timer, set_gauge
from backend.monitoring.registry import get_registry, reset_registry
from backend.monitoring.timers import timer

DOMAINS = (
    "api",
    "workflow",
    "agents",
    "jobs",
    "storage",
    "database",
    "authentication",
    "knowledge",
    "evaluation",
    "memory",
    "rag",
)


def record_api_request(*, method: str, path: str, status_code: int, duration_ms: float) -> None:
    labels = {"method": method, "path": path, "status": str(status_code)}
    inc_counter("api_requests_total", labels=labels)
    observe_timer("api_request_duration_ms", duration_ms, labels={"method": method, "path": path})


def record_workflow(*, event: str, status: str = "") -> None:
    inc_counter("workflow_events_total", labels={"event": event, "status": status or "unknown"})


def record_job(*, event: str, job_type: str = "", status: str = "") -> None:
    inc_counter("job_events_total", labels={"event": event, "job_type": job_type or "generic", "status": status or "unknown"})


def record_storage(*, operation: str, status: str = "ok") -> None:
    inc_counter("storage_operations_total", labels={"operation": operation, "status": status})


def record_auth(*, event: str, status: str = "ok") -> None:
    inc_counter("auth_events_total", labels={"event": event, "status": status})


def record_knowledge(*, operation: str) -> None:
    inc_counter("knowledge_operations_total", labels={"operation": operation})


def record_evaluation(*, event: str) -> None:
    inc_counter("evaluation_events_total", labels={"event": event})


def record_database(*, operation: str, status: str = "ok") -> None:
    inc_counter("database_operations_total", labels={"operation": operation, "status": status})


def record_rag(*, operation: str) -> None:
    inc_counter("rag_operations_total", labels={"operation": operation})


def record_memory(*, operation: str) -> None:
    inc_counter("memory_operations_total", labels={"operation": operation})


def record_agent(*, event: str) -> None:
    inc_counter("agent_events_total", labels={"event": event})
