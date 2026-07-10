from __future__ import annotations

from backend.monitoring.registry import get_registry


def inc_counter(name: str, value: float = 1.0, *, labels: dict[str, str] | None = None) -> None:
    get_registry().counter(name, value, labels=labels)


def set_gauge(name: str, value: float, *, labels: dict[str, str] | None = None) -> None:
    get_registry().gauge(name, value, labels=labels)


def observe_timer(name: str, value: float, *, labels: dict[str, str] | None = None) -> None:
    get_registry().observe(name, value, labels=labels)


def export_metrics() -> dict:
    return get_registry().snapshot()
