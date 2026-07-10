from __future__ import annotations

from backend.monitoring.counters import export_metrics, inc_counter, set_gauge
from backend.monitoring.metrics import record_api_request, record_job, record_workflow
from backend.monitoring.registry import reset_registry
from backend.monitoring.timers import timer


def setup_function():
    reset_registry()


def test_counter_and_gauge():
    inc_counter("test_counter", labels={"a": "1"})
    inc_counter("test_counter", labels={"a": "1"})
    set_gauge("test_gauge", 42.0)
    snap = export_metrics()
    assert snap["counters"]
    assert snap["gauges"]["test_gauge"] == 42.0


def test_timer_context_manager():
    with timer("test_timer"):
        pass
    snap = export_metrics()
    assert "test_timer" in snap["timers"]


def test_domain_recorders():
    record_api_request(method="GET", path="/x", status_code=200, duration_ms=12.5)
    record_workflow(event="started")
    record_job(event="submitted", job_type="generic")
    snap = export_metrics()
    assert snap["counters"]
