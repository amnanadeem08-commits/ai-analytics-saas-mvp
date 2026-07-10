from __future__ import annotations

from backend.monitoring.errors import capture_exception, categorize_exception, recovery_hint
from backend.monitoring.health import health_report, liveness_report, readiness_report
from backend.monitoring.registry import reset_registry


def setup_function():
    reset_registry()


def test_liveness_and_readiness():
    live = liveness_report()
    assert live["alive"] is True
    ready = readiness_report()
    assert "ready" in ready


def test_health_report_structure():
    report = health_report()
    assert report["status"] in {"ok", "degraded"}
    assert "dependencies" in report
    assert "configuration" in report["dependencies"]


def test_error_capture_and_category():
    exc = ValueError("bad input")
    payload = capture_exception(exc, context={"path": "/x"})
    assert payload["category"] == "validation"
    assert categorize_exception(FileNotFoundError("x")) == "not_found"
    assert recovery_hint("validation")
