from __future__ import annotations

from backend.monitoring.collectors import collect_runtime_metrics
from backend.monitoring.counters import export_metrics, inc_counter, observe_timer, set_gauge
from backend.monitoring.errors import capture_exception, categorize_exception, record_unhandled, recovery_hint
from backend.monitoring.health import (
    dependency_checks,
    health_report,
    liveness_report,
    readiness_report,
    system_status,
)
from backend.monitoring.metrics import (
    record_agent,
    record_api_request,
    record_auth,
    record_database,
    record_evaluation,
    record_job,
    record_knowledge,
    record_memory,
    record_rag,
    record_storage,
    record_workflow,
)
from backend.monitoring.registry import get_registry, reset_registry
from backend.monitoring.timers import timer
from backend.monitoring.tracing import (
    end_trace,
    get_span_id,
    get_trace_id,
    new_trace_id,
    span,
    start_trace,
    trace_agent,
    trace_api_request,
    trace_job,
    trace_workflow,
)

__all__ = [
    "get_registry",
    "reset_registry",
    "export_metrics",
    "collect_runtime_metrics",
    "inc_counter",
    "set_gauge",
    "observe_timer",
    "timer",
    "record_api_request",
    "record_workflow",
    "record_job",
    "record_storage",
    "record_auth",
    "record_knowledge",
    "record_evaluation",
    "record_database",
    "record_rag",
    "record_memory",
    "record_agent",
    "health_report",
    "readiness_report",
    "liveness_report",
    "dependency_checks",
    "system_status",
    "capture_exception",
    "categorize_exception",
    "record_unhandled",
    "recovery_hint",
    "start_trace",
    "end_trace",
    "span",
    "trace_api_request",
    "trace_workflow",
    "trace_job",
    "trace_agent",
    "get_trace_id",
    "get_span_id",
    "new_trace_id",
]
