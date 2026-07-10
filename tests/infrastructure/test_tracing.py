from __future__ import annotations

from backend.monitoring.tracing import end_trace, get_trace_id, span, start_trace, trace_job


def test_trace_and_span_lifecycle():
    tid = start_trace("trace_test")
    assert get_trace_id() == "trace_test"
    with span("step.one", key="value"):
        pass
    trace = end_trace()
    assert trace["trace_id"] == tid
    assert len(trace["spans"]) >= 1


def test_trace_job_helper():
    tid = trace_job("job_123", "generic")
    assert tid.startswith("trace_")
