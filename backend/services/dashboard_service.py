from __future__ import annotations

from functools import lru_cache
import logging
from time import perf_counter
from typing import Any

from backend.core.branding_manager import branding_manager
from backend.core.config import settings
from backend.models.domain_context_models import DomainContext
from backend.processing.analytics_engine import build_dashboard_stats
from backend.processing.data_profiler import profile_dataframe
from backend.processing.overview_service import build_dataset_overview
from backend.core.theme_manager import theme_manager
from backend.services.analysis_guardrail_service import build_analysis_guardrails
from backend.services.chart_service import generate_chart_specs
from backend.services.chart_catalog_service import load_custom_chart_specs
from backend.services.dataset_service import get_dataset_metadata, load_dataset_dataframe
from backend.services.domain_intelligence_service import build_domain_context
from backend.services.dashboard_spec_service import build_dashboard_spec
from backend.services.filter_service import apply_filters
from backend.services.geospatial_service import generate_geo_chart_specs, regional_analytics
from backend.services.kpi_service import compute_business_metrics, compute_kpi_cards
from backend.services.suggested_question_service import build_suggested_questions


def _build_dashboard_view_uncached(dataset_id: str, filters: dict[str, Any] | None = None) -> dict[str, Any]:
    theme = theme_manager.get_theme()
    branding = branding_manager.get()
    df = load_dataset_dataframe(dataset_id)
    original_row_count = int(len(df))
    df = apply_filters(df, filters)
    legacy_stats = build_dashboard_stats(df)
    profile = profile_dataframe(df)
    overview = build_dataset_overview(df, preview_rows=5, profile=profile)
    kpi_cards = compute_kpi_cards(df)
    domain_context: DomainContext = build_domain_context(df)
    domain_intelligence = domain_context.to_dict()
    business_metrics = compute_business_metrics(df)
    for index, card in enumerate(domain_context.domain_specific_kpis):
        kpi_cards.insert(
            min(index, len(kpi_cards)),
            {
                "kpi_id": f"domain_{card['label'].lower().replace(' ', '_')}",
                "label": card["label"],
                "value": card["value"],
                "format": card.get("format", "number"),
                "category": "business",
                "description": "Domain-specific KPI generated from detected dataset context.",
                "current_value": card["value"],
                "previous_value": None,
                "delta_percentage": None,
                "trend": "neutral",
                "trend_arrow": "->",
                "status": "warning" if "Churn" in card["label"] or "Depression" in card["label"] or "Anxiety" in card["label"] else "positive",
                "status_color": theme.warning if "Churn" in card["label"] or "Depression" in card["label"] or "Anxiety" in card["label"] else theme.success,
                "business_context": "Detected by the domain-aware KPI engine.",
                "sparkline": [],
                "reason": "This KPI is tied to the detected business domain and calculated from actual dataset fields.",
                "recommended_action": "Review the domain intelligence section for drivers and recommended actions.",
                "expected_impact": "Domain KPIs help leadership prioritize context-specific decisions.",
                "evidence": card.get("evidence", {}),
                "icon": "shield" if card.get("format") == "percent" else "chart",
                "risk_indicator": "risk" if "Churn" in card["label"] or "Depression" in card["label"] or "Anxiety" in card["label"] else "normal",
                "confidence_score": 0.82,
            },
        )
    chart_specs = generate_chart_specs(df, theme.name) + generate_geo_chart_specs(df, theme.name)
    generated_ids = {chart["chart_id"] for chart in chart_specs}
    chart_specs.extend(
        chart for chart in load_custom_chart_specs(dataset_id)
        if chart.get("chart_id") not in generated_ids
    )
    regional = regional_analytics(df)

    sections = [
        {
            "section_id": "kpi_overview",
            "title": "Executive KPI Overview",
            "description": "Power BI-style business scorecard.",
            "card_ids": [card["kpi_id"] for card in kpi_cards],
            "order": 1,
        },
        {
            "section_id": "visualizations",
            "title": "Dashboard Visuals",
            "description": "Presentation-ready Plotly charts with theme inheritance.",
            "chart_ids": [chart["chart_id"] for chart in chart_specs],
            "order": 2,
        },
        {
            "section_id": "categories",
            "title": "Category Breakdowns",
            "description": "Segment distribution and ranking visuals.",
            "chart_keys": list(legacy_stats["top_categories"].keys()),
            "order": 3,
        },
        {
            "section_id": "trends",
            "title": "Time Trends",
            "description": "Trend-ready time-series section.",
            "chart_keys": list(legacy_stats["time_trends"].keys()),
            "order": 4,
        },
        {
            "section_id": "relationships",
            "title": "Relationships",
            "description": "Correlation and relationship analysis.",
            "chart_keys": list(legacy_stats["correlations"].keys()),
            "order": 5,
        },
    ]

    result = {
        "dataset_id": dataset_id,
        "status": "ready",
        "theme": theme.to_dict(),
        "branding": branding.to_dict(),
        "filters": filters or {},
        "filtered": bool(filters),
        "original_row_count": original_row_count,
        "filtered_row_count": int(len(df)),
        "overview": {
            "row_count": overview["row_count"],
            "column_count": overview["column_count"],
            "column_groups": overview["column_groups"],
            "missing_summary": overview["missing_summary"],
        },
        "kpi_cards": kpi_cards,
        "chart_specs": chart_specs,
        "business_metrics": business_metrics,
        "domain_intelligence": domain_intelligence,
        "domain_context": domain_context.to_dict().get("domain_context", {}),
        "regional_analytics": regional,
        "analysis_guardrails": build_analysis_guardrails(df),
        "data_quality_score": profile.get("data_quality_score", {}),
        "suggested_questions": build_suggested_questions(
            business_metrics=business_metrics,
            domain_context=domain_context,
            profile=profile,
        ),
        "layout": {"sections": sections},
        **legacy_stats,
    }
    result["dashboard_spec"] = build_dashboard_spec(dataset_id, df, result)
    result["export_bundle"] = {
        "dataset_id": dataset_id,
        "dashboard_spec": result["dashboard_spec"],
        "kpi_cards": result["kpi_cards"],
        "chart_specs": result["chart_specs"],
        "excel_sheets": ["Data", "Stats Summary", "KPIs", "AI Insights", "Recommendations", "Charts"],
        "exports": {"pptx": True, "pdf": True, "excel": True, "chart_images": True},
    }
    return result

logger = logging.getLogger(__name__)


@lru_cache(maxsize=16)
def _build_dashboard_view_cached(
    dataset_id: str,
    file_hash: str,
    theme_name: str,
    branding_version: int,
    custom_chart_version: int,
) -> dict[str, Any]:
    del file_hash, theme_name, branding_version, custom_chart_version
    return _build_dashboard_view_uncached(dataset_id)


def build_dashboard_view(dataset_id: str, filters: dict[str, Any] | None = None) -> dict[str, Any]:
    started = perf_counter()
    if filters:
        result = _build_dashboard_view_uncached(dataset_id, filters)
        logger.info("dashboard_build dataset=%s filtered=true seconds=%.3f", dataset_id, perf_counter() - started)
        return result

    metadata = get_dataset_metadata(dataset_id)
    branding_version = settings.BRANDING_FILE.stat().st_mtime_ns if settings.BRANDING_FILE.exists() else 0
    custom_path = settings.DATASETS_DIR / dataset_id / "custom_chart_specs.json"
    custom_chart_version = custom_path.stat().st_mtime_ns if custom_path.exists() else 0
    before = _build_dashboard_view_cached.cache_info()
    result = _build_dashboard_view_cached(
        dataset_id,
        metadata.get("file_hash", ""),
        theme_manager.active_name(),
        branding_version,
        custom_chart_version,
    )
    after = _build_dashboard_view_cached.cache_info()
    logger.info(
        "dashboard_build dataset=%s cache_hit=%s seconds=%.3f",
        dataset_id,
        after.hits > before.hits,
        perf_counter() - started,
    )
    return result