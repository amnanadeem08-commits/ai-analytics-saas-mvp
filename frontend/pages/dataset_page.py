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
from frontend.utils.kpi_helpers import _local_summary
from frontend.utils.local_helpers import (
    _apply_local_cleaning_rules,
    _render_local_chart_builder,
    _render_local_data_quality_score,
    _render_local_kpis,
    build_data_anomaly_report,
    select_dataset,
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
        st.caption(f"Selected file: {uploaded_file.name} ({size_mb:.1f} MB)")
        if st.button("Upload and Analyze Dataset", type="primary", use_container_width=True):
            if not ensure_backend_available(client):
                if _register_local_uploaded_dataset(uploaded_file):
                    st.rerun()
                return
            try:
                with st.spinner("Streaming file to the backend and analyzing it..."):
                    result = client.upload_csv(uploaded_file)
                st.success(result.get("message", "Dataset uploaded."))
                backend_dataset_id = result["dataset_id"]
                st.session_state["uploaded_datasets"][backend_dataset_id] = {
                    "dataset_id": backend_dataset_id,
                    "original_filename": uploaded_file.name,
                }
                st.session_state["active_dataset_id"] = backend_dataset_id
                st.session_state["selected_dataset_id"] = backend_dataset_id
                st.session_state.pop("active_dataframe", None)
                st.session_state.pop("local_uploaded_dataset", None)
                st.session_state["local_mode_notice"] = False
                st.rerun()
            except requests.Timeout:
                if _register_local_uploaded_dataset(uploaded_file):
                    st.rerun()
            except requests.RequestException as exc:
                if not _register_local_uploaded_dataset(uploaded_file):
                    st.error("Upload could not be processed right now. Local preview and dashboard remain available when the file can be read locally.")
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
    st.header("Data Cleaning")
    st.caption("Apply transparent cleaning rules and download a cleaned copy without modifying the original upload.")
    dataset_id = select_dataset(client, key="data_cleaning_dataset_select")
    if not dataset_id:
        return

    local_df_for_anomalies = _local_active_dataframe(dataset_id) if is_local_dataset_id(dataset_id) else None
    if local_df_for_anomalies is not None:
        summary = _local_summary(local_df_for_anomalies)
        _render_local_data_quality_score(local_df_for_anomalies, summary)
        anomaly_report = build_data_anomaly_report(local_df_for_anomalies)
        st.subheader("Anomalies and Data Risks")
        if anomaly_report:
            sev_cols = st.columns(3)
            sev_cols[0].metric("High", sum(1 for item in anomaly_report if item["severity"] == "high"))
            sev_cols[1].metric("Medium", sum(1 for item in anomaly_report if item["severity"] == "medium"))
            sev_cols[2].metric("Low", sum(1 for item in anomaly_report if item["severity"] == "low"))
            for item in anomaly_report[:8]:
                with st.container(border=True):
                    st.markdown(f"#### {item['issue_type'].replace('_', ' ').title()} - {item['column']}")
                    st.caption(f"Severity: {item['severity'].title()} | Records affected: {item['records_affected']:,}")
                    st.write(item["explanation"])
                    st.write(f"**Recommended cleaning action:** {item['recommended_cleaning_action']}")
        else:
            st.success("No major statistical anomalies detected in this dataset.")

    with st.form("data_cleaning_form"):
        col1, col2, col3 = st.columns(3)
        normalize_casing = col1.selectbox("Categorical casing", ["lower", "title", "upper", "none"], index=0)
        numeric_missing_strategy = col1.selectbox("Numeric missing values", ["median", "mean", "mode", "drop_rows"], index=0)
        categorical_missing_strategy = col2.selectbox("Categorical missing values", ["mode", "unknown", "drop_rows"], index=0)
        datetime_missing_strategy = col2.selectbox("Datetime missing values", ["manual", "ffill", "bfill"], index=0)
        outlier_method = col3.selectbox("Outlier method", ["iqr", "zscore"], index=0)
        outlier_strategy = col3.selectbox("Outlier handling", ["keep", "cap", "remove"], index=0)
        high_missing_unknown_threshold = st.slider("High-missing threshold for 'Unknown' label", 0.05, 0.95, 0.20, 0.05)
        outlier_zscore_threshold = st.slider("Z-score threshold", 1.0, 6.0, 3.0, 0.5)
        run_cleaning = st.form_submit_button("Apply Cleaning Rules", use_container_width=True, type="primary")

    if not run_cleaning:
        if local_df_for_anomalies is not None:
            st.subheader("Before/After Cleaning Preview")
            st.dataframe(local_df_for_anomalies.head(25), use_container_width=True)
            st.caption("Choose cleaning rules above and apply them to preview the cleaned result and download a cleaned file.")
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
    st.success("Cleaning completed. Review the impact summary below before downloading.")
    summary_cols = st.columns(4)
    summary_cols[0].metric("Rows", f"{result['rows_before']:,} → {result['rows_after']:,}")
    summary_cols[1].metric("Columns", f"{result['columns_before']:,} → {result['columns_after']:,}")
    summary_cols[2].metric("Completeness", f"{result['completeness_before_pct']}% → {result['completeness_after_pct']}%")
    summary_cols[3].metric("Duplicates removed", f"{result['duplicates_removed']:,}")
    if result.get("high_missing_columns"):
        st.warning("High-missing columns (reviewed, not silently dropped): " + ", ".join(result["high_missing_columns"]))
    if result.get("outlier_flags"):
        st.info("Outliers flagged by column: " + ", ".join(f"{col}: {count}" for col, count in result["outlier_flags"].items()))
    st.subheader("Cleaning Change Log")
    st.dataframe(pd.DataFrame(result.get("changes", [])), use_container_width=True, hide_index=True)
    st.subheader("Cleaned Preview")
    st.dataframe(pd.DataFrame(result.get("preview_rows", [])), use_container_width=True)

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
    _render_local_chart_builder(df, palette)
