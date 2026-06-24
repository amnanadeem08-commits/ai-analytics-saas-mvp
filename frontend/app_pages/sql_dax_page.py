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
from frontend.utils.local_helpers import select_dataset

def render_sql_lab(client: BackendClient) -> None:
    st.header("SQL Analytics Lab")
    dataset_id = select_dataset(client)
    if not dataset_id:
        return

    if is_local_dataset_id(dataset_id):
        st.info("SQL Lab requires backend connection. Local dataset dashboards and previews are available.")
        return

    try:
        templates = client.get_sql_templates(dataset_id).get("templates", [])
        history = client.get_sql_history(dataset_id)
    except requests.RequestException as exc:
        _warn_backend_unavailable("SQL Lab")
        return

    if "sql_lab_query" not in st.session_state:
        st.session_state["sql_lab_query"] = templates[0]["sql"] if templates else "SELECT * FROM dataset LIMIT 20"
    if "sql_lab_query_pending" in st.session_state:
        st.session_state["sql_lab_query"] = st.session_state.pop("sql_lab_query_pending")

    left, right = st.columns([2, 1])
    with right:
        st.subheader("Templates")
        for template in templates:
            if st.button(template["name"], key=f"template_{template['name']}", use_container_width=True):
                st.session_state["sql_lab_query"] = template["sql"]
                st.rerun()

        st.subheader("History")
        for item in reversed(history.get("history", [])[-5:]):
            if st.button(item["sql"][:48], key=f"history_{item.get('created_at')}", use_container_width=True):
                st.session_state["sql_lab_query"] = item["sql"]
                st.rerun()

        st.subheader("Saved")
        for item in history.get("saved_queries", [])[-8:]:
            if st.button(item["name"], key=f"saved_{item.get('created_at')}", use_container_width=True):
                st.session_state["sql_lab_query"] = item["sql"]
                st.rerun()

    with left:
        prompt = st.text_input("Generate SQL from natural language", placeholder="Show top 10 customers by revenue")
        if st.button("Generate SQL", disabled=not prompt.strip(), key=f"sql_generate_{dataset_id}"):
            try:
                generated = client.generate_sql(dataset_id, prompt)
                st.session_state["sql_lab_query_pending"] = generated["sql"]
                st.session_state["sql_lab_result"] = client.run_sql(dataset_id, generated["sql"], 100)
                st.session_state["sql_lab_message"] = generated.get("explanation", "")
                st.rerun()
            except requests.RequestException as exc:
                _warn_backend_unavailable("SQL generation")

        sql = st.text_area("SQL editor", key="sql_lab_query", height=180)
        limit = st.slider("Preview limit", 10, 1000, 100, step=10)
        actions = st.columns(5)

        if actions[0].button("Run", type="primary", use_container_width=True, key=f"sql_run_{dataset_id}"):
            try:
                result = client.run_sql(dataset_id, sql, limit)
                st.session_state["sql_lab_result"] = result
            except requests.RequestException as exc:
                st.warning("SQL could not run right now. Please try again when the backend is connected.")
        if actions[1].button("Explain", use_container_width=True, key=f"sql_explain_{dataset_id}"):
            try:
                st.info(client.explain_sql(sql).get("explanation", ""))
            except requests.RequestException as exc:
                _warn_backend_unavailable("SQL explanation")
        if actions[2].button("Optimize", use_container_width=True, key=f"sql_optimize_{dataset_id}"):
            try:
                optimized = client.optimize_sql(sql)
                st.session_state["sql_lab_query_pending"] = optimized["sql"]
                st.session_state["sql_lab_message"] = optimized.get("suggestions", "")
                st.rerun()
            except requests.RequestException as exc:
                _warn_backend_unavailable("SQL optimization")
        if st.session_state.get("sql_lab_message"):
            st.info(st.session_state.pop("sql_lab_message"))
        if actions[3].button("Detect Errors", use_container_width=True, key=f"sql_detect_errors_{dataset_id}"):
            try:
                checked = client.detect_sql_errors(sql)
                st.success("No SQL safety issues detected.") if checked.get("valid") else st.warning(checked.get("error", "Invalid SQL"))
            except requests.RequestException as exc:
                _warn_backend_unavailable("SQL validation")
        if actions[4].button("Save", use_container_width=True, key=f"sql_save_{dataset_id}"):
            try:
                client.save_sql(dataset_id, f"Query {len(history.get('saved_queries', [])) + 1}", sql)
                st.success("Query saved.")
            except requests.RequestException as exc:
                _warn_backend_unavailable("SQL query saving")

        result = st.session_state.get("sql_lab_result")
        if result:
            st.subheader("Result Preview")
            result_df = pd.DataFrame(result.get("rows", []))
            st.dataframe(result_df, use_container_width=True)
            st.download_button(
                "Export results CSV",
                result_df.to_csv(index=False).encode("utf-8"),
                file_name=f"{dataset_id}_sql_results.csv",
                mime="text/csv",
            )
def render_dax_studio(client: BackendClient) -> None:
    st.header("DAX Analytics Studio")
    dataset_id = select_dataset(client)
    if not dataset_id:
        return
    if is_local_dataset_id(dataset_id):
        st.info("DAX Studio requires backend connection. Local dataset dashboards and previews are available.")
        return

    try:
        library = client.get_dax_library(dataset_id)
    except requests.RequestException as exc:
        _warn_backend_unavailable("DAX Studio")
        return
    if "dax_formula" not in st.session_state:
        measures = library.get("measures", [])
        st.session_state["dax_formula"] = measures[0]["dax"] if measures else "Record Count =\nCOUNTROWS('Dataset')"
    if "dax_formula_pending" in st.session_state:
        st.session_state["dax_formula"] = st.session_state.pop("dax_formula_pending")

    def measure_name_from_dax(dax_text: str) -> str:
        first_line = dax_text.strip().splitlines()[0] if dax_text.strip() else "Custom Measure"
        return first_line.split("=", 1)[0].strip() or "Custom Measure"

    def preview_dataframe() -> pd.DataFrame:
        active_df = st.session_state.get("active_dataframe")
        if active_df is not None:
            return active_df.copy()
        try:
            return pd.DataFrame(client.get_preview(dataset_id, rows=100).get("rows", []))
        except requests.RequestException:
            return pd.DataFrame()

    def numeric_metric_from_dax(dax_text: str, df: pd.DataFrame) -> str | None:
        lowered = dax_text.lower()
        numeric_columns = df.select_dtypes(include="number").columns.tolist()
        for column in numeric_columns:
            if f"[{column.lower()}]" in lowered or column.lower() in lowered:
                return column
        return numeric_columns[0] if numeric_columns else None

    def category_column(df: pd.DataFrame, metric: str | None) -> str | None:
        candidates = [column for column in df.columns if column != metric and not pd.api.types.is_numeric_dtype(df[column])]
        return candidates[0] if candidates else None

    def dax_preview_value(dax_text: str, df: pd.DataFrame, metric: str | None) -> float | int | str:
        lowered = dax_text.lower()
        if df.empty:
            return "No preview data"
        if "countrows" in lowered or metric is None:
            return int(len(df))
        series = pd.to_numeric(df[metric], errors="coerce")
        if "average" in lowered or "average(" in lowered:
            return round(float(series.mean()), 2)
        if "divide" in lowered or "rate" in lowered or "%" in lowered:
            denominator = max(len(df), 1)
            return round(float(series.sum()) / denominator, 4)
        return round(float(series.sum()), 2)

    def render_best_visual_preview(package: dict, dax_text: str) -> None:
        df = preview_dataframe()
        best_visual = (package.get("best_visual") or package.get("measure_preview", {}).get("recommended_visual") or "KPI Card").lower()
        metric = numeric_metric_from_dax(dax_text, df)
        value = dax_preview_value(dax_text, df, metric)
        measure_name = measure_name_from_dax(dax_text)
        palette = st.session_state.get("chart_palette", ["#0078D4", "#004E8C", "#00B7C3", "#F2C811"])

        st.subheader("Best Visual Preview")
        st.caption(package.get("best_visual") or package.get("measure_preview", {}).get("recommended_visual") or "KPI Card")
        if df.empty:
            st.info("Preview needs dataset rows. Upload/select a dataset to render the recommended visual.")
            return

        if "gauge" in best_visual or "rate" in dax_text.lower() or "divide" in dax_text.lower():
            numeric_value = float(value) if isinstance(value, (int, float)) else 0
            if numeric_value <= 1:
                numeric_value *= 100
            fig = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=numeric_value,
                    number={"suffix": "%"},
                    title={"text": measure_name},
                    gauge={"axis": {"range": [0, 100]}, "bar": {"color": palette[0]}},
                )
            )
            fig.update_layout(height=340, margin={"l": 24, "r": 24, "t": 48, "b": 24})
            st.plotly_chart(fig, use_container_width=True)
            return

        if "line" in best_visual or "trend" in best_visual or "ytd" in dax_text.lower() or "rolling" in dax_text.lower():
            if metric:
                series = pd.to_numeric(df[metric], errors="coerce").fillna(0).head(50).reset_index(drop=True)
                fig = go.Figure(data=[go.Scatter(x=list(range(1, len(series) + 1)), y=series, mode="lines+markers", line={"color": palette[0]})])
                fig.update_layout(title=measure_name, xaxis_title="Record Sequence", yaxis_title=metric, height=360)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.metric(measure_name, value)
            return

        category = category_column(df, metric)
        if category and metric and ("bar" in best_visual or "column" in best_visual or "comparison" in best_visual):
            grouped = df.groupby(category, dropna=False)[metric].sum().reset_index().sort_values(metric, ascending=False).head(12)
            grouped[category] = grouped[category].astype(str)
            fig = go.Figure(data=[go.Bar(x=grouped[category], y=grouped[metric], marker={"color": palette[: len(grouped)]})])
            fig.update_layout(title=measure_name, xaxis_title=category, yaxis_title=metric, height=380)
            fig.update_xaxes(automargin=True)
            st.plotly_chart(fig, use_container_width=True)
            return

        st.metric(measure_name, value)

    def package_from_editor(dax_text: str) -> dict:
        measure_name = measure_name_from_dax(dax_text)
        lowered = dax_text.lower()
        recommended = "Line Chart" if any(token in lowered for token in ["totalytd", "datesinperiod", "rolling"]) else "Gauge" if "divide" in lowered or "rate" in lowered else "KPI Card"
        return {
            "dax": dax_text,
            "dax_output": dax_text,
            "measure_preview": {
                "measure_name": measure_name,
                "preview_value": "",
                "recommended_visual": recommended,
                "preview_note": "Preview generated locally from the selected dataset.",
            },
            "best_visual": recommended,
            "business_meaning": "Custom DAX measure prepared for dashboard use.",
            "key_insight": "Use the preview to verify whether this measure belongs as a KPI, trend, or category comparison.",
            "next_best_question": "Which segment, period, or category should this measure be compared against?",
            "export_ready_summary": f"{measure_name} is ready to review and save as a custom DAX measure.",
        }

    def render_dax_package(package: dict) -> None:
        if not package:
            return
        st.subheader("Measure Preview")
        dax_text = package.get("dax_output") or package.get("dax_measure") or package.get("dax", "")
        if dax_text:
            st.code(dax_text, language="DAX")

        preview = package.get("measure_preview", {})
        if preview:
            preview_value = preview.get("preview_value", "")
            if preview_value:
                st.metric("Preview", preview_value)
            preview_row = {
                "Measure Name": preview.get("measure_name", ""),
                "Business Meaning": package.get("business_meaning") or package.get("pdf_ppt_business_interpretation", ""),
                "Metric Type": preview.get("metric_type") or preview.get("value_type", ""),
                "Data Type": preview.get("data_type", ""),
                "Display Format": preview.get("display_format") or preview.get("expected_format", ""),
                "Power BI Format String": "Open Advanced Format",
                "Recommended Visual": preview.get("recommended_visual") or package.get("best_visual", ""),
            }
            st.dataframe(pd.DataFrame([preview_row]), use_container_width=True, hide_index=True)
            st.caption(preview.get("preview_note", ""))
            with st.expander("Advanced Format"):
                st.write("Raw Power BI format string")
                st.code(preview.get("power_bi_format_string") or preview.get("expected_format", "") or "Not applicable")

        validation = package.get("data_logic_validation", {})
        if validation.get("invalid_reasons"):
            for item in validation.get("invalid_reasons", []):
                st.warning(item)

        st.subheader("Best Visual")
        st.info(package.get("best_visual") or (package.get("recommended_visual_types", ["KPI Card"])[0]))
        render_best_visual_preview(package, dax_text)

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
        custom_key = f"custom_dax_measures_{dataset_id}"
        st.session_state.setdefault(custom_key, [])
        custom_measures = st.session_state[custom_key]
        if custom_measures:
            st.markdown("**Custom Measures**")
            for index, measure in enumerate(custom_measures):
                if st.button(measure["name"], key=f"custom_dax_{dataset_id}_{index}", use_container_width=True):
                    st.session_state["dax_formula"] = measure["dax"]
                    st.session_state["dax_package"] = package_from_editor(measure["dax"])
                    st.rerun()
            st.divider()
        st.markdown("**Suggested Measures**")
        for measure in library.get("measures", []):
            if st.button(measure["name"], key=f"dax_{measure['name']}", use_container_width=True):
                st.session_state["dax_formula"] = measure["dax"]
                st.session_state["dax_package"] = package_from_editor(measure["dax"])
                st.rerun()

    with left:
        prompt = st.text_input("Generate DAX from natural language", placeholder="Create Revenue YTD")
        if st.button("Generate DAX", disabled=not prompt.strip(), key=f"dax_generate_{dataset_id}"):
            try:
                generated = client.generate_dax(dataset_id, prompt)
                st.session_state["dax_formula_pending"] = generated["dax"]
                st.session_state["dax_package"] = generated
                st.session_state["dax_message"] = generated.get("explanation", "")
                st.rerun()
            except requests.RequestException as exc:
                _warn_backend_unavailable("DAX generation")
        measure_label = st.text_input("Custom measure name", value=measure_name_from_dax(st.session_state.get("dax_formula", "")), key=f"dax_measure_name_{dataset_id}")
        dax = st.text_area("Power BI measure builder", key="dax_formula", height=220)
        actions = st.columns(6)
        if actions[0].button("Explain", use_container_width=True, key=f"dax_explain_{dataset_id}"):
            try:
                st.info(client.explain_dax(dax).get("explanation", ""))
            except requests.RequestException as exc:
                _warn_backend_unavailable("DAX explanation")
        if actions[1].button("Optimize", use_container_width=True, key=f"dax_optimize_{dataset_id}"):
            try:
                optimized = client.optimize_dax(dax, dataset_id)
                st.session_state["dax_formula_pending"] = optimized["dax"]
                st.session_state["dax_package"] = optimized
                st.session_state["dax_message"] = optimized.get("suggestions", "")
                st.rerun()
            except requests.RequestException as exc:
                _warn_backend_unavailable("DAX optimization")
        if st.session_state.get("dax_message"):
            st.info(st.session_state.pop("dax_message"))
        if actions[2].button("Detect Errors", use_container_width=True, key=f"dax_detect_errors_{dataset_id}"):
            try:
                checked = client.detect_dax_errors(dax)
                st.success("No DAX structure issues detected.") if checked.get("valid") else st.warning(checked.get("error", "Invalid DAX"))
            except requests.RequestException as exc:
                _warn_backend_unavailable("DAX validation")
        if actions[3].button("Preview Visual", use_container_width=True, key=f"dax_preview_visual_{dataset_id}"):
            st.session_state["dax_package"] = package_from_editor(dax)
        if actions[4].button("Save Measure", use_container_width=True, key=f"dax_save_measure_{dataset_id}"):
            saved = {"name": measure_label.strip() or measure_name_from_dax(dax), "dax": dax}
            st.session_state[custom_key] = [item for item in st.session_state[custom_key] if item["name"] != saved["name"]]
            st.session_state[custom_key].append(saved)
            st.success(f"Saved custom DAX measure: {saved['name']}")
        if actions[5].button("Use as KPI", use_container_width=True, key=f"dax_use_as_kpi_{dataset_id}"):
            st.session_state["dax_package"] = {**package_from_editor(dax), "best_visual": "KPI Card"}
        render_dax_package(st.session_state.get("dax_package", {}))
