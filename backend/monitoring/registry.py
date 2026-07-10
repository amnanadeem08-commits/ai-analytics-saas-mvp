from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricSample:
    name: str
    metric_type: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    help_text: str = ""


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._timers: dict[str, list[float]] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    def _key(self, name: str, labels: dict[str, str] | None) -> str:
        if not labels:
            return name
        parts = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{parts}}}"

    def counter(self, name: str, value: float = 1.0, *, labels: dict[str, str] | None = None, help_text: str = "") -> None:
        key = self._key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value
            self._metadata.setdefault(key, {"type": "counter", "help": help_text, "name": name})

    def gauge(self, name: str, value: float, *, labels: dict[str, str] | None = None, help_text: str = "") -> None:
        key = self._key(name, labels)
        with self._lock:
            self._gauges[key] = value
            self._metadata.setdefault(key, {"type": "gauge", "help": help_text, "name": name})

    def observe(self, name: str, value: float, *, labels: dict[str, str] | None = None, help_text: str = "") -> None:
        key = self._key(name, labels)
        with self._lock:
            self._timers.setdefault(key, []).append(value)
            self._metadata.setdefault(key, {"type": "timer", "help": help_text, "name": name})

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            timers = {}
            for key, values in self._timers.items():
                if not values:
                    continue
                timers[key] = {
                    "count": len(values),
                    "sum": sum(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                }
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "timers": timers,
                "metadata": dict(self._metadata),
            }

    def clear(self) -> None:
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._timers.clear()
            self._metadata.clear()


_REGISTRY: MetricsRegistry | None = None


def get_registry() -> MetricsRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = MetricsRegistry()
    return _REGISTRY


def reset_registry() -> None:
    global _REGISTRY
    if _REGISTRY is not None:
        _REGISTRY.clear()
    _REGISTRY = None
