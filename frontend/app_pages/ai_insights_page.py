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
from backend.analytics.insights import (
    build_ai_business_insights_from_data_insights,
    build_data_insights,
)
from frontend.components.ai_business_insight_cards import render_ai_business_insight_cards
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
from frontend.app_pages.dashboard_page import (
    _render_business_summary,
    _render_dashboard_header,
    _render_data_quality_panel,
    _render_kpi_cards,
)
from frontend.app_pages.dataset_page import _local_active_dataframe
from frontend.utils.kpi_helpers import _local_column_groups, _local_summary, build_data_anomaly_report
from frontend.utils.local_helpers import (
    _local_anomaly_rows,
    _local_default_figures,
    _render_local_anomalies_and_distribution,
    _render_local_chart_recommendations,
    _render_local_data_quality_score,
    _render_local_executive_summary,
    _render_local_forecast_and_trend,
    _render_local_key_metrics,
    select_dataset,
)


def _render_executive_item(item: object) -> None:
    if isinstance(item, dict):
        title = item.get("risk") or item.get("opportunity") or item.get("recommendation") or item.get("action") or item.get("title") or "Executive signal"
        body_parts = [
            item.get("why_it_matters"),
            item.get("why"),
            item.get("reason"),
            item.get("expected_impact"),
        ]
        body = " ".join(str(part) for part in body_parts if part)
        with st.container(border=True):
            st.markdown(f"**{title}**")
            if body:
                st.write(body)
            evidence = item.get("evidence")
            if evidence:
                st.caption(f"Evidence: {evidence}")
        return
    with st.container(border=True):
        st.write(str(item))


def _render_insight_category_expanders(insights: list[dict], executive: dict) -> None:
    categories: list[tuple[str, list[object]]] = [
        (":material/warning: Critical Risks (requires immediate attention)", []),
        (":material/visibility: Watch List (monitor these trends)", []),
        (":material/trending_up: Opportunities (act on these)", []),
        (":material/query_stats: Statistical Anomalies (unusual patterns)", []),
        (":material/lightbulb: Business Recommendations (actionable next steps)", []),
    ]
    critical, watch, opportunities, anomalies, recommendations = [items for _, items in categories]

    critical.extend(executive.get("risks", []) or [])
    opportunities.extend(executive.get("opportunities", []) or [])
    recommendations.extend(executive.get("recommendations", []) or [])
    recommendations.extend(executive.get("action_plan", []) or [])

    for insight in insights:
        insight_type = str(insight.get("type", "")).lower()
        severity = str(insight.get("severity", "")).lower()
        if insight_type in {"outlier"}:
            anomalies.append(insight)
        elif insight_type in {"correlation", "trend"}:
            watch.append(insight)
        elif insight_type in {"performance", "metric"} or severity == "success":
            opportunities.append(insight)
        elif severity in {"warning", "error", "critical"}:
            critical.append(insight)
        else:
            watch.append(insight)

    st.markdown("#### Executive Insight Categories")
    for label, items in categories:
        with st.container(border=True):
            st.markdown(f"##### {label} ({len(items)})")
            if not items:
                st.caption("No items in this category for the current dataset.")
                continue
            for item in items:
                if isinstance(item, dict) and "message" in item:
                    render_insight(item)
                else:
                    _render_executive_item(item)

def render_ai_insights(client: BackendClient) -> None:
    primary = st.session_state.get("primary_color", "#118DFF")
    secondary = st.session_state.get("secondary_color", "#12239E")
    accent = st.session_state.get("branding", DEFAULT_BRANDING).get("accent_color", "#E66C37")
    palette = st.session_state.get("chart_palette", [primary, secondary, accent, "#10B981", "#F59E0B"])
    _ai_dashboard_css(primary, secondary, accent)

    st.markdown(
        """
        <div class="ai-hero">
            <h1>Ask Your Data</h1>
            <p>Ask questions in plain English. The assistant answers using your uploaded data and generated analysis.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    dataset_id = st.session_state.get("active_dataset_id") or st.session_state.get("selected_dataset_id")
    if not dataset_id:
        st.info("Upload a dataset first from Dataset Preview.")
        return
    if _is_local_dataset_id(dataset_id):
        local_df = _local_active_dataframe(dataset_id)
        if local_df is None:
            st.info("Upload a dataset first from Dataset Preview.")
            return
        st.info(LOCAL_MODE_INFO_MESSAGE)
        data_insights_payload = build_data_insights(local_df)
        render_ai_business_insight_cards(build_ai_business_insights_from_data_insights(data_insights_payload))
        summary = _local_summary(local_df)
        numeric_cols = local_df.select_dtypes(include="number").columns.tolist()
        top_cards = st.columns(4)
        with top_cards[0]:
            _html_card("Rows", f"{summary['row_count']:,}", "Evidence available for answers.", palette[0])
        with top_cards[1]:
            _html_card("Columns", f"{summary['column_count']:,}", "Fields the assistant can reference.", palette[1])
        with top_cards[2]:
            _html_card("Missing Values", f"{summary['total_missing_values']:,}", "Quality issues that may lower confidence.", palette[2])
        with top_cards[3]:
            _html_card("Duplicates", f"{summary['duplicate_rows']:,}", "Repeated rows can inflate answers.", palette[3 % len(palette)])
        st.subheader("Example Questions")
        examples = ["What are the biggest data quality risks?", "Which segment appears most common?", "Which numeric measure should I monitor first?"]
        for question in examples:
            with st.container(border=True):
                st.markdown(f"#### Question: {question}")
                if numeric_cols:
                    metric = numeric_cols[0]
                    metric_series = pd.to_numeric(local_df[metric], errors="coerce")
                    st.write(f"**Answer:** {metric} is a useful first measure to review. Its average is {metric_series.mean():,.2f} across supported records.")
                    st.write(f"**Evidence from dataset:** {metric_series.notna().sum():,} non-empty values in {metric}.")
                    st.write("**Confidence:** Medium")
                    st.write("**Recommended next step:** Compare this measure by the largest category segment.")
                else:
                    st.write("The uploaded dataset does not provide enough evidence to answer this confidently.")
        return

    try:
        insight_payload = client.get_insights(dataset_id)
        ai_business_payload = client.get_ai_business_insights(dataset_id)
        domain_payload = client.get_domain_intelligence(dataset_id)
        dashboard_payload = client.get_dashboard(dataset_id)
        insights = insight_payload.get("insights", [])
    except requests.RequestException as exc:
        _warn_backend_unavailable("Insights")
        return

    render_ai_business_insight_cards(ai_business_payload)

    detection = domain_payload.get("detection", {})
    summary = dashboard_payload.get("summary", {})
    root_causes = domain_payload.get("root_causes", [])
    executive = insight_payload.get("executive_summary") or {}
    evidence = executive.get("evidence", [])

    top = st.columns(4)
    with top[0]:
        _html_card("Detected Pattern", detection.get("domain", "Generic Analytics"), detection.get("business_context", "Dataset-level analytical decision support."), palette[0])
    with top[1]:
        _html_card("Confidence", str(detection.get("confidence", "low")).title(), f"Signals: {', '.join(detection.get('signals', [])[:4]) or 'schema + statistics'}", palette[1])
    with top[2]:
        _html_card("Insight Cards", len(insights), "Rule-based findings generated from uploaded data.", palette[2])
    with top[3]:
        _html_card("Evidence Blocks", len(evidence) + len(root_causes), "Executive evidence plus root-cause candidates.", palette[3 % len(palette)])

    tab_overview, tab_evidence, tab_ask, tab_raw = st.tabs(["Insight Overview", "Evidence Board", "Ask Your Data", "Technical Details"])

    with tab_overview:
        # Polished AI Insight panel — no raw JSON by default
        data_quality = executive.get("metrics_snapshot", {}).get("data_quality_score") or dashboard_payload.get("data_quality_score")
        render_business_insights_overview(
            executive=executive,
            data_quality=data_quality,
            summary=summary,
            raw_payload=insight_payload if st.session_state.get("_show_raw_insight", False) else None,
        )

        _render_insight_category_expanders(insights, executive)

        # Color-Coded Insight Stream (rule-based insights)
        if insights:
            st.markdown("#### Rule-Based Insights")
            for insight in insights:
                render_insight(insight)
        else:
            st.info("No rule-based insights were generated for this dataset.")

        domain_mode = domain_payload.get("domain_mode", {})
        if domain_mode.get("available"):
            st.subheader("Adaptive Domain Mode")
            mode_cols = st.columns(4)
            for idx, key in enumerate(["what_happened", "why_it_happened", "what_to_do", "expected_impact"]):
                with mode_cols[idx]:
                    _html_card(key.replace("_", " ").title(), domain_mode.get(key, "Not available"), "", palette[idx % len(palette)])

    with tab_evidence:
        st.subheader("Evidence Board")
        st.caption("Evidence is displayed from metrics, tables, and generated analysis tied to the uploaded dataset.")
        _evidence_pills(evidence, "Executive summary did not return explicit evidence bullets.")
        if root_causes:
            rows = []
            for cause in root_causes:
                rows.append({"metric": cause.get("metric"), "driver_count": len(cause.get("potential_drivers", [])), "evidence": cause.get("supporting_evidence"), "action": cause.get("recommended_action")})
            _numeric_evidence_chart("Root-Cause Evidence Density", rows, "metric", "driver_count", palette)
            st.dataframe(safe_table(rows), use_container_width=True, hide_index=True)
            for cause in root_causes:
                with st.expander(f"Evidence chain: {cause.get('metric', 'Metric')}", expanded=False):
                    st.write(cause.get("supporting_evidence", ""))
                    st.write(cause.get("recommended_action", ""))
                    if cause.get("potential_drivers"):
                        st.dataframe(safe_table(cause["potential_drivers"]), use_container_width=True, hide_index=True)
        else:
            st.info("No root-cause candidates were returned for this dataset. Try a dataset with numeric measures and segment/category columns.")

    with tab_ask:
        st.subheader("Ask Your Data")
        question = st.text_input("Ask about this dataset", placeholder="Example: What segment, category, or field appears most important?")
        if st.button("Ask", disabled=not question.strip(), type="primary"):
            try:
                answer = client.ask_question(dataset_id, question)
                st.markdown(f"<div class='rag-box'><b>Answer</b><br>{html.escape(str(answer.get('answer', '')))}</div>", unsafe_allow_html=True)
                support = answer.get("supporting_data", {})
                analyst = answer.get("analyst", {})
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("##### Supporting Data")
                    if isinstance(support, dict):
                        for key, value in support.items():
                            if isinstance(value, list) and value and isinstance(value[0], dict):
                                st.write(f"**{key.replace('_', ' ').title()}**")
                                st.dataframe(safe_table(value), use_container_width=True, hide_index=True)
                            else:
                                st.write(f"**{key.replace('_', ' ').title()}**: {value}")
                    else:
                        st.write(support)
                with c2:
                    st.markdown("##### How confident is this?")
                    if isinstance(analyst, dict) and analyst:
                        analyst_rows = [{"metric": str(key).replace("_", " "), "value": value} for key, value in analyst.items()]
                        st.dataframe(pd.DataFrame(analyst_rows), use_container_width=True, hide_index=True)
                    else:
                        st.write(analyst)
            except requests.RequestException as exc:
                _warn_backend_unavailable("Question answering")

    with tab_raw:
        st.subheader("Technical Details")
        st.caption("Validation details shown in business-friendly format.")
        with st.expander("Domain intelligence payload", expanded=False):
            detection = (domain_payload or {}).get("detection") or {}
            rows = [
                {"field": "Detected Domain", "value": detection.get("domain", "Not available")},
                {"field": "Confidence", "value": detection.get("confidence", "Not available")},
                {"field": "Confidence Score", "value": detection.get("confidence_score", "Not available")},
                {"field": "Signals", "value": ", ".join(detection.get("signals", []) or [])},
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        with st.expander("Dashboard payload summary", expanded=False):
            rows = [
                {"field": "Dataset ID", "value": dashboard_payload.get("dataset_id")},
                {"field": "Suggested Questions", "value": len(dashboard_payload.get("suggested_questions", []) or [])},
                {"field": "KPI Cards", "value": len(dashboard_payload.get("kpi_cards", []) or [])},
                {"field": "Charts", "value": len(dashboard_payload.get("chart_specs", []) or [])},
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
def render_data_visual_analysis(client: BackendClient) -> None:
    st.header("Data Visual Analysis")
    st.caption("Statistical exploration, data quality, distributions, correlations, and cleaning guidance.")
    dataset_id = select_dataset(client, key="data_visual_analysis_dataset_select")
    if not dataset_id:
        return

    if is_local_dataset_id(dataset_id):
        df = _local_active_dataframe(dataset_id)
        if df is None:
            st.info("Upload a dataset first from Dataset Preview.")
            return
        summary = _local_summary(df)
        render_summary_metrics(summary)
        _render_local_data_quality_score(df, summary)
        left, right = st.columns(2)
        with left.container(border=True):
            st.markdown("#### Missing Values")
            missing = df.isna().sum().sort_values(ascending=False)
            missing = missing[missing > 0].head(15)
            if missing.empty:
                st.success("No missing values detected.")
            else:
                st.dataframe(missing.rename("Missing values").reset_index().rename(columns={"index": "Column"}), use_container_width=True, hide_index=True)
        with right.container(border=True):
            st.markdown("#### Duplicate Rows")
            st.metric("Duplicates", f"{int(df.duplicated().sum()):,}")
            st.caption("Duplicates can inflate count, sum, and frequency-based visuals.")
        with st.expander("Column schema", expanded=True):
            schema = pd.DataFrame([{"Column": col, "Type": str(dtype), "Missing": int(df[col].isna().sum()), "Unique": int(df[col].nunique(dropna=True))} for col, dtype in df.dtypes.items()])
            st.dataframe(schema, use_container_width=True, hide_index=True)
        palette = st.session_state.get("chart_palette", ["#0078D4", "#004E8C", "#F2C811", "#10B981"])
        figures = _local_default_figures(df, palette)
        st.subheader("Statistical Visuals")
        for offset in range(0, len(figures), 2):
            cols = st.columns(2)
            for col, item in zip(cols, figures[offset: offset + 2]):
                with col.container(border=True):
                    st.markdown(f"#### {item['title']}")
                    st.plotly_chart(item["figure"], use_container_width=True)
                    kind = str(item.get("kind", "visual")).lower()
                    if "distribution" in kind:
                        st.caption("Shows how values are spread. Skew or extreme bars can affect averages and should be checked before business interpretation.")
                    elif "category" in kind:
                        st.caption("Shows frequency by category. A dominant category may indicate concentration or an imbalanced sample.")
                    elif "correlation" in kind:
                        st.caption("Shows association between numeric fields. Correlation does not prove causality.")
                    else:
                        st.caption("Shows a statistical pattern from the uploaded data. Interpret alongside sample size, missing values, and outlier warnings.")
        if st.session_state.get("show_anomaly_panel", True):
            _render_local_anomalies_and_distribution(df)
        if st.session_state.get("show_statistical_explanations", True):
            st.subheader("Cleaning Suggestions")
            suggestions = _local_anomaly_rows(df) or ["Dataset is ready for basic analysis. Review column types before executive reporting."]
            for item in suggestions:
                st.write(f"- {item}")
        return

    try:
        summary = client.get_summary(dataset_id)
        dashboard = client.get_dashboard(dataset_id)
    except requests.RequestException:
        _warn_backend_unavailable("Data Visual Analysis")
        return
    render_summary_metrics(summary)
    _render_data_quality_panel(summary, dashboard)
    with st.expander("Column schema", expanded=True):
        col_types = summary.get("column_types", {})
        rows = []
        for kind, columns in (col_types or {}).items():
            for column in columns:
                rows.append({"column": column, "detected_type": str(kind).replace("_", " ")})
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.subheader("Statistical Visuals")
    render_plotly_chart_specs(dashboard)
def render_business_visual_analysis(client: BackendClient) -> None:
    st.header("Business Visual Analysis")
    st.caption("Executive KPIs, segment performance, risk, opportunity, and board-ready recommendations.")
    dataset_id = select_dataset(client, key="business_visual_analysis_dataset_select")
    if not dataset_id:
        return

    if is_local_dataset_id(dataset_id):
        df = _local_active_dataframe(dataset_id)
        if df is None:
            st.info("Upload a dataset first from Dataset Preview.")
            return
        summary = _local_summary(df)
        palette = st.session_state.get("chart_palette", ["#0078D4", "#004E8C", "#F2C811", "#10B981"])
        _render_dashboard_header({"branding": st.session_state.get("branding", DEFAULT_BRANDING), "theme": {"primary": palette[0], "muted_text": "#64748B"}, "chart_specs": []}, summary)
        _render_local_key_metrics(df)
        _render_local_chart_recommendations(df, palette)
        _render_local_forecast_and_trend(df)
        numeric, categorical, datetime_cols = _local_column_groups(df)
        top_segment = "No segment field detected"
        if categorical:
            counts = df[categorical[0]].astype("string").fillna("Unknown").value_counts()
            if not counts.empty:
                top_segment = f"{categorical[0]} = {counts.index[0]} ({int(counts.iloc[0]):,} records)"
        left, right = st.columns(2)
        with left.container(border=True):
            st.markdown("#### What / When / Why / Who / What Now")
            st.write(f"**What happened:** {len(df):,} records are available for executive review, with {len(numeric):,} measurable fields.")
            st.write(f"**When it happened:** {('Trend review is available through ' + datetime_cols[0]) if datetime_cols else 'No reliable date field was detected, so timing is not shown.'}")
            st.write("**Why it may have happened:** Segment comparisons can indicate associations, but this view avoids unsupported causal claims.")
            st.write(f"**Who or which segment is affected:** {top_segment}.")
            st.write("**What now:** Promote one KPI, one segment comparison, and the anomaly summary into the storyboard for leadership review.")
        with right.container(border=True):
            st.markdown("#### Risk, Opportunity, Expected Impact")
            anomalies = [item['explanation'] for item in build_data_anomaly_report(df)]
            st.write(f"**Risk:** {(anomalies[0] if anomalies else 'No major quality risk detected in local analysis.')}")
            st.write("**Opportunity:** Use segment performance and trend visuals to prioritize management actions.")
            st.write("**Expected impact:** Faster executive review with fewer blank export sections and clearer owners for follow-up.")
        if st.session_state.get("show_business_recommendations", True):
            _render_local_executive_summary(df)
        return

    try:
        summary = client.get_summary(dataset_id)
        dashboard = client.get_dashboard(dataset_id)
        insights_payload = client.get_insights(dataset_id)
    except requests.RequestException:
        _warn_backend_unavailable("Business Visual Analysis")
        return
    _render_dashboard_header(dashboard, summary)
    _render_business_summary(dashboard, insights_payload)
    _render_kpi_cards(dashboard.get("kpi_cards", []), dashboard.get("theme", {}), key_prefix="business_visual")
    render_plotly_chart_specs(dashboard)
def _html_card(title: str, value: str | int | float, caption: str = "", color: str = "var(--brand-primary)") -> None:
    st.markdown(
        f"""
        <div class="ai-card" style="border-top: 5px solid {color};">
            <div class="ai-card-title">{html.escape(str(title))}</div>
            <div class="ai-card-value">{html.escape(str(value))}</div>
            <div class="ai-card-caption">{html.escape(str(caption))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
def _evidence_pills(items: list[str], empty_text: str = "No explicit evidence returned yet.") -> None:
    if not items:
        st.caption(empty_text)
        return
    st.markdown("".join(f'<span class="evidence-pill">{html.escape(str(item))}</span>' for item in items[:12]), unsafe_allow_html=True)
def _numeric_evidence_chart(title: str, rows: list[dict], label_key: str, value_key: str, palette: list[str]) -> None:
    cleaned = [row for row in rows if isinstance(row, dict) and row.get(label_key) is not None and isinstance(row.get(value_key), (int, float))]
    if not cleaned:
        return
    fig = go.Figure(
        data=[go.Bar(
            x=[str(row[label_key]) for row in cleaned[:8]],
            y=[row[value_key] for row in cleaned[:8]],
            marker_color=[palette[i % len(palette)] for i, _ in enumerate(cleaned[:8])],
        )]
    )
    fig.update_layout(title=title, height=280, margin=dict(l=10, r=10, t=45, b=10), template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)
