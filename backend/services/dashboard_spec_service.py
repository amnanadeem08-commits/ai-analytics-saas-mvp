from __future__ import annotations

from typing import Any

import pandas as pd

from backend.models.domain_context_models import DomainContext
from backend.processing.column_detector import detect_column_types
from backend.services.ai_business_insight_service import build_ai_business_insights_from_data_insights
from backend.services.data_insights_service import build_data_insights
from backend.services.domain_intelligence_service import ensure_domain_context
from backend.services.domain_profile_service import domain_profile
from backend.utils.response_utils import to_json_safe


FINANCIAL_TOKENS = ("revenue", "sales", "profit", "cost", "expense", "amount", "income", "spend")
DURATION_TOKENS = ("hour", "duration", "sleep", "screen_time", "time_before_sleep", "social_media")
SCORE_TOKENS = ("score", "rating", "risk", "percent", "percentage", "rate")
TARGET_TOKENS = ("target", "risk", "churn", "fraud", "outcome", "label", "diagnosis")
ID_TOKENS = ("id", "code", "uuid", "key")


def _name(column: str) -> str:
    return str(column).lower().replace(" ", "_").replace("-", "_")


def _classify_column(column: str, df: pd.DataFrame, detected: dict[str, list[str]]) -> dict[str, Any]:
    name = _name(column)
    unique_count = int(df[column].nunique(dropna=True)) if column in df.columns else 0
    row_count = max(int(len(df)), 1)
    roles: list[str] = []
    if column in detected.get("numeric_columns", []):
        roles.append("numeric")
    if column in detected.get("categorical_columns", []):
        roles.append("categorical")
    if column in detected.get("date_columns", []):
        roles.append("date")
    if name == "id" or name.endswith("_id") or any(token == name for token in ID_TOKENS):
        roles.append("id")
    if any(token in name for token in TARGET_TOKENS):
        roles.append("target_risk")
    if any(token in name for token in FINANCIAL_TOKENS):
        roles.append("financial")
    if any(token in name for token in DURATION_TOKENS):
        roles.append("duration_hour")
    if any(token in name for token in SCORE_TOKENS):
        roles.append("score_rating")
    if not roles:
        roles.append("general")
    return {
        "name": column,
        "roles": sorted(set(roles)),
        "unique_count": unique_count,
        "unique_ratio": round(unique_count / row_count, 4),
        "missing_count": int(df[column].isna().sum()) if column in df.columns else 0,
    }


def _suggest_slicers(df: pd.DataFrame, column_roles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    slicers: list[dict[str, Any]] = []
    for item in column_roles:
        column = item["name"]
        roles = set(item.get("roles", []))
        if "date" in roles:
            slicers.append({"field": column, "type": "date_range", "label": column.replace("_", " ").title()})
        elif "categorical" in roles and item.get("unique_count", 0) <= 25:
            values = sorted(df[column].dropna().astype(str).unique().tolist())[:50]
            slicers.append({"field": column, "type": "categorical", "label": column.replace("_", " ").title(), "values": values})
        elif "numeric" in roles and item.get("unique_count", 0) <= 100:
            series = pd.to_numeric(df[column], errors="coerce").dropna()
            if not series.empty:
                slicers.append({"field": column, "type": "numeric_range", "label": column.replace("_", " ").title(), "min": float(series.min()), "max": float(series.max())})
    return slicers[:8]


def _chart_summary(chart: dict[str, Any]) -> dict[str, Any]:
    return {
        "chart_id": chart.get("chart_id"),
        "title": chart.get("title"),
        "chart_type": chart.get("chart_type"),
        "fields": chart.get("columns") or chart.get("fields") or [],
        "insight": (chart.get("metadata") or {}).get("short_ai_insight") or (chart.get("metadata") or {}).get("subtitle") or "Recommended visual generated from dataset structure.",
        "spec": chart.get("spec") or {},
    }


def build_dashboard_spec(
    dataset_id: str,
    df: pd.DataFrame,
    dashboard: dict[str, Any],
    data_insights: dict[str, Any] | None = None,
    ai_business: dict[str, Any] | None = None,
) -> dict[str, Any]:
    detected_types = detect_column_types(df)
    data_insights = data_insights or build_data_insights(df)
    raw_context = dashboard.get("domain_context")
    if isinstance(raw_context, dict) and "detected_domain" in raw_context and "domain_context" not in raw_context:
        raw_context = {"domain_context": raw_context}
    domain_context: DomainContext = ensure_domain_context(raw_context or dashboard.get("domain_intelligence"), df)
    domain_detection = {
        "domain": domain_context.detected_domain,
        "confidence": domain_context.confidence,
        "confidence_score": domain_context.confidence_score,
        "signals": domain_context.detection_signals,
    }
    ai_business = ai_business or build_ai_business_insights_from_data_insights(data_insights, domain_context=domain_context)
    column_roles = [_classify_column(column, df, detected_types) for column in df.columns]
    charts = dashboard.get("chart_specs", []) or []
    kpis = dashboard.get("kpi_cards", []) or []
    recommendations = ai_business.get("recommendations") or []
    risks = ai_business.get("risks") or []
    opportunities = ai_business.get("opportunities") or []
    profile = domain_profile(domain_detection.get("domain"))
    classifier = domain_context.dataset_classifier or {}
    business_context_engine = domain_context.business_context_engine or {}
    dynamic_storyboard_template = domain_context.storyboard_template or {}
    dynamic_dashboard_template = domain_context.dashboard_template or {}
    domain_kpis = domain_context.domain_specific_kpis or []

    template_sections = dynamic_storyboard_template.get("sections") or []
    if template_sections:
        storyboard_blueprint = [
            {
                "section_id": section.get("section_id"),
                "title": section.get("title"),
                "intent": section.get("intent"),
                "order": section.get("order"),
            }
            for section in template_sections
        ]
    else:
        storyboard_blueprint = [{"title": section, "source": section.lower().replace(" ", "_")} for section in profile.get("storyboard_sections", [])]

    confidence_score = float(domain_detection.get("confidence_score") or 0)
    domain_score = int(domain_detection.get("score") or round(confidence_score * 100))

    spec = {
        "dataset_id": dataset_id,
        "status": "ready" if len(df) else "empty",
        "domain": {
            "detected": domain_context.detected_domain,
            "confidence": domain_context.confidence,
            "score": domain_score,
            "signals": domain_context.detection_signals,
        },
        "domain_context": domain_context.to_dict().get("domain_context", {}),
        "dataset_classifier": classifier,
        "business_context_engine": business_context_engine,
        "dynamic_storyboard_template": dynamic_storyboard_template,
        "dynamic_dashboard_template": dynamic_dashboard_template,
        "visualization_rules": domain_context.visualization_rules,
        "language_policy": domain_context.language_policy,
        "executive_summary_style": domain_context.executive_summary_style,
        "recommended_questions": domain_context.recommended_questions,
        "rag_context": domain_context.rag_context,
        "industry": domain_context.industry,
        "column_roles": column_roles,
        "default_dashboard": {
            "title": "Auto BI Dashboard",
            "kpis": kpis[:8],
            "domain_specific_kpis": domain_kpis[:8],
            "data_quality": dashboard.get("data_quality_score", {}),
            "charts": [_chart_summary(chart) for chart in charts[:8]],
            "slicers": _suggest_slicers(df, column_roles),
            "template_widgets": dynamic_dashboard_template.get("widgets", []),
            "insights": ai_business.get("cards", [])[:6],
            "risks": risks[:5],
            "opportunities": opportunities[:5],
            "recommendations": recommendations[:5],
        },
        "storyboard_blueprint": storyboard_blueprint,
        "domain_knowledge": profile.get("knowledge", []),
        "dashboard_widgets": [item.get("title") for item in dynamic_dashboard_template.get("widgets", [])] or profile.get("dashboard_widgets", []),
    }
    return to_json_safe(spec)


def build_export_bundle(
    dataset_id: str,
    dashboard: dict[str, Any],
    data_insights: dict[str, Any],
    ai_business: dict[str, Any],
    storyboard: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bundle = {
        "dataset_id": dataset_id,
        "status": "ready",
        "dashboard_spec": dashboard.get("dashboard_spec", {}),
        "kpi_cards": dashboard.get("kpi_cards", []),
        "chart_specs": dashboard.get("chart_specs", []),
        "data_insights": data_insights,
        "ai_business_insights": ai_business,
        "recommendations": ai_business.get("recommendations", []),
        "storyboard": storyboard or {},
        "excel_sheets": ["Data", "Stats Summary", "KPIs", "AI Insights", "Recommendations", "Charts"],
        "exports": {"pptx": True, "pdf": True, "excel": True, "chart_images": True},
    }
    return to_json_safe(bundle)
