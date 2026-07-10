from __future__ import annotations

import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Iterator

_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_span_id: ContextVar[str | None] = ContextVar("span_id", default=None)
_spans: ContextVar[list[dict[str, Any]]] = ContextVar("spans", default=[])


@dataclass
class Span:
    name: str
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    trace_id: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    parent_span_id: str | None = None


def new_trace_id() -> str:
    return f"trace_{uuid.uuid4().hex}"


def new_span_id() -> str:
    return uuid.uuid4().hex[:16]


def get_trace_id() -> str | None:
    return _trace_id.get()


def get_span_id() -> str | None:
    return _span_id.get()


def start_trace(trace_id: str | None = None) -> str:
    tid = trace_id or new_trace_id()
    _trace_id.set(tid)
    _spans.set([])
    return tid


def end_trace() -> dict[str, Any]:
    return {"trace_id": _trace_id.get(), "spans": list(_spans.get() or [])}


@contextmanager
def span(name: str, **attributes: Any) -> Iterator[Span]:
    parent = _span_id.get()
    current = Span(name=name, trace_id=_trace_id.get() or start_trace(), attributes=dict(attributes), parent_span_id=parent)
    token_span = _span_id.set(current.span_id)
    stack = list(_spans.get() or [])
    stack.append({"name": name, "span_id": current.span_id, "parent_span_id": parent, "attributes": dict(attributes)})
    _spans.set(stack)
    try:
        yield current
    finally:
        _span_id.reset(token_span)


def trace_api_request(method: str, path: str) -> str:
    tid = start_trace()
    with span("api.request", method=method, path=path):
        return tid


def trace_workflow(workflow_id: str) -> str:
    tid = start_trace()
    with span("workflow.execute", workflow_id=workflow_id):
        return tid


def trace_job(job_id: str, job_type: str = "") -> str:
    tid = start_trace()
    with span("job.run", job_id=job_id, job_type=job_type):
        return tid


def trace_agent(agent_name: str) -> str:
    tid = start_trace()
    with span("agent.run", agent_name=agent_name):
        return tid
