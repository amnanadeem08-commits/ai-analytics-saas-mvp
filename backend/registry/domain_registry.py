from __future__ import annotations

from typing import Any, Callable

import pandas as pd

from backend.registry.domain_plugin import DomainPlugin
from backend.services.domain_policy_service import build_domain_policy


def _slug(text: str) -> str:
    return str(text or "").strip().lower().replace("&", "and").replace(" ", "_").replace("-", "_")


def _storyboard_from_profile(profile: dict[str, Any], dataset_type: str) -> dict[str, Any]:
    sections = [
        {
            "section_id": _slug(title),
            "title": title,
            "order": idx + 1,
            "intent": "time_analysis" if "trend" in title.lower() else "domain_analysis",
        }
        for idx, title in enumerate(profile.get("storyboard_sections", []))
    ]
    if dataset_type in {"time_series", "panel_time_series"} and not any("trend" in section["title"].lower() for section in sections):
        sections.insert(min(2, len(sections)), {"section_id": "time_trends", "title": "Time Trends", "order": 3, "intent": "time_analysis"})
    for idx, section in enumerate(sections):
        section["order"] = idx + 1
    return {
        "template_id": f"storyboard_{_slug(profile.get('domain'))}_{dataset_type}",
        "domain": profile.get("domain"),
        "dataset_type": dataset_type,
        "sections": sections,
    }


def _dashboard_from_profile(profile: dict[str, Any], dataset_type: str) -> dict[str, Any]:
    widgets = []
    for idx, widget in enumerate(profile.get("dashboard_widgets", []), start=1):
        kind = "trend" if "trend" in widget.lower() else "kpi" if "kpi" in widget.lower() else "chart"
        widgets.append({"widget_id": f"widget_{idx}_{_slug(widget)}", "title": widget, "kind": kind, "order": idx})
    if dataset_type in {"time_series", "panel_time_series"} and not any("trend" in item.get("title", "").lower() for item in widgets):
        widgets.append({"widget_id": "widget_time_trend", "title": "Time Trend", "kind": "trend", "order": len(widgets) + 1})
    return {
        "template_id": f"dashboard_{_slug(profile.get('domain'))}_{dataset_type}",
        "domain": profile.get("domain"),
        "dataset_type": dataset_type,
        "widgets": widgets,
        "layout": "grid_2x2" if len(widgets) <= 4 else "grid_3x2",
    }


class ProfileBackedDomainPlugin(DomainPlugin):
    def __init__(
        self,
        *,
        name: str,
        aliases: tuple[str, ...],
        profile_supplier: Callable[[str], dict[str, Any]],
        kpi_provider: Callable[[pd.DataFrame, dict[str, Any], dict[str, Any], dict[str, Any] | None], list[dict[str, Any]]],
    ) -> None:
        self.name = name
        self.aliases = aliases
        self.profile_supplier = profile_supplier
        self.kpi_provider = kpi_provider

    def build_context(self, *, detection: dict[str, Any], classifier: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
        return {
            "detected_domain": detection.get("domain", profile.get("domain", self.name)),
            "confidence": detection.get("confidence", "low"),
            "confidence_score": float(detection.get("confidence_score") or 0.0),
            "business_context": profile.get("context", "General business analytics and evidence-based decision support."),
            "industry": profile.get("domain", self.name),
        }

    def get_kpis(self, df: pd.DataFrame, *, detection: dict[str, Any], classifier: dict[str, Any]) -> list[dict[str, Any]]:
        return self.kpi_provider(df, detection, classifier, None)

    def get_storyboard(self, *, classifier: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
        return _storyboard_from_profile(profile, classifier.get("dataset_type", "tabular"))

    def get_dashboard(self, *, classifier: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
        return _dashboard_from_profile(profile, classifier.get("dataset_type", "tabular"))

    def get_language_policy(self) -> dict[str, Any]:
        return build_domain_policy(self.name)

    def get_visualization_policy(self, *, classifier: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
        return {
            "preferred_widgets": profile.get("dashboard_widgets", []),
            "preferred_storyboard_sections": profile.get("storyboard_sections", []),
            "dataset_type": classifier.get("dataset_type", "tabular"),
            "layout_hint": "time_series_first" if classifier.get("dataset_type") in {"time_series", "panel_time_series"} else "balanced",
        }

    def get_recommendations(self, *, classifier: dict[str, Any], profile: dict[str, Any]) -> list[str]:
        primary_metric = (profile.get("metrics") or ["primary KPI"])[0]
        return [
            f"Prioritize {primary_metric} with clear owner and review cadence.",
            "Validate assumptions with segment-level evidence before rollout.",
        ]

    def get_suggested_questions(self, *, classifier: dict[str, Any], profile: dict[str, Any]) -> list[str]:
        metric = classifier.get("primary_metric") or (profile.get("metrics") or ["primary metric"])[0]
        segment = classifier.get("key_dimension") or "top segment"
        return [
            f"Which {segment} is driving the strongest movement in {metric}?",
            f"What is the highest-priority risk in {profile.get('domain', self.name)} performance?",
            "Which action should leadership prioritize next?",
        ]


class HealthcareDomain(ProfileBackedDomainPlugin):
    pass


class SalesDomain(ProfileBackedDomainPlugin):
    pass


class CustomerChurnDomain(ProfileBackedDomainPlugin):
    pass


class GenericBusinessDomain(ProfileBackedDomainPlugin):
    pass


class DomainRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, DomainPlugin] = {}
        self._aliases: dict[str, str] = {}

    def register(self, plugin: DomainPlugin) -> None:
        self._plugins[plugin.name] = plugin
        self._aliases[plugin.name.lower()] = plugin.name
        for alias in plugin.aliases:
            self._aliases[alias.lower()] = plugin.name

    def resolve(self, domain: str | None) -> DomainPlugin:
        key = self._aliases.get(str(domain or "").lower(), str(domain or "Generic Business Dataset"))
        return self._plugins.get(key) or self._plugins.get("Generic Business Dataset")

    def registered_domains(self) -> list[str]:
        return sorted(self._plugins)
