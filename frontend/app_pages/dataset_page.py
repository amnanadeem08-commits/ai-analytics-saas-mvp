from __future__ import annotations

import html
import io
import json
import re
from datetime import date, datetime
from pathlib import Path
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
from frontend.utils.kpi_helpers import _local_summary, _local_kpi_cards
from frontend.utils.local_helpers import (
    _apply_local_cleaning_rules,
    _render_local_chart_builder,
    _render_local_data_quality_score,
    _render_local_kpis,
    build_data_anomaly_report,
    select_dataset,
)

from frontend.services.business_columns_service import (
    BusinessColumnRecipe,
    create_business_columns,
    detect_available_recipes,
    generate_preview_rows,
    recipe_by_target,
)

def render_dataset_upload_area(client: BackendClient) -> None:
    with st.container(border=True):
        st.subheader("Upload CSV Dataset")
        st.caption("Files are sent to the backend when available; if not, they are read locally for dashboard analysis.")
        if st.session_state.get("local_mode_notice"):
            st.info(LOCAL_MODE_INFO_MESSAGE)
        uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx", "xlsm"], key="dataset_upload_main")
        if uploaded_file is None:
            return

        size_mb = uploaded_file.size / 1024 / 1024
        upload_signature = f"{uploaded_file.name}:{uploaded_file.size}"
        st.caption(f"Selected file: {uploaded_file.name} ({size_mb:.1f} MB)")

        if st.session_state.get("dataset_upload_signature") != upload_signature:
            if _register_local_uploaded_dataset(uploaded_file):
                st.session_state["dataset_upload_signature"] = upload_signature
                st.success("Dataset loaded locally. Preview and analysis are ready.")
                st.rerun()
            return

        st.success("Dataset is loaded locally for preview, cleaning, dashboards, insights, and reports.")
        if st.button("Reload selected file", use_container_width=True):
            st.session_state.pop("dataset_upload_signature", None)
            st.rerun()
def render_dataset_overview(client: BackendClient) -> None:
    st.header("Dataset Preview")
    branding = st.session_state.get("branding", DEFAULT_BRANDING)
    render_dataset_upload_area(client)
    st.divider()

    dataset_id = select_dataset(client, key="dataset_preview_select")
    if not dataset_id:
        local_dataset = st.session_state.get("local_uploaded_dataset")
        if local_dataset:
            _render_local_dataset_workbench(local_dataset["dataframe"], local_dataset["filename"], branding)
        return

    if _is_local_dataset_id(dataset_id):
        active_df = _local_active_dataframe(dataset_id)
        local_dataset = st.session_state.get("uploaded_datasets", {}).get(dataset_id, {})
        if active_df is not None:
            _render_local_dataset_workbench(active_df, local_dataset.get("original_filename", "Uploaded dataset"), branding)
        else:
            st.info("Upload a dataset first from Dataset Preview.")
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
        st.dataframe(pd.DataFrame(overview.get("column_schema", [])), use_container_width=True)
        st.subheader("Preview")
        st.dataframe(pd.DataFrame(preview["rows"]), use_container_width=True)
    except requests.RequestException as exc:
        st.warning("Could not load backend preview. Showing local preview if available.")
        local_dataset = st.session_state.get("local_uploaded_dataset")
        if local_dataset:
            _render_local_dataset_workbench(local_dataset["dataframe"], local_dataset["filename"], branding)
def render_data_cleaning(client: BackendClient) -> None:
    st.header("Data Quality Workspace")
    st.caption("Recommendation-driven cleaning. Issues and recommendations are shown first; fixes are applied only when you submit.")

    dataset_id = select_dataset(client, key="data_cleaning_dataset_select")
    if not dataset_id:
        return

    local_df_for_issues = _local_active_dataframe(dataset_id) if is_local_dataset_id(dataset_id) else None
    anomaly_report = []
    if local_df_for_issues is not None:
        summary = _local_summary(local_df_for_issues)
        _render_local_data_quality_score(local_df_for_issues, summary)
        anomaly_report = build_data_anomaly_report(local_df_for_issues)

    # ── Issues Detected ──────────────────────────────────────────────────
    st.subheader("Issues Detected")
    if anomaly_report:
        sev_cols = st.columns(3)
        sev_cols[0].metric("High", sum(1 for item in anomaly_report if item["severity"] == "high"))
        sev_cols[1].metric("Medium", sum(1 for item in anomaly_report if item["severity"] == "medium"))
        sev_cols[2].metric("Low", sum(1 for item in anomaly_report if item["severity"] == "low"))

        for item in anomaly_report[:8]:
            with st.container(border=True):
                st.markdown(f"#### {item['issue_type'].replace('_', ' ').title()} - {item['column']}")
                st.caption(
                    "Severity: "
                    f"{str(item['severity']).title()} | "
                    f"Affected Rows: {int(item['records_affected']):,}"
                )
                st.write("Business Impact:")
                st.write(item["explanation"])
                st.write("Suggested Fix:")
                st.write(f"**{item['recommended_cleaning_action']}**")
    else:
        st.info("No local issues detected (either dataset is empty or local issues require a local dataframe).")

    # ── Recommended Fixes + User Selected Fixes ─────────────────────────
    with st.form("data_quality_workspace_form"):
        st.subheader("Recommended Fixes")
        col1, col2, col3 = st.columns(3)

        normalize_casing = col1.selectbox("Categorical casing", ["lower", "title", "upper", "none"], index=0)
        numeric_missing_strategy = col1.selectbox("Numeric missing values", ["median", "mean", "mode", "drop_rows"], index=0)
        categorical_missing_strategy = col2.selectbox("Categorical missing values", ["mode", "unknown", "drop_rows"], index=0)
        datetime_missing_strategy = col2.selectbox("Datetime missing values", ["manual", "ffill", "bfill"], index=0)

        outlier_method = col3.selectbox("Outlier method", ["iqr", "zscore"], index=0)
        outlier_strategy = col3.selectbox("Outlier handling", ["keep", "cap", "remove"], index=0)

        high_missing_unknown_threshold = st.slider("High-missing threshold for 'Unknown' label", 0.05, 0.95, 0.20, 0.05)
        outlier_zscore_threshold = st.slider("Z-score threshold", 1.0, 6.0, 3.0, 0.5)

        st.subheader("User Selected Fixes")
        dup_col, _ = st.columns([2, 1])
        remove_duplicates = dup_col.checkbox(
            "Remove duplicates",
            value=True,
            help="If unchecked, duplicates are kept (when supported by cleaning options).",
        )

        run_cleaning = st.form_submit_button("Apply Selected Cleaning Fixes", use_container_width=True, type="primary")

    if not run_cleaning:
        if local_df_for_issues is not None:
            st.subheader("Cleaning Preview (No changes applied yet)")
            st.dataframe(local_df_for_issues.head(25), use_container_width=True)
            st.caption("Submit the form to apply your selected fixes to preview results and generate downloads.")
        return

    payload = {
        "normalize_casing": normalize_casing,
        "numeric_missing_strategy": numeric_missing_strategy,
        "categorical_missing_strategy": categorical_missing_strategy,
        "datetime_missing_strategy": datetime_missing_strategy,
        "high_missing_unknown_threshold": high_missing_unknown_threshold,
        "outlier_strategy": outlier_strategy,
        "outlier_method": outlier_method,
        "outlier_zscore_threshold": outlier_zscore_threshold,
        "remove_duplicates": remove_duplicates,
    }

    local_cleaned_df = None
    if is_local_dataset_id(dataset_id):
        local_df = _local_active_dataframe(dataset_id)
        if local_df is None:
            st.info("Upload a dataset first from Dataset Preview.")
            return
        local_cleaned_df, result = _apply_local_cleaning_rules(local_df, payload)
        st.session_state["local_dataframes"][dataset_id] = local_cleaned_df
        st.session_state["active_dataframe"] = local_cleaned_df
        local_dataset = st.session_state.get("local_uploaded_dataset")
        if isinstance(local_dataset, dict) and local_dataset.get("dataset_id") == dataset_id:
            local_dataset["dataframe"] = local_cleaned_df
        st.success("Cleaning applied locally for this Streamlit session.")
    else:
        try:
            result = client.clean_dataset(dataset_id, payload)
        except requests.RequestException:
            st.error("Data cleaning requires the backend connection right now.")
            return

    # ── Cleaning Results ───────────────────────────────────────────────
    st.subheader("Cleaning Results")
    st.success("Cleaning completed. Review issues, your decisions, and the applied actions below.")

    # Summary
    summary_cols = st.columns(4)
    summary_cols[0].metric("Rows", f"{result['rows_before']:,} → {result['rows_after']:,}")
    summary_cols[1].metric("Columns", f"{result['columns_before']:,} → {result['columns_after']:,}")
    summary_cols[2].metric("Completeness", f"{result['completeness_before_pct']}% → {result['completeness_after_pct']}%")
    summary_cols[3].metric("Duplicates removed", f"{result['duplicates_removed']:,}")

    if result.get("high_missing_columns"):
        st.warning("High-missing columns (reviewed, not silently dropped): " + ", ".join(result["high_missing_columns"]))
    if result.get("outlier_flags"):
        st.info("Outliers flagged by column: " + ", ".join(f"{col}: {count}" for col, count in result["outlier_flags"].items()))

    # Detailed report table (Issue/Severity/Rows/Impact/Recommended/User Decision/Applied)
    report_rows = []
    # Use anomaly_report when available for severity & business impact; otherwise show minimal.
    for item in (anomaly_report or []):
        report_rows.append(
            {
                "Issue Type": item.get("issue_type"),
                "Severity": item.get("severity"),
                "Affected Rows": item.get("records_affected"),
                "Business Impact": item.get("explanation"),
                "Recommended Action": item.get("recommended_cleaning_action"),
                "User Decision": "Applied" if run_cleaning else "Not applied",
                "Action Applied": "See change log below",
            }
        )

    # Ensure duplicates choice is always reflected
    report_rows.append(
        {
            "Issue Type": "duplicate_detection",
            "Severity": "high" if result.get("duplicates_removed") else "low",
            "Affected Rows": result.get("duplicates_removed", 0),
            "Business Impact": "Duplicate rows can inflate counts and totals.",
            "Recommended Action": "Remove duplicates" if result.get("duplicates_removed") else "Keep duplicates",
            "User Decision": "Remove duplicates" if remove_duplicates else "Keep duplicates",
            "Action Applied": "Duplicates removed" if result.get("duplicates_removed") else "Duplicates kept",
        }
    )

    st.dataframe(pd.DataFrame(report_rows), use_container_width=True, hide_index=True)

    st.subheader("Action Applied (Backend/Local Cleaning Change Log)")
    st.dataframe(pd.DataFrame(result.get("changes", [])), use_container_width=True, hide_index=True)

    st.subheader("Cleaned Preview")
    st.dataframe(pd.DataFrame(result.get("preview_rows", [])), use_container_width=True)

    # Downloads
    if local_cleaned_df is not None:
        csv_bytes = local_cleaned_df.to_csv(index=False).encode("utf-8")
        xlsx_buffer = io.BytesIO()
        local_cleaned_df.to_excel(xlsx_buffer, index=False)
        xlsx_bytes = xlsx_buffer.getvalue()
    else:
        csv_bytes = client.download_cleaned_dataset(dataset_id, result["cleaned_filename_csv"])
        xlsx_bytes = client.download_cleaned_dataset(dataset_id, result["cleaned_filename_xlsx"])

    dl_cols = st.columns(2)
    dl_cols[0].download_button(
        "Download cleaned CSV",
        data=csv_bytes,
        file_name=result["cleaned_filename_csv"],
        mime="text/csv",
        use_container_width=True,
    )
    dl_cols[1].download_button(
        "Download cleaned Excel",
        data=xlsx_bytes,
        file_name=result["cleaned_filename_xlsx"],
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    # AI Business Column Suggestions (local session only; user-initiated creation only)
    if is_local_dataset_id(dataset_id):
        _render_ai_business_column_suggestions(dataset_id)


def _render_ai_business_column_suggestions(dataset_id: str) -> None:
    df = _local_active_dataframe(dataset_id)
    if df is None or df.empty:
        st.info("Upload a dataset to enable calculated business column suggestions.")
        return

    st.subheader("AI Business Column Suggestions")
    st.caption("Suggestions are based only on existing dataset columns. No changes are applied until you create selected columns.")

    suggestions = detect_available_recipes(df)
    if not suggestions:
        st.info("No deterministic business calculated columns can be suggested from the current columns.")
        return

    with st.form(f"business_columns_form_{dataset_id}"):
        selected_targets: list[str] = []
        st.write("Select business columns to create:")

        for idx, item in enumerate(suggestions):
            recipe: BusinessColumnRecipe = item["recipe"]
            depends = item.get("depends_on_columns") or []
            target = recipe.target_column

            st.markdown(f"#### {recipe.display_name}")
            if item.get("description"):
                st.write(item["description"])
            if depends:
                st.caption("Depends on columns: " + ", ".join(map(str, depends)))

            preview_rows = generate_preview_rows(df, recipe, preview_rows=5)
            preview_vals = [list(r.values())[0] for r in preview_rows] if preview_rows else []
            st.caption("Preview (first values): " + (", ".join(map(str, preview_vals[:5])) if preview_vals else "—"))

            if st.checkbox(f"Select: {target}", value=False, key=f"bizcol_select_{dataset_id}_{idx}_{target}"):
                selected_targets.append(target)

        submitted = st.form_submit_button("Create Selected Business Columns", use_container_width=True, type="primary")

    if not submitted:
        return

    selected_recipes: list[BusinessColumnRecipe] = []
    for t in selected_targets:
        r = recipe_by_target(t)
        if r is not None:
            selected_recipes.append(r)

    if not selected_recipes:
        st.info("No business columns selected.")
        return

    new_df = create_business_columns(df, selected_recipes)

    st.session_state["active_dataframe"] = new_df
    st.session_state["local_dataframes"][dataset_id] = new_df
    st.success(f"Created {len(selected_recipes)} business calculated column(s).")


def _register_local_uploaded_dataset(uploaded_file) -> bool:
    try:
        with st.spinner("Backend unavailable. Reading file locally with pandas..."):
            local_df = _read_uploaded_dataframe(uploaded_file)
    except Exception as exc:
        st.error("Local fallback could not read this file. Please check the file format and try again.")
        return False

    local_dataset_id = _build_local_dataset_id(uploaded_file.name)
    st.session_state["uploaded_datasets"][local_dataset_id] = {
        "dataset_id": local_dataset_id,
        "original_filename": uploaded_file.name,
    }
    st.session_state["active_dataset_id"] = local_dataset_id
    st.session_state["selected_dataset_id"] = local_dataset_id
    st.session_state["active_dataframe"] = local_df
    st.session_state["local_dataframes"][local_dataset_id] = local_df
    st.session_state["local_uploaded_dataset"] = {
        "dataset_id": local_dataset_id,
        "filename": uploaded_file.name,
        "dataframe": local_df,
    }
    st.session_state["local_mode_notice"] = True
    st.info(LOCAL_MODE_INFO_MESSAGE)
    return True
def _local_active_dataframe(dataset_id: str | None = None) -> pd.DataFrame | None:
    if dataset_id:
        local_map = st.session_state.get("local_dataframes", {})
        if isinstance(local_map, dict):
            dataset_df = local_map.get(dataset_id)
            if isinstance(dataset_df, pd.DataFrame):
                return dataset_df

    active_df = st.session_state.get("active_dataframe")
    if isinstance(active_df, pd.DataFrame):
        return active_df
    local_dataset = st.session_state.get("local_uploaded_dataset")
    if isinstance(local_dataset, dict):
        local_df = local_dataset.get("dataframe")
        if isinstance(local_df, pd.DataFrame):
            return local_df
    return None
def _read_uploaded_dataframe(uploaded_file) -> pd.DataFrame:
    suffix = Path(uploaded_file.name).suffix.lower()
    content = uploaded_file.getvalue()
    buffer = io.BytesIO(content)
    if suffix in {".xlsx", ".xlsm"}:
        try:
            return pd.read_excel(buffer)
        except Exception:
            # Some exports are CSV data with an Excel-like extension.
            buffer.seek(0)
            return pd.read_csv(buffer)

    for encoding in ("utf-8", "utf-8-sig", "latin1"):
        try:
            return pd.read_csv(io.BytesIO(content), encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(io.BytesIO(content))
def _render_local_dataset_workbench(df: pd.DataFrame, filename: str, branding: dict) -> None:
    st.success(f"Previewing local dataset: {filename}")
    summary = _local_summary(df)
    render_summary_metrics(summary)

    rows = st.slider("Preview rows", min_value=5, max_value=100, value=min(10, max(5, len(df))), step=5, key="local_preview_rows")
    st.subheader("Preview")
    st.dataframe(df.head(rows), use_container_width=True)

    with st.expander("Column Schema", expanded=False):
        schema = pd.DataFrame(
            [{"column": column, "dtype": str(dtype), "missing": int(df[column].isna().sum())} for column, dtype in df.dtypes.items()]
        )
        st.dataframe(schema, use_container_width=True, hide_index=True)

    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    palette = [
        branding.get("primary_color", "#0078D4"),
        branding.get("secondary_color", "#004E8C"),
        branding.get("accent_color", "#F2C811"),
        "#10B981",
        "#F97316",
    ]
    _render_local_kpis(df, numeric_columns)

    # KPI Intelligence (local session only): reuse existing KPI cards; no fabricated metrics.
    kpis = _local_kpi_cards(df)
    if kpis:
        st.subheader("KPI Intelligence")
        st.caption("This panel interprets the existing validated KPI cards for the current dataset (no extra KPI generation).")

        # Deterministic interpretations based strictly on KPI card fields.
        for kpi in kpis:
            kpi_id = str(kpi.get("kpi_id") or kpi.get("label") or "kpi")
            title = str(kpi.get("title") or kpi.get("label") or kpi_id)
            status = str(kpi.get("status") or "neutral").upper()
            metric_type = str(kpi.get("metric_type") or "number")
            value = kpi.get("raw_value", kpi.get("formatted_value", kpi.get("value", "—")))

            # Trend signal only when the KPI was computed as a trend card.
            is_trend = "trend_" in kpi_id or "trend" in title.lower()
            trend_text = ""
            if is_trend and isinstance(kpi.get("raw_value"), (int, float)):
                # raw_value for trend cards is % change.
                trend_val = float(kpi["raw_value"])
                direction = "up" if trend_val > 0 else "down" if trend_val < 0 else "flat"
                trend_text = f"Trend: {trend_val:.1f}% ({direction})"

            # Target comparison is intentionally not fabricated. Only show if present.
            target_comp_text = ""
            if kpi.get("target_value") is not None or kpi.get("target") is not None:
                target_value = kpi.get("target_value", kpi.get("target"))
                target_comp_text = f"Target comparison: target={target_value} vs actual={kpi.get('formatted_value', kpi.get('value', '—'))}"
            else:
                target_comp_text = "Target comparison: not available (no validated targets for this MVP KPI)."

            # Confidence: deterministic mapping from status + available sample size.
            sample_size = int(kpi.get("sample_size") or len(df) or 0)
            conf = "high" if status in {"GOOD", "NEUTRAL"} and sample_size >= 50 else "medium" if sample_size >= 10 else "low"
            conf_expl = (
                "Confidence is derived from the KPI card status and dataset sample size "
                "(no external/assumed benchmarks are used)."
            )

            st.markdown(
                f"""
                <div class="ai-insight-block" style="border-left: 4px solid var(--ui-info); margin-top: 10px;">
                    <div style="display:flex; align-items:center; justify-content:space-between; gap: 12px;">
                        <div style="min-width: 0;">
                            <div class="ai-insight-title" style="color: var(--text-color);">{title}</div>
                            <div style="font-size: 1.2rem; font-weight: 900; margin-top: 2px;">{kpi.get('formatted_value','—')}</div>
                        </div>
                        <div style="flex-shrink:0; font-size: 0.8rem;">
                            <span style="padding: 3px 10px; border-radius: 999px; background: rgba(148,163,184,0.12); border: 1px solid rgba(148,163,184,0.25);">
                                Status: {status}
                            </span>
                        </div>
                    </div>
                    <div class="ai-insight-body" style="margin-top: 8px;">
                        <b>Business meaning:</b> {html.escape(str(kpi.get('short_interpretation') or kpi.get('description') or '—'))}<br/>
                        <b>Status:</b> {html.escape(status)}<br/>
                        <b>Trend:</b> {html.escape(trend_text) if trend_text else '—'}<br/>
                        <b>Target comparison:</b> {html.escape(target_comp_text)}<br/>
                        <b>Confidence:</b> {html.escape(conf.title())}<br/>
                        <span style="color: var(--text-subtle);">{html.escape(conf_expl)}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No KPI cards available to interpret for this dataset.")
    _render_local_chart_builder(df, palette)
