from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class MetricDefinition:
    name: str
    business_meaning: str
    metric_category: str
    executive_importance: str
    preferred_visualizations: list[str]
    benchmark_compatibility: bool
    aggregation_strategy: str


class MetricRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, MetricDefinition] = {}

    def register(self, definition: MetricDefinition) -> None:
        self._definitions[definition.name.lower()] = definition

    def get(self, metric_name: str | None) -> MetricDefinition | None:
        if not metric_name:
            return None
        name = str(metric_name).strip().lower()
        if name in self._definitions:
            return self._definitions[name]
        for key, definition in self._definitions.items():
            if key in name or name in key:
                return definition
        return None

    def to_lookup_dict(self, metric_name: str | None) -> dict[str, Any]:
        definition = self.get(metric_name)
        if not definition:
            return {}
        return {
            "name": definition.name,
            "business_meaning": definition.business_meaning,
            "metric_category": definition.metric_category,
            "executive_importance": definition.executive_importance,
            "preferred_visualizations": list(definition.preferred_visualizations),
            "benchmark_compatibility": definition.benchmark_compatibility,
            "aggregation_strategy": definition.aggregation_strategy,
        }
