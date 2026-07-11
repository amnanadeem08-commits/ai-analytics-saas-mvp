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
    LOCAL_MODE_INFO_MESSAGE,
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
from frontend.utils.kpi_helpers import (
    _format_kpi_value,
    _kpi_icon_svg,
    _kpi_id_from_label,
    _local_summary,
    _safe_trend_text,
    _sparkline_html,
    build_default_kpis,
)
from frontend.utils.local_helpers import (
    _build_filter_payload,
    _render_local_anomalies_and_distribution,
    _render_local_chart_recommendations,
    _render_local_data_quality_score,
    _render_local_executive_summary,
    _render_local_forecast_and_trend,
    _render_local_key_metrics,
    select_dataset,
)


def _statistical_metric_help(label: str) -> str:
    normalized = str(label).lower()
    if "mean" in normalized or "average" in normalized:
        return "Average of all values. Use median if you suspect outliers."
    if "median" in normalized:
        return "Middle value after sorting. More reliable than mean when outliers are present."
    if "mode" in normalized:
        return "Most frequent value. Useful for identifying the most common category or outcome."
    if "std" in normalized or "standard deviation" in normalized:
        return "How spread out values are around the mean. Higher values mean more variability."
    if "variance" in normalized:
        return "Average squared deviation from the mean. Useful as a volatility measure."
    if "p-value" in normalized or "p value" in normalized:
        return "Probability score. Values below 0.05 usually indicate a statistically significant finding."
    if "correlation" in normalized:
        return "Ranges from -1 to +1 and shows how two variables move together."
    if "skew" in normalized:
        return "Distribution lean. Positive skew means a right tail with high outliers."
    if "iqr" in normalized:
        return "Q3 minus Q1. Captures the middle 50% range and helps detect outliers."
    if "z-score" in normalized or "z score" in normalized:
        return "Shows how many standard deviations a value is from the mean."
    if "confidence" in normalized:
        return "Percent certainty. Higher confidence means the insight is more reliable."
    return "Business metric generated from the selected dataset. Review context and confidence before acting."


def _render_statistical_glossary() -> None:
    with st.expander("📖 Statistical Terms Guide", expanded=False):
        st.table(
            pd.DataFrame(
                [
                    {"Term": "Mean", "Formula": "Sum/Count", "Business Meaning": "Average value — your baseline"},
                    {"Term": "Median", "Formula": "Middle value", "Business Meaning": "Outlier-resistant center"},
                    {"Term": "Mode", "Formula": "Most frequent", "Business Meaning": "Most common category"},
                    {"Term": "Std Dev", "Formula": "√Variance", "Business Meaning": "How spread out data is"},
                    {"Term": "Variance", "Formula": "Avg squared deviation", "Business Meaning": "Volatility measure"},
                    {"Term": "T-Test", "Formula": "(x̄-μ)/(s/√n)", "Business Meaning": "Is difference statistically significant?"},
                    {"Term": "P-Value", "Formula": "Probability score", "Business Meaning": "<0.05 = significant finding"},
                    {"Term": "Correlation", "Formula": "-1 to +1", "Business Meaning": "How two variables move together"},
                    {"Term": "Skewness", "Formula": "Distribution lean", "Business Meaning": "Positive = right tail, outliers high"},
                    {"Term": "IQR", "Formula": "Q3 - Q1", "Business Meaning": "Middle 50% range, outlier detection"},
                    {"Term": "Z-Score", "Formula": "(x-μ)/σ", "Business Meaning": "How many std devs from mean"},
                    {"Term": "Confidence", "Formula": "% certainty", "Business Meaning": "How reliable is this insight"},
                ]
            )
        )


def render_dashboard(client: BackendClient) -> None:
    from frontend.components.ux_states import empty_state, error_panel, page_intro, section_header

    page_intro(
        "Executive Dashboard",
        "KPIs, trends, and quality signals for the selected dataset.",
    )
    _render_statistical_glossary()
    dataset_id = select_dataset(client)
    if not dataset_id:
        empty_state(
            "Select a dataset to open the dashboard",
            "Upload data first, then return here for KPIs and charts.",
            primary_label="Upload data",
            primary_page="Upload",
            key="dash_empty",
        )
        return

    if _is_local_dataset_id(dataset_id):
        local_df = _local_active_dataframe(dataset_id)
        if local_df is None:
            empty_state(
                "Upload a dataset first",
                "Go to Upload or Dataset Preview, then open the dashboard again.",
                primary_label="Upload data",
                primary_page="Upload",
                key="dash_local_empty",
            )
            return
        st.info(LOCAL_MODE_INFO_MESSAGE)
        summary = _local_summary(local_df)
        palette = st.session_state.get("chart_palette", ["#0078D4", "#004E8C", "#F2C811", "#10B981", "#F97316"])
        section_header("Local analysis", "Computed in-browser while the API is optional")
        _render_local_executive_dashboard(local_df, summary, palette)
        with st.expander("Dataset preview", expanded=False):
            st.dataframe(local_df.head(20), use_container_width=True)
        return

    try:
        summary = client.get_summary(dataset_id)
        preview = client.get_preview(dataset_id, rows=8)
        insights_payload = client.get_insights(dataset_id)
        schema = client.get_visual_builder_schema(dataset_id)
        filters = _build_filter_payload(schema, "dashboard")
        dashboard = (
            client.get_filtered_dashboard(dataset_id, filters)
            if filters
            else client.get_dashboard(dataset_id)
        )
    except requests.RequestException as exc:
        error_panel(
            "Dashboard could not load from the API",
            suggestion="Check Connection in the sidebar, or use a local uploaded dataset.",
            retry_key="dash_api",
        )
        with st.expander("Technical details", expanded=False):
            st.code(str(exc))
        _warn_backend_unavailable("Stats Dashboard")
        return

    storyboard_key = f"dashboard_studio_storyboard_{dataset_id}"

    def _add_dashboard_chart_to_storyboard(chart: dict) -> None:
        storyboard = st.session_state.setdefault(storyboard_key, [])
        result = add_storyboard_entry(
            storyboard,
            {
                "chart_id": chart.get("chart_id"),
                "title": chart.get("title", "Dashboard Chart"),
                "suggested_chart_type": chart.get("chart_type", "chart"),
                "business_meaning": chart.get("metadata", {}).get("statistical_explanation", ""),
                "short_ai_insight": chart.get("metadata", {}).get("subtitle", ""),
                "spec": {
                    "chart_type": chart.get("chart_type"),
                    "dimension": chart.get("columns", [None])[0],
                    "measure": chart.get("columns", [None, None])[1] if len(chart.get("columns", [])) > 1 else None,
                    "aggregation": chart.get("metadata", {}).get("aggregation", "sum"),
                    "title": chart.get("title"),
                },
            },
        )
        if result["added"]:
            st.success(f"Added {chart.get('title', 'chart')} to Storyboard.")
        else:
            st.info("This chart is already in Storyboard.")

    def _add_dashboard_kpi_to_storyboard(card: dict) -> None:
        storyboard = st.session_state.setdefault(storyboard_key, [])
        kpi_id = card.get("kpi_id") or _kpi_id_from_label(card.get("label", "Metric"))
        result = add_storyboard_entry(
            storyboard,
            {
                "chart_id": f"kpi_{kpi_id}",
                "kpi_id": kpi_id,
                "title": card.get("label", "KPI"),
                "suggested_chart_type": "kpi",
                "business_meaning": card.get("statistical_explanation", ""),
                "short_ai_insight": card.get("reason", ""),
                "spec": {"chart_type": "kpi", "title": card.get("label"), "value": card.get("value"), "kpi_id": kpi_id},
            },
        )
        if result["added"]:
            st.success(f"Added KPI {card.get('label', 'Metric')} to Storyboard.")
        else:
            st.info("This KPI is already in Storyboard.")

    def _add_dashboard_chart_to_report(chart: dict) -> None:
        try:
            response = client.register_visual(dataset_id, chart)
            st.success("Added to Reports catalog." if response.get("registered") else "Already available in Reports.")
        except requests.RequestException as exc:
            _warn_backend_unavailable("Adding chart to Reports")

    _render_dashboard_header(dashboard, summary)
    render_summary_metrics(summary)
    _render_dashboard_preview(preview.get("rows", []))
    _render_business_summary(dashboard, insights_payload)
    _render_kpi_cards(
        dashboard.get("kpi_cards", []),
        dashboard.get("theme", {}),
        on_add_to_storyboard=_add_dashboard_kpi_to_storyboard,
        key_prefix="main_dashboard",
    )

    if dashboard.get("filtered"):
        st.caption(
            f"Filtered rows: {dashboard.get('filtered_row_count', 0):,} of "
            f"{dashboard.get('original_row_count', 0):,}"
        )

    _render_data_quality_panel(summary, dashboard)

    with st.expander("Column profile", expanded=False):
        col_types = summary.get("column_types", {})
        if col_types:
            col_type_rows = []
            for category, columns in col_types.items():
                for column in columns:
                    col_type_rows.append({"column": column, "detected_type": category.replace("_", " ")})
            if col_type_rows:
                st.dataframe(pd.DataFrame(col_type_rows), use_container_width=True, hide_index=True)
        numeric_summary = summary.get("numeric_summary", {})
        if numeric_summary:
            st.dataframe(pd.DataFrame(numeric_summary).T, use_container_width=True)
        missing_values = summary.get("missing_values_by_column", {})
        if missing_values:
            missing_df = pd.DataFrame(
                [{"column": key, "missing_values": value} for key, value in missing_values.items()]
            )
            st.dataframe(missing_df, use_container_width=True)

    st.subheader("Visual Analysis")
    render_plotly_chart_specs(
        dashboard,
        on_add_to_storyboard=_add_dashboard_chart_to_storyboard,
        on_add_to_report=_add_dashboard_chart_to_report,
    )

    left, right = st.columns(2)
    with left:
        _render_suggested_questions(dashboard)
    with right:
        with st.container(border=True):
            st.markdown("#### Business Insights")
            # Render polished executive summary instead of plain text
            executive_summary = insights_payload.get("executive_summary") or {}
            st.markdown(f"**Insight:** {executive_summary.get('insight', 'Not available')}")
            st.caption(f"Reason: {executive_summary.get('reason', 'Not available')}")
            st.info(f"Recommended action: {executive_summary.get('action', 'Not available')}")
            # Render rule-based insights as compact cards
            for insight in insights_payload.get("insights", [])[:4]:
                render_insight(insight)
def _render_kpi_cards(
    cards: list[dict],
    theme: dict | None = None,
    *,
    on_add_to_storyboard=None,
    on_add_to_report=None,
    key_prefix: str = "kpi_cards",
) -> None:
    if not cards:
        return
    theme = theme or {}
    surface = theme.get("surface", "var(--ui-surface)")
    border = theme.get("border", "var(--surface-border)")
    muted = theme.get("muted_text", "var(--text-muted)")
    text = theme.get("text", "var(--text-color)")
    shadow = "0 10px 24px rgba(15, 23, 42, 0.06)" if theme.get("mode") != "dark" else "0 10px 24px rgba(0, 0, 0, 0.28)"
    st.markdown(
        f"""
        <style>
        :root {{
            --kpi-surface: {surface};
            --kpi-border: {border};
            --kpi-muted: {muted};
            --kpi-text: {text};
            --kpi-shadow: {shadow};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <style>
        .kpi-card {
            border: 1px solid var(--kpi-border);
            border-radius: 10px;
            padding: 14px 16px 16px;
            min-height: 198px;
            background: var(--kpi-surface);
            box-shadow: var(--kpi-shadow);
            display: flex;
            flex-direction: column;
            gap: 8px;
            overflow: visible;
            height: auto;
            overflow-wrap: anywhere;
            word-break: normal;
        }
        .kpi-topline {
            display: flex;
            align-items: center;
            justify-content: space-between;
            min-width: 0;
            gap: 8px;
        }
        .kpi-icon {
            width: 22px;
            height: 22px;
        }
        .kpi-label {
            font-size: 0.78rem;
            color: var(--kpi-muted);
            text-transform: uppercase;
            letter-spacing: 0;
            font-weight: 700;
        }
        .kpi-value {
            font-size: 1.55rem;
            color: var(--kpi-text);
            font-weight: 800;
            margin-top: 6px;
        }
        .kpi-delta {
            font-size: 0.86rem;
            margin-top: 8px;
            font-weight: 700;
        }
        .kpi-context {
            font-size: 0.78rem;
            color: var(--kpi-muted);
            margin-top: 8px;
            line-height: 1.25;
        }
        .sparkline {
            display: flex;
            align-items: flex-end;
            gap: 3px;
            height: 38px;
            margin-top: 8px;
        }
        .spark-bar {
            display: inline-block;
            width: 8px;
            border-radius: 3px 3px 0 0;
            background: currentColor;
            opacity: 0.72;
        }
        .kpi-decision {
            font-size: 0.72rem;
            color: var(--kpi-muted);
            margin-top: 8px;
            line-height: 1.25;
        }
        .kpi-meta {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 8px;
            font-size: 0.7rem;
            color: var(--kpi-muted);
        }
        .risk-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 5px;
            background: currentColor;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    for offset in range(0, min(len(cards), 8), 4):
        cols = st.columns(4)
        for card_index, (col, card) in enumerate(zip(cols, cards[offset : offset + 4]), start=offset):
            value = card.get("formatted_value", card.get("value", ""))
            if not card.get("formatted_value") and card.get("format") == "percent" and isinstance(value, (int, float)):
                value = f"{value}%"
            delta = card.get("delta_percentage")
            trend_arrow = _safe_trend_text(str(card.get("trend_arrow", "->")))
            delta_text = "" if delta is None else f"{trend_arrow} {delta}%".strip()
            color = card.get("status_color") or muted
            context = card.get("business_context") or card.get("description") or ""
            sparkline = _sparkline_html(card.get("sparkline", []))
            reason = card.get("reason", "")
            action = card.get("recommended_action", "")
            impact = card.get("expected_impact", "")
            icon = _kpi_icon_svg(card.get("icon", "metric"))
            risk = card.get("risk_indicator", "normal")
            confidence = card.get("confidence_score", 0.75)
            tooltip = _statistical_metric_help(card.get("label", "Metric"))
            col.markdown(
                f"""
                <div class="kpi-card" title="{html.escape(tooltip)}">
                    <div class="kpi-topline">
                        <div class="kpi-label">{html.escape(str(card.get('label', 'Metric')))}</div>
                        <div style="color: {color};">{icon}</div>
                    </div>
                    <div class="kpi-value">{html.escape(str(value))}</div>
                    {f'<div class="kpi-delta" style="color: {color};">{html.escape(delta_text)}</div>' if delta_text else ''}
                    <div style="color: {color};">{sparkline}</div>
                    <div class="kpi-meta">
                        <span style="color: {color};"><span class="risk-dot"></span>{risk.title()}</span>
                        <span>Confidence {round(float(confidence) * 100)}%</span>
                    </div>
                    <div class="kpi-context">{html.escape(str(context))}</div>
                    <div class="kpi-decision"><b>Reason:</b> {html.escape(str(reason))}</div>
                    <div class="kpi-decision"><b>Action:</b> {html.escape(str(action))}</div>
                    <div class="kpi-decision"><b>Impact:</b> {html.escape(str(impact))}</div>
                    <div class="kpi-decision">{html.escape(str(card.get("statistical_explanation", "")))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            kpi_id = card.get("kpi_id") or _kpi_id_from_label(card.get("label", "Metric"))
            key_suffix = f"{key_prefix}_{kpi_id}_{card_index}"
            action_cols = col.columns([1, 1])
            if action_cols[0].button("Storyboard", key=f"{key_suffix}_storyboard", use_container_width=True):
                if callable(on_add_to_storyboard):
                    on_add_to_storyboard(card)
            if action_cols[1].button("Report", key=f"{key_suffix}_report", use_container_width=True):
                if callable(on_add_to_report):
                    on_add_to_report(card)
def _render_dashboard_header(dashboard: dict, summary: dict) -> None:
    branding = dashboard.get("branding", {})
    theme = dashboard.get("theme", {})
    title = html.escape(branding.get("report_title", "Executive Analytics Dashboard"))
    company = html.escape(branding.get("company_name", "AI Analytics"))
    primary = theme.get("primary", "#118DFF")
    muted = theme.get("muted_text", "#64748B")
    rows = dashboard.get("filtered_row_count", summary.get("row_count", 0))
    cols = summary.get("column_count", dashboard.get("overview", {}).get("column_count", 0))
    charts = len(dashboard.get("chart_specs", []))
    st.markdown(
        f"""
        <div style="
            border: 1px solid rgba(148,163,184,0.26);
            border-radius: 10px;
            padding: 18px 20px;
            margin-bottom: 16px;
            background: linear-gradient(135deg, rgba(17,141,255,0.10), rgba(255,255,255,0.02));
        ">
            <div style="font-size:0.76rem;font-weight:800;color:{primary};text-transform:uppercase;">{company}</div>
            <div style="font-size:1.55rem;font-weight:850;color:var(--text-color);margin-top:2px;">{title}</div>
            <div style="font-size:0.88rem;color:{muted};margin-top:6px;">
                {rows:,} active records · {cols:,} columns · {charts:,} generated visuals
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
def _render_data_quality_panel(summary: dict, dashboard: dict) -> None:
    missing = int(summary.get("total_missing_values", 0) or 0)
    duplicates = int(summary.get("duplicate_rows", 0) or 0)
    row_count = int(summary.get("row_count", 0) or 0)
    column_count = int(summary.get("column_count", 0) or 0)
    total_cells = max(row_count * column_count, 1)
    completeness = round((1 - missing / total_cells) * 100, 2)
    grade = "A" if completeness >= 98 and duplicates == 0 else "B" if completeness >= 92 else "C" if completeness >= 80 else "D"
    status = "Production-ready" if grade == "A" else "Review recommended"
    analysis_guardrails = dashboard.get("analysis_guardrails", {})
    with st.container(border=True):
        st.markdown("#### Data Quality")
        cols = st.columns([1, 1, 1, 2])
        cols[0].metric("Grade", grade)
        cols[1].metric("Completeness", f"{completeness}%")
        cols[2].metric("Duplicates", f"{duplicates:,}")
        cols[3].write(f"**Status:** {status}")
        if missing:
            cols[3].caption(f"{missing:,} missing cells may affect charts and KPI confidence.")
        else:
            cols[3].caption("No missing cells detected in the current dataset view.")
        invalid = analysis_guardrails.get("invalid_methods", [])
        if invalid:
            with st.expander("Analysis guardrails"):
                for item in invalid:
                    st.write(f"- {item}")
def _render_business_summary(dashboard: dict, insights_payload: dict | None = None) -> None:
    executive = (insights_payload or {}).get("executive_summary") or {}
    domain = dashboard.get("domain_intelligence", {}).get("detection", {})
    with st.container(border=True):
        st.markdown("#### Executive Summary")
        if domain:
            st.caption(f"Detected domain: {domain.get('domain', 'Generic Analytics')} · Confidence: {domain.get('confidence', 'low').title()}")
        if not executive:
            st.info("Executive summary is not available yet. Upload a dataset with measurable fields to generate one.")
            return
        st.markdown(f"**Insight:** {executive.get('insight', '')}")
        st.write(f"**Why it matters:** {executive.get('reason', '')}")
        st.write(f"**Recommended action:** {executive.get('action', '')}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Data confidence", str(executive.get("data_confidence", executive.get("confidence", "low"))).title())
        c2.metric("Business confidence", str(executive.get("business_confidence", "medium")).title())
        c3.metric("Business relevance", str(executive.get("business_relevance", "medium")).title())
        evidence = executive.get("evidence", [])
        if evidence:
            with st.expander("Evidence"):
                for item in evidence[:8]:
                    st.write(f"- {item}")
def _render_suggested_questions(dashboard: dict) -> None:
    backend_questions = dashboard.get("suggested_questions") or []
    if backend_questions:
        questions = backend_questions
    else:
        questions = []
        metrics = dashboard.get("business_metrics", {})
        metric = metrics.get("primary_metric")
        segment = metrics.get("primary_segment")
        if metric and segment:
            questions.extend(
                [
                    f"Which {segment} has the strongest {metric} performance?",
                    f"Why is {metric} different across {segment}?",
                    f"What should management do to improve {metric}?",
                ]
            )
        elif metric:
            questions.extend(
                [
                    f"What is the trend in {metric}?",
                    f"Which columns explain changes in {metric}?",
                ]
            )
        questions.append("What risks should leadership watch in this dataset?")
    with st.container(border=True):
        st.markdown("#### Suggested Questions")
        for question in questions[:5]:
            st.write(f"- {question}")
def _render_dashboard_preview(preview_rows: list[dict]) -> None:
    with st.expander("Dataset preview", expanded=False):
        if preview_rows:
            st.dataframe(pd.DataFrame(preview_rows), use_container_width=True)
        else:
            st.info("No preview rows are available for this dataset.")
def _render_local_executive_dashboard(df: pd.DataFrame, summary: dict, palette: list[str]) -> None:
    render_summary_metrics(summary)
    _render_local_data_quality_score(df, summary)
    _render_local_key_metrics(df)
    _render_local_chart_recommendations(df, palette)
    _render_local_forecast_and_trend(df)
    _render_local_anomalies_and_distribution(df)
    _render_local_executive_summary(df)
