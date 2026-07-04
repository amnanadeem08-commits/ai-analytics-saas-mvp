from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class VisualizationPolicy:
    domain: str
    preferred_charts: list[str] = field(default_factory=list)
    fallback_charts: list[str] = field(default_factory=lambda: ["bar", "line", "table"])
    section_chart_hints: dict[str, list[str]] = field(default_factory=dict)


class VisualizationRegistry:
    def __init__(self) -> None:
        self._policies: dict[str, VisualizationPolicy] = {}
        self._aliases: dict[str, str] = {}

    def register(self, policy: VisualizationPolicy, aliases: tuple[str, ...] = ()) -> None:
        self._policies[policy.domain] = policy
        self._aliases[policy.domain.lower()] = policy.domain
        for alias in aliases:
            self._aliases[alias.lower()] = policy.domain

    def resolve(self, domain: str | None) -> VisualizationPolicy:
        key = self._aliases.get(str(domain or "").lower(), str(domain or "Generic Business Dataset"))
        return self._policies.get(key) or self._policies.get("Generic Business Dataset") or VisualizationPolicy(domain="Generic Business Dataset")

    def recommend_for_section(self, domain: str | None, section_id: str, kpi_label: str | None = None) -> dict[str, Any]:
        policy = self.resolve(domain)
        section_key = str(section_id or "").lower().strip()
        ranked = list(policy.section_chart_hints.get(section_key) or policy.preferred_charts or policy.fallback_charts)
        if kpi_label and any(token in str(kpi_label).lower() for token in ("rate", "ratio", "percent", "%")):
            ranked = ["line", "bar", "table"] + [chart for chart in ranked if chart not in {"line", "bar", "table"}]
        return {
            "domain": policy.domain,
            "section_id": section_id,
            "ranked_chart_types": ranked,
            "fallback_chart_types": list(policy.fallback_charts),
        }

    def rank_chart_suitability(self, domain: str | None, chart_type: str, *, section_id: str | None = None) -> int:
        policy = self.resolve(domain)
        chart = str(chart_type or "").lower().strip()
        if section_id:
            section_rank = policy.section_chart_hints.get(str(section_id).lower(), [])
            if chart in section_rank:
                return max(1, 100 - section_rank.index(chart) * 20)
        if chart in policy.preferred_charts:
            return max(1, 90 - policy.preferred_charts.index(chart) * 15)
        if chart in policy.fallback_charts:
            return max(1, 60 - policy.fallback_charts.index(chart) * 10)
        return 20
