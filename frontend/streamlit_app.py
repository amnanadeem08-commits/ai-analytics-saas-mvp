from __future__ import annotations

import html
import json
from urllib.parse import urlencode

import pandas as pd
import plotly.graph_objects as go
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
from frontend.components.upload_component import render_upload


st.set_page_config(page_title="AI Analytics SaaS MVP", layout="wide")


@st.cache_resource
def get_client(base_url: str) -> BackendClient:
    return BackendClient(base_url=base_url)


def safe_table(rows: list[dict]) -> pd.DataFrame:
    """Normalize nested API values so Streamlit/PyArrow can render them."""
    normalized_rows = []
    for row in rows:
        normalized = {}
        for key, value in row.items():
            if isinstance(value, (dict, list)):
                normalized[key] = json.dumps(value, ensure_ascii=False)
            else:
                normalized[key] = value
        normalized_rows.append(normalized)
    return pd.DataFrame(normalized_rows)


def render_backend_status(client: BackendClient) -> None:
    try:
        health = client.health()
        st.sidebar.success(f"Backend connected: {health.get('version', '')}")
    except requests.RequestException:
        st.sidebar.error("Backend not reachable. Start FastAPI first.")


def render_theme_selector(client: BackendClient) -> None:
    try:
        payload = client.list_themes()
    except requests.RequestException:
        return

    themes = payload.get("themes", [])
    if not themes:
        return
    labels = {theme["display_name"]: theme["name"] for theme in themes}
    active_name = payload.get("active_theme")
    active_label = next((label for label, name in labels.items() if name == active_name), list(labels)[0])
    selected = st.sidebar.selectbox(
        "Theme",
        list(labels),
        index=list(labels).index(active_label),
    )
    selected_name = labels[selected]
    if selected_name != active_name:
        try:
            client.set_active_theme(selected_name)
            st.cache_data.clear()
            st.rerun()
        except requests.RequestException as exc:
            st.sidebar.error(f"Could not switch theme: {exc}")


def get_active_branding(client: BackendClient) -> dict:
    try:
        return client.get_branding()
    except requests.RequestException:
        return {
            "company_name": "AI Analytics",
            "report_title": "Executive Decision Intelligence Report",
            "logo_url": "",
            "primary_color": "#118DFF",
            "secondary_color": "#12239E",
            "accent_color": "#E66C37",
            "theme_name": "power_bi_professional",
        }


def render_branding_editor(client: BackendClient, branding: dict) -> None:
    st.sidebar.divider()
    with st.sidebar.expander("Branding"):
        logo_url = branding.get("logo_url")
        if logo_url:
            st.image(f"{client.base_url}{logo_url}", width=120)

        company_name = st.text_input("Company name", value=branding.get("company_name", "AI Analytics"))
        report_title = st.text_input(
            "Report title",
            value=branding.get("report_title", "Executive Decision Intelligence Report"),
        )
        primary_color = st.color_picker("Primary", value=branding.get("primary_color", "#118DFF"))
        secondary_color = st.color_picker("Secondary", value=branding.get("secondary_color", "#12239E"))
        accent_color = st.color_picker("Accent", value=branding.get("accent_color", "#E66C37"))
        logo_file = st.file_uploader("Logo", type=["png", "jpg", "jpeg", "webp", "svg"])

        col1, col2 = st.columns(2)
        if col1.button("Save", width="stretch"):
            try:
                client.update_branding(
                    {
                        "company_name": company_name,
                        "report_title": report_title,
                        "primary_color": primary_color,
                        "secondary_color": secondary_color,
                        "accent_color": accent_color,
                    }
                )
                if logo_file is not None:
                    client.upload_logo(logo_file)
                st.rerun()
            except requests.RequestException as exc:
                st.error(f"Could not save branding: {exc}")
        if col2.button("Reset", width="stretch"):
            try:
                client.update_branding(
                    {
                        "company_name": "AI Analytics",
                        "report_title": "Executive Decision Intelligence Report",
                        "logo_url": "",
                        "primary_color": "#118DFF",
                        "secondary_color": "#12239E",
                        "accent_color": "#E66C37",
                        "theme_name": "power_bi_professional",
                    }
                )
                st.rerun()
            except requests.RequestException as exc:
                st.error(f"Could not reset branding: {exc}")


def get_dataset_options(client: BackendClient) -> list[dict]:
    try:
        return client.list_datasets()
    except requests.RequestException:
        return []


def select_dataset(client: BackendClient) -> str | None:
    datasets = get_dataset_options(client)
    if not datasets:
        st.info("No datasets found. Upload a CSV first.")
        return None

    labels = {
        f"{item['original_filename']} — {item['dataset_id']}": item["dataset_id"]
        for item in datasets
    }

    default_label = None
    selected_id = st.session_state.get("selected_dataset_id")
    for label, dataset_id in labels.items():
        if dataset_id == selected_id:
            default_label = label
            break

    label_list = list(labels.keys())
    index = label_list.index(default_label) if default_label in label_list else 0
    selected_label = st.selectbox("Select dataset", label_list, index=index)
    dataset_id = labels[selected_label]
    st.session_state["selected_dataset_id"] = dataset_id
    return dataset_id


def render_dataset_overview(client: BackendClient) -> None:
    st.header("Dataset Preview")
    dataset_id = select_dataset(client)
    if not dataset_id:
        return

    rows = st.slider("Preview rows", min_value=5, max_value=100, value=10, step=5)
    try:
        overview = client.get_overview(dataset_id)
        preview = client.get_preview(dataset_id, rows=rows)
        summary_cols = st.columns(4)
        summary_cols[0].metric("Rows", f"{overview.get('row_count', 0):,}")
        summary_cols[1].metric("Columns", f"{overview.get('column_count', 0):,}")
        summary_cols[2].metric(
            "Completeness",
            f"{overview.get('missing_summary', {}).get('completeness_pct', 0)}%",
        )
        summary_cols[3].metric("Duplicates", f"{overview.get('duplicate_rows', 0):,}")
        st.subheader("Column Schema")
        st.dataframe(pd.DataFrame(overview.get("column_schema", [])), width="stretch")
        st.subheader("Preview")
        st.dataframe(pd.DataFrame(preview["rows"]), width="stretch")
    except requests.RequestException as exc:
        st.error(f"Could not load preview: {exc}")


def _build_filter_payload(schema: dict, key_prefix: str) -> dict:
    filters: dict = {}
    options = schema.get("filters", {})
    categorical = {
        name: cfg
        for name, cfg in options.items()
        if cfg.get("type") in {"categorical", "boolean"} and cfg.get("values")
    }
    if not categorical:
        return filters

    with st.expander("Filters", expanded=False):
        for column, cfg in categorical.items():
            selected = st.multiselect(
                column,
                cfg.get("values", []),
                key=f"{key_prefix}_filter_{column}",
            )
            if selected:
                filters[column] = {"values": selected}
    return filters


def _sparkline_html(values: list) -> str:
    numeric = [float(value) for value in values if isinstance(value, (int, float))]
    if not numeric:
        return ""
    max_value = max(abs(value) for value in numeric) or 1
    bars = []
    for value in numeric[-8:]:
        height = max(14, int(abs(value) / max_value * 34))
        bars.append(f'<span class="spark-bar" style="height:{height}px"></span>')
    return f'<div class="sparkline">{"".join(bars)}</div>'


def _kpi_icon_svg(icon: str) -> str:
    paths = {
        "table": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 4v16"/>',
        "shield": '<path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6l7-3z"/><path d="M9 12l2 2 4-5"/>',
        "chart": '<path d="M4 19h16"/><rect x="6" y="10" width="3" height="7"/><rect x="11" y="6" width="3" height="11"/><rect x="16" y="12" width="3" height="5"/>',
        "users": '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2"/><path d="M3 19c1-4 4-6 6-6s5 2 6 6"/><path d="M14 15c2 0 4 1 5 4"/>',
        "metric": '<path d="M4 17l5-5 3 3 7-8"/><path d="M15 7h4v4"/>',
    }
    path = paths.get(icon, paths["metric"])
    return f'<svg class="kpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">{path}</svg>'


def _render_kpi_cards(cards: list[dict], theme: dict | None = None) -> None:
    if not cards:
        return
    theme = theme or {}
    surface = theme.get("surface", "#FFFFFF")
    border = theme.get("border", "#D7DEE8")
    muted = theme.get("muted_text", "#64748B")
    text = theme.get("text", "#111827")
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
        }
        .kpi-topline {
            display: flex;
            align-items: center;
            justify-content: space-between;
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
        for col, card in zip(cols, cards[offset : offset + 4]):
            value = card.get("value", "")
            if card.get("format") == "percent" and isinstance(value, (int, float)):
                value = f"{value}%"
            delta = card.get("delta_percentage")
            delta_text = "No prior comparison" if delta is None else f"{card.get('trend_arrow', '->')} {delta}%"
            color = card.get("status_color") or muted
            context = card.get("business_context") or card.get("description") or ""
            sparkline = _sparkline_html(card.get("sparkline", []))
            reason = card.get("reason", "")
            action = card.get("recommended_action", "")
            impact = card.get("expected_impact", "")
            icon = _kpi_icon_svg(card.get("icon", "metric"))
            risk = card.get("risk_indicator", "normal")
            confidence = card.get("confidence_score", 0.75)
            col.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-topline">
                        <div class="kpi-label">{card.get('label', 'Metric')}</div>
                        <div style="color: {color};">{icon}</div>
                    </div>
                    <div class="kpi-value">{value}</div>
                    <div class="kpi-delta" style="color: {color};">{delta_text}</div>
                    <div style="color: {color};">{sparkline}</div>
                    <div class="kpi-meta">
                        <span style="color: {color};"><span class="risk-dot"></span>{risk.title()}</span>
                        <span>Confidence {round(float(confidence) * 100)}%</span>
                    </div>
                    <div class="kpi-context">{context}</div>
                    <div class="kpi-decision"><b>Reason:</b> {reason}</div>
                    <div class="kpi-decision"><b>Action:</b> {action}</div>
                    <div class="kpi-decision"><b>Impact:</b> {impact}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


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
            st.dataframe(pd.DataFrame(preview_rows), width="stretch")
        else:
            st.info("No preview rows are available for this dataset.")


def render_dashboard(client: BackendClient) -> None:
    st.header("Executive Dashboard")
    dataset_id = select_dataset(client)
    if not dataset_id:
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
        st.error(f"Could not load analytics: {exc}")
        return

    _render_dashboard_header(dashboard, summary)
    render_summary_metrics(summary)
    _render_dashboard_preview(preview.get("rows", []))
    _render_business_summary(dashboard, insights_payload)
    _render_kpi_cards(dashboard.get("kpi_cards", []), dashboard.get("theme", {}))

    if dashboard.get("filtered"):
        st.caption(
            f"Filtered rows: {dashboard.get('filtered_row_count', 0):,} of "
            f"{dashboard.get('original_row_count', 0):,}"
        )

    _render_data_quality_panel(summary, dashboard)

    with st.expander("Column profile", expanded=False):
        col_types = summary.get("column_types", {})
        st.json(col_types)
        numeric_summary = summary.get("numeric_summary", {})
        if numeric_summary:
            st.dataframe(pd.DataFrame(numeric_summary).T, width="stretch")
        missing_values = summary.get("missing_values_by_column", {})
        if missing_values:
            missing_df = pd.DataFrame(
                [{"column": key, "missing_values": value} for key, value in missing_values.items()]
            )
            st.dataframe(missing_df, width="stretch")

    st.subheader("Visual Analysis")
    render_plotly_chart_specs(dashboard)

    left, right = st.columns(2)
    with left:
        _render_suggested_questions(dashboard)
    with right:
        with st.container(border=True):
            st.markdown("#### Business Insights")
            for insight in insights_payload.get("insights", [])[:4]:
                render_insight(insight)


def render_ai_insights(client: BackendClient) -> None:
    st.header("Phase 3: AI Insights + Natural Language Questions")
    dataset_id = select_dataset(client)
    if not dataset_id:
        return

    try:
        insight_payload = client.get_insights(dataset_id)
        domain_payload = client.get_domain_intelligence(dataset_id)
        insights = insight_payload.get("insights", [])
    except requests.RequestException as exc:
        st.error(f"Could not load insights: {exc}")
        return

    detection = domain_payload.get("detection", {})
    st.subheader("Domain Intelligence")
    cols = st.columns(3)
    cols[0].metric("Detected Domain", detection.get("domain", "Generic Analytics"))
    cols[1].metric("Confidence", detection.get("confidence", "low").title())
    cols[2].metric("Domain KPIs", len(domain_payload.get("domain_kpis", [])))
    st.caption(detection.get("business_context", ""))

    domain_mode = domain_payload.get("domain_mode", {})
    if domain_mode.get("available"):
        with st.expander(f"{domain_mode.get('mode', '').title()} Analytics Mode", expanded=True):
            st.write(f"**What happened:** {domain_mode.get('what_happened', '')}")
            st.write(f"**Why it happened:** {domain_mode.get('why_it_happened', '')}")
            st.write(f"**What to do:** {domain_mode.get('what_to_do', '')}")
            st.write(f"**Expected impact:** {domain_mode.get('expected_impact', '')}")
            st.json({key: value for key, value in domain_mode.items() if key not in {'what_happened', 'why_it_happened', 'what_to_do', 'expected_impact'}})

    root_causes = domain_payload.get("root_causes", [])
    if root_causes:
        with st.expander("Root Cause Engine", expanded=True):
            st.dataframe(safe_table(root_causes), width="stretch")

    executive = insight_payload.get("executive_summary")
    if executive:
        st.subheader("Executive Summary")
        st.info(f"**Insight**\n\n{executive.get('insight', '')}")
        st.write(f"**Reason:** {executive.get('reason', '')}")
        st.write(f"**Action:** {executive.get('action', '')}")
        ceo_insights = executive.get("ceo_insights", [])
        if ceo_insights:
            st.subheader("CEO Insight Framework")
            for item in ceo_insights:
                with st.expander(item.get("metric", "Metric"), expanded=True):
                    st.write(f"**What happened:** {item.get('what_happened', '')}")
                    st.write(f"**Why it happened:** {item.get('why_it_happened', '')}")
                    st.write(f"**What to do:** {item.get('what_to_do', '')}")
                    st.write(f"**Expected impact:** {item.get('expected_impact', '')}")
                    st.write(f"**Confidence:** {item.get('confidence', '')}")
        with st.expander("Evidence"):
            for item in executive.get("evidence", []):
                st.write(f"- {item}")

    st.subheader("Rule-Based Insights")
    for insight in insights:
        render_insight(insight)

    st.subheader("Ask a Question")
    question = st.text_input(
        "Ask about this dataset",
        placeholder="Example: Which product has the highest sales?",
    )

    if st.button("Ask", disabled=not question.strip()):
        try:
            answer = client.ask_question(dataset_id, question)
            st.success(answer["answer"])
            with st.expander("Supporting data"):
                st.json(answer.get("supporting_data", {}))
            with st.expander("Analyst plan"):
                st.json(answer.get("analyst", {}))
        except requests.RequestException as exc:
            st.error(f"Could not answer question: {exc}")


def render_visual_builder(client: BackendClient) -> None:
    st.header("Visual Builder")
    dataset_id = select_dataset(client)
    if not dataset_id:
        return

    try:
        schema = client.get_visual_builder_schema(dataset_id)
    except requests.RequestException as exc:
        st.error(f"Could not load visual builder schema: {exc}")
        return

    dimensions = [field["name"] for field in schema.get("dimensions", [])]
    measures = [field["name"] for field in schema.get("measures", [])]
    defaults = schema.get("suggested_defaults", {})

    if not dimensions:
        st.info("No dimension fields are available for visual builder.")
        return

    filters = _build_filter_payload(schema, "visual_builder")
    col1, col2, col3, col4 = st.columns(4)
    dimension = col1.selectbox(
        "Dimension",
        dimensions,
        index=dimensions.index(defaults.get("dimension")) if defaults.get("dimension") in dimensions else 0,
    )
    measure_options = ["Count"] + measures
    default_measure = defaults.get("measure") if defaults.get("measure") in measures else "Count"
    measure_label = col2.selectbox(
        "Measure",
        measure_options,
        index=measure_options.index(default_measure) if default_measure in measure_options else 0,
    )
    chart_type = col3.selectbox("Chart", ["bar", "pie", "table"], index=0)
    aggregation = col4.selectbox("Aggregation", ["sum", "mean", "count", "min", "max"], index=0)

    spec = {
        "chart_type": chart_type,
        "dimension": dimension,
        "measure": None if measure_label == "Count" else measure_label,
        "aggregation": aggregation,
        "filters": filters,
    }

    try:
        visual = client.render_visual(dataset_id, spec)
    except requests.RequestException as exc:
        st.error(f"Could not render visual: {exc}")
        return

    chart = visual.get("chart", {})
    plotly_spec = chart.get("plotly", {})
    fig = go.Figure(data=plotly_spec.get("data", []), layout=plotly_spec.get("layout", {}))
    st.plotly_chart(fig, width="stretch")

    with st.expander("Suggestions"):
        st.dataframe(pd.DataFrame(visual.get("suggestions", [])), width="stretch")


def render_export_downloads(
    client: BackendClient,
    dataset_id: str,
    chart_ids: list[str] | None = None,
    package: str = "executive",
    label_prefix: str = "",
) -> None:
    def export_url(report_format: str) -> str:
        params: list[tuple[str, str]] = [("format", report_format), ("package", package)]
        for chart_id in chart_ids or []:
            params.append(("chart_ids", chart_id))
        return f"{client.base_url}/report/{dataset_id}/export?{urlencode(params)}"

    selected_count = len(chart_ids or [])
    target = "complete dashboard" if not chart_ids else f"{selected_count} selected visual{'s' if selected_count != 1 else ''}"
    st.markdown(f"**Download exports for {target}**")
    st.caption(
        "Click one format to generate and download it. Large PDF/PPTX exports may take a moment, but the page will not time out."
    )
    download_path = "C:\\Users\\DELL\\Downloads"
    file_names = {
        "JSON": f"{dataset_id}_report.json",
        "CSV": f"{dataset_id}.csv",
        "PDF": f"{dataset_id}_executive_report.pdf",
        "PPTX": f"{dataset_id}_executive_deck.pptx",
        "Excel": f"{dataset_id}_executive_report.xlsx",
        "PNG": f"{dataset_id}_dashboard_snapshot.png",
    }
    st.info(
        f"Download location: browser Downloads folder, usually `{download_path}` on this machine. "
        "If your browser asks where to save files, it will use the folder you choose."
    )
    with st.expander("Export file names"):
        for label, file_name in file_names.items():
            st.write(f"**{label}:** `{file_name}`")

    safe_prefix = f"{label_prefix} " if label_prefix else ""
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.link_button(
        f"{safe_prefix}JSON",
        export_url("json"),
        width="stretch",
    )
    col2.link_button(
        f"{safe_prefix}CSV",
        export_url("csv"),
        width="stretch",
    )
    col3.link_button(
        f"{safe_prefix}PDF",
        export_url("pdf"),
        width="stretch",
    )
    col4.link_button(
        f"{safe_prefix}PPTX",
        export_url("pptx"),
        width="stretch",
    )
    col5.link_button(
        f"{safe_prefix}Excel",
        export_url("xlsx"),
        width="stretch",
    )
    col6.link_button(
        f"{safe_prefix}PNG",
        export_url("png"),
        width="stretch",
    )


def render_reports(client: BackendClient) -> None:
    st.header("Reports")
    dataset_id = select_dataset(client)
    if not dataset_id:
        return

    try:
        report = client.get_report(dataset_id)
    except requests.RequestException as exc:
        st.error(f"Could not load report preview: {exc}")
        return

    branding = report.get("branding", {})
    if branding:
        st.caption(branding.get("company_name", ""))
        st.subheader(branding.get("report_title", "Executive Report"))

    overview = report.get("overview", {})
    cols = st.columns(3)
    cols[0].metric("Rows", f"{overview.get('row_count', 0):,}")
    cols[1].metric("Columns", f"{overview.get('column_count', 0):,}")
    cols[2].metric("Charts", f"{report.get('chart_count', 0):,}")

    guardrails = report.get("analysis_guardrails", {})
    if guardrails:
        with st.expander("Analysis Readiness", expanded=False):
            st.write(guardrails.get("summary", ""))
            readiness_cols = st.columns(4)
            supports = guardrails.get("supports", {})
            readiness_cols[0].metric("KPI", "Yes" if supports.get("kpi_tracking") else "No")
            readiness_cols[1].metric("Trend", "Yes" if supports.get("trend_analysis") else "No")
            readiness_cols[2].metric("Comparison", "Yes" if supports.get("comparison_analysis") else "No")
            readiness_cols[3].metric("Maps", "Yes" if supports.get("geographic_analysis") else "No")
            for item in guardrails.get("invalid_methods", []):
                st.warning(item)

    executive = report.get("executive_summary", {})
    if executive:
        st.subheader("Executive Summary")
        st.write(f"**Insight:** {executive.get('insight', '')}")
        st.write(f"**Reason:** {executive.get('reason', '')}")
        st.write(f"**Action:** {executive.get('action', '')}")

        business_story = report.get("business_story", {})
        if business_story:
            with st.expander("Business Storytelling Engine", expanded=True):
                st.write(f"**Data Story:** {business_story.get('data_story', '')}")
                st.write(f"**Trend Story:** {business_story.get('trend_story', '')}")
                st.write(f"**Business Story:** {business_story.get('business_story', '')}")

        tabs = st.tabs(["Action Framework", "Findings", "Risks", "Opportunities", "Recommendations", "Action Plan"])
        with tabs[0]:
            st.dataframe(safe_table(executive.get("decision_framework", [])), width="stretch")
        with tabs[1]:
            st.dataframe(safe_table(executive.get("key_findings", [])), width="stretch")
        with tabs[2]:
            risks = executive.get("risks", [])
            if risks:
                st.dataframe(safe_table(risks), width="stretch")
            else:
                st.success("No material risks detected from the current evidence.")
        with tabs[3]:
            st.dataframe(safe_table(executive.get("opportunities", [])), width="stretch")
        with tabs[4]:
            st.dataframe(safe_table(executive.get("recommendations", [])), width="stretch")
        with tabs[5]:
            st.dataframe(safe_table(executive.get("action_plan", [])), width="stretch")

    chart_specs = report.get("chart_specs", [])
    chart_labels = {f"{chart.get('title', chart.get('chart_id'))} ({chart.get('chart_type', 'chart')})": chart.get("chart_id") for chart in chart_specs}
    st.subheader("Export Package")
    package = st.selectbox(
        "Report package",
        ["executive", "board", "dashboard", "selected_visuals"],
        format_func=lambda value: {
            "executive": "Executive Report",
            "board": "Board Report",
            "dashboard": "Complete Dashboard",
            "selected_visuals": "Selected Visuals Only",
        }[value],
    )
    selected_labels = st.multiselect(
        "Visuals to include",
        list(chart_labels),
        default=list(chart_labels) if package != "selected_visuals" else list(chart_labels)[: min(3, len(chart_labels))],
    )
    selected_chart_ids = [chart_labels[label] for label in selected_labels if chart_labels.get(label)]
    if chart_specs:
        st.success(
            f"{len(selected_chart_ids)} visual(s) selected. Use the buttons below to download them as PDF, PPTX, PNG, JSON, or CSV."
        )
    else:
        st.info("No generated dashboard visuals are available for this dataset yet.")

    with st.container(border=True):
        render_export_downloads(
            client,
            dataset_id,
            selected_chart_ids,
            package,
            label_prefix="Download",
        )


def render_sql_lab(client: BackendClient) -> None:
    st.header("SQL Analytics Lab")
    dataset_id = select_dataset(client)
    if not dataset_id:
        return

    try:
        templates = client.get_sql_templates(dataset_id).get("templates", [])
        history = client.get_sql_history(dataset_id)
    except requests.RequestException as exc:
        st.error(f"Could not load SQL Lab: {exc}")
        return

    if "sql_lab_query" not in st.session_state:
        st.session_state["sql_lab_query"] = templates[0]["sql"] if templates else "SELECT * FROM dataset LIMIT 20"
    if "sql_lab_query_pending" in st.session_state:
        st.session_state["sql_lab_query"] = st.session_state.pop("sql_lab_query_pending")

    left, right = st.columns([2, 1])
    with right:
        st.subheader("Templates")
        for template in templates:
            if st.button(template["name"], key=f"template_{template['name']}", width="stretch"):
                st.session_state["sql_lab_query"] = template["sql"]
                st.rerun()

        st.subheader("History")
        for item in reversed(history.get("history", [])[-5:]):
            if st.button(item["sql"][:48], key=f"history_{item.get('created_at')}", width="stretch"):
                st.session_state["sql_lab_query"] = item["sql"]
                st.rerun()

        st.subheader("Saved")
        for item in history.get("saved_queries", [])[-8:]:
            if st.button(item["name"], key=f"saved_{item.get('created_at')}", width="stretch"):
                st.session_state["sql_lab_query"] = item["sql"]
                st.rerun()

    with left:
        prompt = st.text_input("Generate SQL from natural language", placeholder="Show top 10 customers by revenue")
        if st.button("Generate SQL", disabled=not prompt.strip()):
            try:
                generated = client.generate_sql(dataset_id, prompt)
                st.session_state["sql_lab_query_pending"] = generated["sql"]
                st.session_state["sql_lab_result"] = client.run_sql(dataset_id, generated["sql"], 100)
                st.session_state["sql_lab_message"] = generated.get("explanation", "")
                st.rerun()
            except requests.RequestException as exc:
                st.error(f"Could not generate SQL: {exc}")

        sql = st.text_area("SQL editor", key="sql_lab_query", height=180)
        limit = st.slider("Preview limit", 10, 1000, 100, step=10)
        actions = st.columns(5)

        if actions[0].button("Run", type="primary", width="stretch"):
            try:
                result = client.run_sql(dataset_id, sql, limit)
                st.session_state["sql_lab_result"] = result
            except requests.RequestException as exc:
                st.error(f"SQL failed: {exc}")
        if actions[1].button("Explain", width="stretch"):
            try:
                st.info(client.explain_sql(sql).get("explanation", ""))
            except requests.RequestException as exc:
                st.error(f"Could not explain SQL: {exc}")
        if actions[2].button("Optimize", width="stretch"):
            try:
                optimized = client.optimize_sql(sql)
                st.session_state["sql_lab_query_pending"] = optimized["sql"]
                st.session_state["sql_lab_message"] = optimized.get("suggestions", "")
                st.rerun()
            except requests.RequestException as exc:
                st.error(f"Could not optimize SQL: {exc}")
        if st.session_state.get("sql_lab_message"):
            st.info(st.session_state.pop("sql_lab_message"))
        if actions[3].button("Detect Errors", width="stretch"):
            try:
                checked = client.detect_sql_errors(sql)
                st.success("No SQL safety issues detected.") if checked.get("valid") else st.error(checked.get("error", "Invalid SQL"))
            except requests.RequestException as exc:
                st.error(f"Could not detect errors: {exc}")
        if actions[4].button("Save", width="stretch"):
            try:
                client.save_sql(dataset_id, f"Query {len(history.get('saved_queries', [])) + 1}", sql)
                st.success("Query saved.")
            except requests.RequestException as exc:
                st.error(f"Could not save query: {exc}")

        result = st.session_state.get("sql_lab_result")
        if result:
            st.subheader("Result Preview")
            result_df = pd.DataFrame(result.get("rows", []))
            st.dataframe(result_df, width="stretch")
            st.download_button(
                "Export results CSV",
                result_df.to_csv(index=False).encode("utf-8"),
                file_name=f"{dataset_id}_sql_results.csv",
                mime="text/csv",
            )


def _presentation_slides(report: dict) -> list[dict]:
    executive = report.get("executive_summary", {})
    story = report.get("business_story", {})
    kpis = report.get("kpi_cards", [])
    blocks = executive.get("decision_framework", [])
    return [
        {"title": "Executive Summary", "body": [executive.get("insight", ""), executive.get("reason", ""), executive.get("action", "")]},
        {"title": "Business Health Overview", "body": [story.get("business_story", "")]},
        {"title": "Key KPIs", "kpis": kpis[:4], "body": []},
        {"title": "Revenue Analysis", "body": [blocks[0].get("what_happened", "") if blocks else "", blocks[0].get("why_it_happened", "") if blocks else ""]},
        {"title": "Customer Analysis", "body": [blocks[1].get("what_happened", "") if len(blocks) > 1 else "Segment analysis appears when customer or segment fields are available."]},
        {"title": "Root Cause Analysis", "body": [block.get("why_it_happened", "") for block in blocks[:3]]},
        {"title": "Risks", "body": [item.get("risk", "") + ": " + item.get("why_it_matters", "") for item in executive.get("risks", [])] or ["No material risks detected from current evidence."]},
        {"title": "Opportunities", "body": [item.get("opportunity", "") + ": " + item.get("why", "") for item in executive.get("opportunities", [])]},
        {"title": "Recommendations", "body": [item.get("recommendation", "") for item in executive.get("recommendations", [])]},
        {"title": "Action Plan", "body": [item.get("action", "") for item in executive.get("action_plan", [])]},
    ]


def render_presentation_mode(client: BackendClient) -> None:
    st.header("Presentation Mode")
    dataset_id = select_dataset(client)
    if not dataset_id:
        return

    try:
        report = client.get_report(dataset_id)
    except requests.RequestException as exc:
        st.error(f"Could not load presentation: {exc}")
        return

    slides = _presentation_slides(report)
    index = st.slider("Slide", 1, len(slides), 1) - 1
    slide = slides[index]
    branding = report.get("branding", {})
    theme = report.get("theme", {})
    primary = branding.get("primary_color", theme.get("primary", "#0078D4"))

    st.markdown(
        f"""
        <style>
        .presentation-frame {{
            min-height: 620px;
            border-radius: 10px;
            padding: 38px 44px;
            background: {theme.get('surface', '#FFFFFF')};
            border: 1px solid {theme.get('border', '#D9E0EA')};
            box-shadow: 0 18px 42px rgba(15, 23, 42, 0.10);
        }}
        .presentation-title {{
            color: {primary};
            font-size: 2rem;
            font-weight: 800;
            margin-bottom: 8px;
        }}
        .presentation-subtitle {{
            color: {theme.get('muted_text', '#5F6B7A')};
            margin-bottom: 28px;
        }}
        .presentation-body {{
            color: {theme.get('text', '#1B1F23')};
            font-size: 1.05rem;
            line-height: 1.55;
            margin-bottom: 14px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="presentation-frame">', unsafe_allow_html=True)
    st.markdown(f'<div class="presentation-title">{slide["title"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="presentation-subtitle">{branding.get("company_name", "AI Analytics")} | Slide {index + 1} of {len(slides)}</div>', unsafe_allow_html=True)
    if slide.get("kpis"):
        _render_kpi_cards(slide["kpis"], theme)
    for item in slide.get("body", []):
        if item:
            st.markdown(f'<div class="presentation-body">{item}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.subheader("Download Presentation")
    chart_specs = report.get("chart_specs", [])
    chart_labels = {
        f"{chart.get('title', chart.get('chart_id'))} ({chart.get('chart_type', 'chart')})": chart.get("chart_id")
        for chart in chart_specs
    }
    selected_labels = st.multiselect(
        "Visuals to include in presentation exports",
        list(chart_labels),
        default=list(chart_labels),
        key="presentation_export_visuals",
    )
    selected_chart_ids = [chart_labels[label] for label in selected_labels if chart_labels.get(label)]
    with st.container(border=True):
        render_export_downloads(
            client,
            dataset_id,
            selected_chart_ids,
            "dashboard",
            label_prefix="Download",
        )


def render_regional_analytics(client: BackendClient) -> None:
    st.header("Regional Analytics")
    dataset_id = select_dataset(client)
    if not dataset_id:
        return
    try:
        regional = client.get_regional_intelligence(dataset_id)
    except requests.RequestException as exc:
        st.error(f"Could not load regional analytics: {exc}")
        return
    if not regional.get("available"):
        st.info(regional.get("geo_detection", {}).get("message", "No geographic fields detected."))
        st.write("Recommended columns: country, state, province, region, city, territory, postal code, latitude, longitude.")
        return
    st.subheader("Regional KPIs")
    cols = st.columns(max(1, min(3, len(regional.get("regional_kpis", [])))))
    for col, kpi in zip(cols, regional.get("regional_kpis", [])):
        col.metric(kpi.get("label", "Region"), kpi.get("region", ""), kpi.get("value", ""))
    if regional.get("regional_rows"):
        st.subheader("Regional Performance")
        st.dataframe(pd.DataFrame(regional["regional_rows"]), width="stretch")
    st.subheader("Executive Regional Insights")
    for item in regional.get("regional_insights", []):
        with st.expander(item.get("title", "Regional Insight"), expanded=True):
            st.write(item.get("insight", ""))
            st.write(f"**Recommendation:** {item.get('recommendation', '')}")
            st.json(item.get("evidence", []))


def render_geographic_insights(client: BackendClient) -> None:
    st.header("Geographic Insights")
    dataset_id = select_dataset(client)
    if not dataset_id:
        return
    try:
        regional = client.get_regional_intelligence(dataset_id)
    except requests.RequestException as exc:
        st.error(f"Could not load geographic insights: {exc}")
        return
    if not regional.get("available"):
        st.info(regional.get("geo_detection", {}).get("message", "No geographic fields detected."))
        st.write("Maps are hidden until location fields are available.")
        return
    charts = regional.get("map_charts", [])
    if not charts:
        st.info("Geographic columns were detected, but no map-ready visual could be generated from the available values.")
        return
    for chart in charts:
        fig = go.Figure(data=chart.get("plotly", {}).get("data", []), layout=chart.get("plotly", {}).get("layout", {}))
        st.plotly_chart(fig, width="stretch")


def render_dax_studio(client: BackendClient) -> None:
    st.header("DAX Analytics Studio")
    dataset_id = select_dataset(client)
    if not dataset_id:
        return
    try:
        library = client.get_dax_library(dataset_id)
    except requests.RequestException as exc:
        st.error(f"Could not load DAX Studio: {exc}")
        return
    if "dax_formula" not in st.session_state:
        measures = library.get("measures", [])
        st.session_state["dax_formula"] = measures[0]["dax"] if measures else "Record Count =\nCOUNTROWS('Dataset')"
    if "dax_formula_pending" in st.session_state:
        st.session_state["dax_formula"] = st.session_state.pop("dax_formula_pending")

    def render_dax_package(package: dict) -> None:
        if not package:
            return
        st.subheader("Measure Preview")
        dax_text = package.get("dax_output") or package.get("dax_measure") or package.get("dax", "")
        if dax_text:
            st.code(dax_text, language="DAX")

        preview = package.get("measure_preview", {})
        if preview:
            cols = st.columns(4)
            cols[0].metric("Measure", preview.get("measure_name", ""))
            cols[1].metric("Metric", preview.get("metric", ""))
            cols[2].metric("Value Type", preview.get("value_type", ""))
            cols[3].metric("Format", preview.get("expected_format", ""))
            st.caption(preview.get("preview_note", ""))

        validation = package.get("data_logic_validation", {})
        if validation.get("invalid_reasons"):
            for item in validation.get("invalid_reasons", []):
                st.warning(item)

        st.subheader("Best Visual")
        st.info(package.get("best_visual") or (package.get("recommended_visual_types", ["KPI Card"])[0]))

        st.subheader("Dashboard Placement")
        placement = package.get("dashboard_placement", {})
        st.write(f"**Page:** {placement.get('page', '')}")
        st.write(f"**Section:** {placement.get('section', '')}")
        st.write(f"**Purpose in flow:** {placement.get('purpose_in_flow', '')}")

        st.subheader("Business Interpretation")
        st.write(package.get("business_meaning") or package.get("pdf_ppt_business_interpretation", ""))

        st.subheader("Executive Insight")
        st.success(package.get("key_insight") or package.get("executive_insight_summary", ""))

        st.subheader("Next Best Analysis")
        st.write(package.get("next_best_question", ""))

        st.subheader("Export-Ready Summary")
        st.write(package.get("export_ready_summary", ""))

        with st.expander("Dashboard Integration Guidance"):
            for item in package.get("dashboard_integration_guidance", []):
                st.write(f"- {item}")

    left, right = st.columns([2, 1])
    with right:
        st.subheader("DAX Library")
        st.caption(f"Detected domain: {library.get('domain', 'Generic Analytics')}")
        for measure in library.get("measures", []):
            if st.button(measure["name"], key=f"dax_{measure['name']}", width="stretch"):
                st.session_state["dax_formula"] = measure["dax"]
                st.rerun()

    with left:
        prompt = st.text_input("Generate DAX from natural language", placeholder="Create Revenue YTD")
        if st.button("Generate DAX", disabled=not prompt.strip()):
            try:
                generated = client.generate_dax(dataset_id, prompt)
                st.session_state["dax_formula_pending"] = generated["dax"]
                st.session_state["dax_package"] = generated
                st.session_state["dax_message"] = generated.get("explanation", "")
                st.rerun()
            except requests.RequestException as exc:
                st.error(f"Could not generate DAX: {exc}")
        dax = st.text_area("Power BI measure builder", key="dax_formula", height=220)
        actions = st.columns(3)
        if actions[0].button("Explain", width="stretch"):
            try:
                st.info(client.explain_dax(dax).get("explanation", ""))
            except requests.RequestException as exc:
                st.error(f"Could not explain DAX: {exc}")
        if actions[1].button("Optimize", width="stretch"):
            try:
                optimized = client.optimize_dax(dax, dataset_id)
                st.session_state["dax_formula_pending"] = optimized["dax"]
                st.session_state["dax_package"] = optimized
                st.session_state["dax_message"] = optimized.get("suggestions", "")
                st.rerun()
            except requests.RequestException as exc:
                st.error(f"Could not optimize DAX: {exc}")
        if st.session_state.get("dax_message"):
            st.info(st.session_state.pop("dax_message"))
        if actions[2].button("Detect Errors", width="stretch"):
            try:
                checked = client.detect_dax_errors(dax)
                st.success("No DAX structure issues detected.") if checked.get("valid") else st.error(checked.get("error", "Invalid DAX"))
            except requests.RequestException as exc:
                st.error(f"Could not detect DAX errors: {exc}")
        render_dax_package(st.session_state.get("dax_package", {}))


def main() -> None:
    api_base_url = st.sidebar.text_input("Backend API URL", value=DEFAULT_API_BASE_URL)
    client = get_client(api_base_url)
    branding = get_active_branding(client)

    st.title(branding.get("company_name", "AI Analytics SaaS MVP"))
    st.caption(branding.get("report_title", "Executive Decision Intelligence Report"))

    render_backend_status(client)
    render_theme_selector(client)
    render_branding_editor(client, branding)

    page = st.sidebar.radio(
        "Navigation",
        [
            "Upload Data",
            "Dataset Preview",
            "Stats Dashboard",
            "AI Insights",
            "Visual Builder",
            "Reports",
            "SQL Lab",
            "DAX Studio",
            "Regional Analytics",
            "Geographic Insights",
            "Presentation Mode",
        ],
    )

    if page == "Upload Data":
        render_upload(client)
    elif page == "Dataset Preview":
        render_dataset_overview(client)
    elif page == "Stats Dashboard":
        render_dashboard(client)
    elif page == "AI Insights":
        render_ai_insights(client)
    elif page == "Visual Builder":
        render_visual_builder(client)
    elif page == "Reports":
        render_reports(client)
    elif page == "SQL Lab":
        render_sql_lab(client)
    elif page == "DAX Studio":
        render_dax_studio(client)
    elif page == "Regional Analytics":
        render_regional_analytics(client)
    elif page == "Geographic Insights":
        render_geographic_insights(client)
    elif page == "Presentation Mode":
        render_presentation_mode(client)


if __name__ == "__main__":
    main()
