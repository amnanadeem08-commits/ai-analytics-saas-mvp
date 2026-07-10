from __future__ import annotations

from typing import Any

from backend.services.ai_business_insight_service import build_ai_business_insights
from backend.services.dashboard_service import build_dashboard_view
from backend.services.domain_intelligence_service import ensure_domain_context
from backend.services.domain_profile_service import domain_profile
from backend.services.data_insights_service import build_data_insights
from backend.services.dataset_service import load_dataset_dataframe
from backend.utils.response_utils import to_json_safe


def _fallback_summary() -> dict[str, Any]:
    return {
        "dataset_readiness": {"score": 0, "ready": False, "reason": "No dataset rows available."},
        "overall_business_health": 0,
        "executive_summary": "No executive storyboard can be generated until validated dataset evidence exists.",
        "top_opportunity": "Insufficient evidence to identify an opportunity.",
        "biggest_risk": "Insufficient evidence to identify a risk.",
    }


def _card_by_type(cards: list[dict[str, Any]], card_type: str) -> dict[str, Any] | None:
    return next((card for card in cards if card.get("type") == card_type), None)


def _recommendation_priority(card: dict[str, Any]) -> str:
    card_type = card.get("type")
    confidence = float(card.get("confidence_score") or 0)
    if card_type == "Risk" and confidence >= 0.45:
        return "High"
    if card_type in {"Opportunity", "Trend"} and confidence >= 0.65:
        return "High"
    if confidence >= 0.45:
        return "Medium"
    return "Low"


def _recommendation_difficulty(card: dict[str, Any]) -> str:
    card_type = card.get("type")
    if card_type == "Forecast":
        return "High"
    if card.get("evidence_status") == "insufficient":
        return "Medium"
    return "Low"


def _build_recommendations(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    rows: list[dict[str, Any]] = []
    for card in cards:
        recommendation = card.get("executive_recommendation")
        if not recommendation:
            continue
        priority = _recommendation_priority(card)
        rows.append(
            {
                "title": card.get("title"),
                "priority": priority,
                "business_value": card.get("business_meaning"),
                "difficulty": _recommendation_difficulty(card),
                "expected_impact": card.get("expected_business_impact"),
                "recommendation": recommendation,
                "source_type": card.get("type"),
            }
        )
    return sorted(rows, key=lambda item: priority_rank.get(item["priority"], 9))


def _section_titles(dashboard: dict[str, Any], domain_name: str | None) -> list[str]:
    template_sections = (((dashboard.get("dashboard_spec") or {}).get("dynamic_storyboard_template") or {}).get("sections") or [])
    titles = [str(section.get("title")) for section in template_sections if section.get("title")]
    if titles:
        return titles
    intelligence_sections = (((dashboard.get("domain_intelligence") or {}).get("dynamic_storyboard_template") or {}).get("sections") or [])
    intelligence_titles = [str(section.get("title")) for section in intelligence_sections if section.get("title")]
    if intelligence_titles:
        return intelligence_titles
    profile = domain_profile(domain_name)
    return list(profile.get("storyboard_sections", []))


def build_executive_storyboard(dataset_id: str) -> dict[str, Any]:
    df = load_dataset_dataframe(dataset_id)
    data_insights = build_data_insights(df)
    ai_business = build_ai_business_insights(dataset_id)
    dashboard = build_dashboard_view(dataset_id)

    cards = ai_business.get("cards", [])
    opportunity = _card_by_type(cards, "Opportunity")
    risk = _card_by_type(cards, "Risk")
    readiness = (data_insights.get("readiness_score") or {}).get("ai_analysis") or {}
    health = data_insights.get("dataset_health") or {}
    kpis = dashboard.get("kpi_cards", []) or []
    raw_context = dashboard.get("domain_context")
    if isinstance(raw_context, dict) and "detected_domain" in raw_context and "domain_context" not in raw_context:
        raw_context = {"domain_context": raw_context}
    domain_context = ensure_domain_context(raw_context or dashboard.get("domain_intelligence"), df)
    domain_kpis = domain_context.domain_specific_kpis
    charts = dashboard.get("chart_specs", []) or []
    domain_name = domain_context.detected_domain or (((dashboard.get("dashboard_spec") or {}).get("domain") or {}).get("detected"))
    profile = domain_profile(domain_name)
    dashboard_spec = dashboard.get("dashboard_spec") or {}
    business_context = (
        (dashboard_spec.get("business_context_engine") or {}).get("business_context")
        or domain_context.business_context
        or profile.get("context")
        or "General business analytics and decision support"
    )
    section_names = _section_titles(dashboard, domain_name)

    stitched_kpis = list(kpis)
    for index, item in enumerate(domain_kpis[:3]):
        stitched_kpis.insert(
            min(index, len(stitched_kpis)),
            {
                "kpi_id": f"story_domain_{item.get('label', 'kpi').lower().replace(' ', '_')}",
                "label": item.get("label", "Domain KPI"),
                "value": item.get("value"),
                "format": item.get("format", "number"),
                "business_context": "Domain-specific KPI injected by domain intelligence.",
                "description": "This metric is selected from domain-aware KPI logic.",
            },
        )

    if data_insights.get("status") == "empty":
        executive_summary = _fallback_summary()
    else:
        health_score = health.get("overall_data_quality_score", 0)
        domain_label = profile.get("domain", "Generic Business Dataset")
        executive_summary = {
            "dataset_readiness": readiness,
            "overall_business_health": health_score,
            "executive_summary": (
                f"{domain_label} context: {business_context}. "
                f"Dataset is {readiness.get('score', 0)}/100 ready for AI-backed executive analysis, "
                f"with business health score {health_score}/100 and {len(stitched_kpis)} available KPI cards."
            ),
            "top_opportunity": (opportunity or {}).get("business_meaning") or "No validated opportunity is available.",
            "biggest_risk": (risk or {}).get("business_meaning") or "No validated risk is available.",
        }

    return to_json_safe(
        {
            "dataset_id": dataset_id,
            "status": data_insights.get("status", "ready"),
            "sections": [
                {"section_id": "executive_summary", "title": section_names[0] if len(section_names) > 0 else "Executive Summary", "order": 1, "content": executive_summary},
                {"section_id": "kpi_overview", "title": section_names[1] if len(section_names) > 1 else "KPI Overview", "order": 2, "kpis": stitched_kpis[:8]},
                {"section_id": "ai_business_insights", "title": section_names[2] if len(section_names) > 2 else "AI Business Insights", "order": 3, "cards": cards},
                {"section_id": "executive_charts", "title": section_names[3] if len(section_names) > 3 else "Executive Charts", "order": 4, "charts": charts[:6]},
                {"section_id": "executive_recommendations", "title": section_names[-1] if section_names else "Executive Recommendations", "order": 5, "recommendations": _build_recommendations(cards)},
            ],
            "source_payloads": {
                "data_insights_status": data_insights.get("status"),
                "ai_business_insights_status": ai_business.get("status"),
                "dashboard_status": dashboard.get("status"),
            },
        }
    )
