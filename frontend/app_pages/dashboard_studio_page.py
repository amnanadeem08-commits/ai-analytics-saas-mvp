from __future__ import annotations

import html
import io
import json
import re
from datetime import date, datetime
from urllib.parse import urlencode

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import requests
import streamlit as st

from frontend.api_client.backend_client import BackendClient, DEFAULT_API_BASE_URL
from frontend.components.chart_components import (
    render_plotly_chart_specs,
    render_time_trends,
    render_top_categories,
)
from frontend.components.insight_cards import render_insight
from frontend.components.metric_cards import render_summary_metrics
from frontend.components.ai_insight_panel import render_business_insights_overview
from frontend.components.storyboard_session import add_storyboard_entry
from frontend.utils.backend_utils import (
    _build_local_dataset_id,
    _is_local_dataset_id,
    _warn_backend_unavailable,
    ensure_backend_available,
    get_client,
    is_local_dataset_id,
    render_backend_status,
    safe_table,
)
from frontend.utils.session_state import (
    _ensure_default_local_storyboard,
    _sync_storyboard_keys,
    initialize_session_state,
)
from frontend.utils.theme_manager import (
    DEFAULT_BRANDING,
    THEME_PRESETS,
    _ai_dashboard_css,
    _apply_branding_theme,
    _storyboard_theme_snapshot,
    get_active_branding,
    render_branding_editor,
    render_dashboard_settings,
    render_theme_selector,
)
from frontend.app_pages.dataset_page import _local_active_dataframe
from frontend.utils.local_helpers import (
    _build_local_visual_schema,
    _dashboard_studio_slicer_payload,
    _render_local_visual,
    select_dataset,
)
from frontend.utils.kpi_helpers import build_default_kpis


def _dashboard_studio_css() -> None:
    st.markdown(
        """
        <style>
        /* Dashboard Studio presentation-only styling */
        .ds-studio-wrap {
            padding: 12px 4px;
        }
        .ds-card {
            border: 1px solid rgba(148,163,184,0.25);
            border-radius: 16px;
            background: rgba(255,255,255,0.80);
            box-shadow: 0 8px 20px rgba(0,0,0,0.03);
            overflow: hidden;
        }
        .ds-card-header {
            padding: 14px 16px 10px 16px;
            border-bottom: 1px solid rgba(148,163,184,0.18);
            background: linear-gradient(180deg, rgba(148,163,184,0.08), rgba(255,255,255,0));
        }
        .ds-card-title {
            font-size: 1.00rem;
            font-weight: 900;
            color: var(--text-color);
            line-height: 1.2;
        }
        .ds-card-subtitle {
            font-size: 0.82rem;
            color: var(--text-subtle);
            margin-top: 4px;
            line-height: 1.35;
        }
        .ds-card-body {
            padding: 10px 12px 6px 12px;
        }
        .ds-card-footer {
            padding: 10px 12px 14px 12px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .ds-footer-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
        }
        .ds-confidence {
            font-size: 0.78rem;
            color: var(--text-muted-soft);
        }
        .ds-section-title {
            font-size: 1.02rem;
            font-weight: 900;
            margin-top: 4px;
        }
        .ds-muted-hint {
            font-size: 0.82rem;
            color: var(--text-subtle);
        }
        .ds-grid-gap > div {
            margin-bottom: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def _field_names(items: list[dict]) -> list[str]:
    return [item.get("name") for item in items if item.get("name")]


def _display_value(card: dict) -> str:
    return str(card.get("formatted_value", card.get("value", "-")))


def _local_quality(df: pd.DataFrame) -> dict:
    rows = int(len(df))
    cols = int(len(df.columns))
    cells = max(rows * cols, 1)
    missing = int(df.isna().sum().sum())
    duplicates = int(df.duplicated().sum())
    completeness = round((1 - missing / cells) * 100, 2)
    return {"score": completeness, "grade": "A" if completeness >= 95 and duplicates == 0 else "B" if completeness >= 85 else "C" if completeness >= 70 else "D", "missing_values": missing, "duplicate_rows": duplicates, "row_count": rows, "column_count": cols}


def _auto_chart_specs_from_schema(schema: dict) -> list[dict]:
    dimensions = _field_names(schema.get("dimensions", []))
    measures = _field_names(schema.get("measures", []))
    date_columns = schema.get("datetime_columns", []) or []
    specs: list[dict] = []
    if dimensions and measures:
        specs.append({"chart_type": "bar", "dimension": dimensions[0], "measure": measures[0], "aggregation": "auto", "sort": "descending", "title": f"{measures[0]} by {dimensions[0]}", "data_labels": True, "filters": {}})
    if date_columns and measures:
        specs.append({"chart_type": "line", "dimension": date_columns[0], "measure": measures[0], "aggregation": "auto", "sort": "ascending", "title": f"{measures[0]} trend", "data_labels": True, "filters": {}})
    if len(dimensions) > 1:
        specs.append({"chart_type": "bar", "dimension": dimensions[1], "measure": None, "aggregation": "count", "sort": "descending", "title": f"Records by {dimensions[1]}", "data_labels": True, "filters": {}})
    if dimensions and len(measures) > 1:
        specs.append({"chart_type": "horizontal_bar", "dimension": dimensions[0], "measure": measures[1], "aggregation": "auto", "sort": "descending", "title": f"{measures[1]} by {dimensions[0]}", "data_labels": True, "filters": {}})
    if dimensions:
        specs.append({"chart_type": "table", "dimension": dimensions[0], "measure": measures[0] if measures else None, "aggregation": "auto" if measures else "count", "sort": "descending", "title": "Top records summary", "data_labels": True, "filters": {}})
    return specs[:5]


def _slicer_summaries_from_schema(schema: dict) -> list[dict]:
    slicers = []
    for field in schema.get("semantic_layer", []):
        name = field.get("name")
        role = field.get("semantic_role") or field.get("semantic_type")
        unique = int(field.get("unique_count", 0) or 0)
        if role in {"date", "datetime"}:
            slicers.append({"field": name, "type": "date_range", "label": str(name).replace("_", " ").title()})
        elif role in {"dimension", "categorical"} and unique <= 25:
            slicers.append({"field": name, "type": "categorical", "label": str(name).replace("_", " ").title()})
        elif role in {"measure", "numeric"} and unique <= 100:
            slicers.append({"field": name, "type": "numeric_range", "label": str(name).replace("_", " ").title()})
    return slicers[:8]


def _build_local_auto_dashboard(df: pd.DataFrame, dataset_id: str, schema: dict) -> dict:
    specs = _auto_chart_specs_from_schema(schema)
    charts = []
    for index, spec in enumerate(specs):
        visual = _render_local_visual(df, spec)
        chart = visual.get("chart", {})
        chart["chart_id"] = chart.get("chart_id") or f"local_auto_{index}"
        chart["chart_type"] = spec.get("chart_type")
        chart["columns"] = [field for field in [spec.get("dimension"), spec.get("measure")] if field]
        chart["spec"] = spec
        charts.append(chart)
    kpis = build_default_kpis(df, dataset_id)[:8]
    quality = _local_quality(df)
    return {
        "dataset_id": dataset_id,
        "status": "ready",
        "overview": {"row_count": quality["row_count"], "column_count": quality["column_count"], "column_groups": {"numeric": schema.get("numeric_columns", []), "categorical": schema.get("categorical_columns", []), "datetime": schema.get("datetime_columns", [])}},
        "kpi_cards": kpis,
        "chart_specs": charts,
        "data_quality_score": {"score": quality["score"], "grade": quality["grade"]},
        "dashboard_spec": {"domain": {"detected": "Local Analytics", "confidence": "medium"}, "default_dashboard": {"kpis": kpis, "charts": charts, "slicers": _slicer_summaries_from_schema(schema), "insights": [], "recommendations": []}, "storyboard_blueprint": [{"title": "Dataset Overview", "source": "overview"}, {"title": "KPI Summary", "source": "kpis"}, {"title": "Dashboard Visuals", "source": "charts"}]},
        "export_bundle": {"excel_sheets": ["Data", "Stats Summary", "KPIs", "AI Insights", "Recommendations", "Charts"], "exports": {"pptx": True, "pdf": True, "excel": True, "chart_images": True}},
    }


def _render_auto_header(dashboard: dict) -> None:
    spec = dashboard.get("dashboard_spec", {})
    domain = spec.get("domain", {}) or dashboard.get("domain_intelligence", {}).get("detection", {})
    overview = dashboard.get("overview", {})
    domain_name = html.escape(str(domain.get("detected") or domain.get("domain") or "Generic"))
    html_block = (
        '<div style="border:1px solid rgba(148,163,184,.28);border-radius:10px;padding:16px 18px;margin:8px 0 14px;background:var(--ui-surface);">'
        '<div style="font-size:.76rem;font-weight:800;color:var(--primary-color);text-transform:uppercase;">Auto BI Dashboard</div>'
        '<div style="font-size:1.45rem;font-weight:850;color:var(--text-color);">Generated dashboard from dataset structure and BI rules</div>'
        f'<div style="font-size:.86rem;color:var(--text-muted);margin-top:4px;">{overview.get("row_count", 0):,} rows | {overview.get("column_count", 0):,} columns | Domain: {domain_name}</div>'
        '</div>'
    )
    st.markdown(html_block, unsafe_allow_html=True)


def _render_auto_kpis(cards: list[dict]) -> None:
    if not cards:
        st.info("No KPI cards are available for this dataset yet.")
        return
    for offset in range(0, min(len(cards), 8), 4):
        cols = st.columns(4)
        for col, card in zip(cols, cards[offset : offset + 4]):
            col.metric(str(card.get("label", "KPI")), _display_value(card))
            context = card.get("reason") or card.get("business_context") or card.get("description")
            if context:
                col.caption(str(context)[:140])


def _render_quality_and_filters(dashboard: dict, schema: dict, dataset_id: str) -> dict:
    quality = dashboard.get("data_quality_score", {}) or {}
    with st.container(border=True):
        st.markdown("#### Data Quality")
        qcols = st.columns(3)
        qcols[0].metric("Score", quality.get("score", "-"))
        qcols[1].metric("Grade", quality.get("grade", "-"))
        qcols[2].metric("Charts", len(dashboard.get("chart_specs", [])))
    with st.container(border=True):
        st.markdown("#### Filters")
        filters = _dashboard_studio_slicer_payload(schema, dataset_id)
        suggested = (dashboard.get("dashboard_spec", {}).get("default_dashboard", {}) or {}).get("slicers") or _slicer_summaries_from_schema(schema)
        if suggested:
            st.caption("Auto-suggested slicers: " + ", ".join(str(item.get("label", item.get("field", ""))) for item in suggested[:5]))
        return filters


def _render_auto_charts(charts: list[dict], *, compact: bool = False) -> None:
    if not charts:
        st.info("No chart-ready visuals were generated for this dataset.")
        return
    for offset in range(0, min(len(charts), 6), 2):
        cols = st.columns(2)
        for col, chart in zip(cols, charts[offset : offset + 2]):
            with col.container(border=True):
                st.markdown(f"**{chart.get('title', 'Dashboard Visual')}**")
                metadata = chart.get("metadata", {})
                if metadata.get("short_ai_insight") or metadata.get("subtitle"):
                    st.caption(metadata.get("short_ai_insight") or metadata.get("subtitle"))
                plotly_spec = chart.get("plotly", {})
                fig = go.Figure(data=plotly_spec.get("data", []), layout=plotly_spec.get("layout", {}))
                fig.update_layout(height=280 if compact else 340, margin={"l": 36, "r": 16, "t": 48, "b": 56})
                st.plotly_chart(fig, use_container_width=True)


def _render_auto_insights(ai_payload: dict | None, dashboard: dict) -> None:
    cards = (ai_payload or {}).get("cards") or (dashboard.get("dashboard_spec", {}).get("default_dashboard", {}) or {}).get("insights", [])
    if not cards:
        st.info("AI insight cards will appear here when backend insights are available.")
        return
    for card in cards[:4]:
        with st.container(border=True):
            st.markdown(f"**{card.get('title', card.get('type', 'Insight'))}**")
            st.write(card.get("business_meaning") or card.get("insight") or card.get("supporting_evidence") or "Validated insight generated from dataset evidence.")
            if card.get("executive_recommendation"):
                st.caption("Recommendation: " + str(card.get("executive_recommendation")))


def _render_customize_dashboard(client: BackendClient, dataset_id: str, schema: dict, dashboard: dict, local_df: pd.DataFrame | None, ai_payload: dict | None, storyboard: dict | None) -> None:
    with st.expander("Customize Dashboard", expanded=False):
        tabs = st.tabs(["KPIs", "Charts", "Slicers", "Insights", "Storyboard", "Export"])
        dimensions = _field_names(schema.get("dimensions", []))
        measures = _field_names(schema.get("measures", []))
        with tabs[0]:
            st.caption("Auto mode chooses averages for age/hour/duration/score, sums for financial measures, and counts for IDs/categories.")
            _render_auto_kpis(dashboard.get("kpi_cards", []))
            if measures:
                c1, c2 = st.columns(2)
                c1.selectbox("KPI Metric", measures, key=f"custom_kpi_metric_{dataset_id}")
                c2.selectbox("Aggregation", ["Auto", "Average", "Sum", "Median", "Min", "Max", "Count"], key=f"custom_kpi_agg_{dataset_id}")
        with tabs[1]:
            st.caption("Recommended visuals are generated first; manual chart settings are optional.")
            _render_auto_charts(dashboard.get("chart_specs", [])[:4], compact=True)
            if dimensions:
                c1, c2, c3 = st.columns(3)
                dimension = c1.selectbox("Dimension", dimensions, key=f"custom_chart_dim_{dataset_id}")
                measure = c2.selectbox("Measure", ["Count"] + measures, key=f"custom_chart_measure_{dataset_id}")
                aggregation = c3.selectbox("Aggregation", ["auto", "average", "sum", "median", "min", "max", "count"], key=f"custom_chart_agg_{dataset_id}")
                chart_type = st.selectbox("Chart Type", ["bar", "horizontal_bar", "line", "pie", "table"], key=f"custom_chart_type_{dataset_id}")
                if st.button("Preview Custom Chart", key=f"preview_custom_chart_{dataset_id}"):
                    spec = {"chart_type": chart_type, "dimension": dimension, "measure": None if measure == "Count" else measure, "aggregation": aggregation, "sort": "descending", "data_labels": True, "filters": {}}
                    visual = _render_local_visual(local_df, spec) if local_df is not None else client.render_visual(dataset_id, spec)
                    _render_auto_charts([visual.get("chart", {})])
        with tabs[2]:
            suggested = (dashboard.get("dashboard_spec", {}).get("default_dashboard", {}) or {}).get("slicers") or _slicer_summaries_from_schema(schema)
            st.dataframe(pd.DataFrame(suggested), use_container_width=True, hide_index=True)
        with tabs[3]:
            _render_auto_insights(ai_payload, dashboard)
        with tabs[4]:
            blueprint = dashboard.get("dashboard_spec", {}).get("storyboard_blueprint", [])
            if storyboard and storyboard.get("sections"):
                st.write(f"Storyboard sections: {len(storyboard.get('sections', []))}")
                st.dataframe(pd.DataFrame([{"Section": item.get("title"), "Order": item.get("order")} for item in storyboard.get("sections", [])]), use_container_width=True, hide_index=True)
            elif blueprint:
                st.dataframe(pd.DataFrame(blueprint), use_container_width=True, hide_index=True)
            else:
                st.info("Storyboard will be generated from overview, KPIs, insights, visuals, risks, and recommendations.")
        with tabs[5]:
            bundle = dashboard.get("export_bundle", {})
            st.write("Exports use the same dashboard/storyboard bundle.")
            exports = (bundle.get("exports") if isinstance(bundle, dict) else None) or {"pptx": True, "pdf": True, "excel": True}
            rows = [{"format": fmt.upper(), "enabled": bool(enabled)} for fmt, enabled in exports.items()]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_visual_builder(client: BackendClient) -> None:
    st.header("Dashboard Studio")
    st.caption("Auto BI builds the dashboard first. Customize only when you need to tune a KPI, chart, slicer, insight, storyboard, or export.")
    _dashboard_studio_css()
    dataset_id = select_dataset(client)
    if not dataset_id:
        return

    local_df = None
    ai_payload = None
    storyboard = None
    if is_local_dataset_id(dataset_id):
        local_df = _local_active_dataframe(dataset_id)
        if local_df is None:
            st.info("Upload a dataset first from Dataset Preview.")
            return
        schema = _build_local_visual_schema(local_df)
        dashboard = _build_local_auto_dashboard(local_df, dataset_id, schema)
    else:
        try:
            schema = client.get_visual_builder_schema(dataset_id)
            dashboard = client.get_dashboard(dataset_id)
            ai_payload = client.get_ai_business_insights(dataset_id)
            storyboard = client.get_executive_storyboard(dataset_id)
        except requests.RequestException:
            _warn_backend_unavailable("Dashboard Studio")
            return

    _render_auto_header(dashboard)
    left, right = st.columns([2.7, 1])
    with right:
        filters = _render_quality_and_filters(dashboard, schema, dataset_id)
    if filters and local_df is None:
        try:
            dashboard = client.get_filtered_dashboard(dataset_id, filters)
        except requests.RequestException:
            _warn_backend_unavailable("Filtered Dashboard Studio")

    with left:
        st.subheader("Executive KPI Cards")
        _render_auto_kpis(dashboard.get("kpi_cards", []))
        st.subheader("Dashboard Canvas")
        _render_auto_charts(dashboard.get("chart_specs", []))
        st.subheader("Insight Cards")
        _render_auto_insights(ai_payload, dashboard)

    _render_customize_dashboard(client, dataset_id, schema, dashboard, local_df, ai_payload, storyboard)
