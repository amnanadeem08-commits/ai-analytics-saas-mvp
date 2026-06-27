from __future__ import annotations

from typing import Any

from backend.core.branding_manager import branding_manager
from backend.services.dashboard_service import build_dashboard_view
from backend.services.executive_storyboard_service import build_executive_storyboard
from backend.services.insight_service import get_insights
from backend.services.storytelling_service import build_business_story


def build_report_payload(dataset_id: str) -> dict[str, Any]:
    dashboard = build_dashboard_view(dataset_id)
    insights = get_insights(dataset_id)
    executive_summary = insights.get("executive_summary") or {}
    story = build_business_story(executive_summary)
    return {
        "dataset_id": dataset_id,
        "branding": branding_manager.get().to_dict(),
        "theme": dashboard.get("theme", {}),
        "overview": dashboard["overview"],
        "kpi_cards": dashboard["kpi_cards"],
        "executive_summary": executive_summary,
        "business_story": story,
        "domain_intelligence": dashboard.get("domain_intelligence", {}),
        "regional_analytics": dashboard.get("regional_analytics", {}),
        "analysis_guardrails": dashboard.get("analysis_guardrails", {}),
        "data_quality_score": dashboard.get("data_quality_score", {}),
        "suggested_questions": dashboard.get("suggested_questions", []),
        "chart_specs": dashboard["chart_specs"],
        "chart_count": len(dashboard["chart_specs"]),
        "executive_storyboard": build_executive_storyboard(dataset_id),
    }
