from __future__ import annotations

import html
import io
import json
import re
from datetime import date, datetime
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
from frontend.components.metric_cards import render_summary_metrics
from frontend.components.storyboard_session import add_storyboard_entry
from frontend.utils.backend_utils import (
    _build_local_dataset_id,
    _is_local_dataset_id,
    _warn_backend_unavailable,
    is_local_dataset_id,
    safe_table,
)
from frontend.utils.theme_manager import DEFAULT_BRANDING, THEME_PRESETS, _storyboard_theme_snapshot
from frontend.services.domain_detection_service import update_session_detected_domain

from frontend.utils.kpi_helpers import (
    _format_kpi_value,
    _infer_domain_context,
    _kpi_id_from_label,
    _local_column_groups,
    _local_kpi_cards,
    _local_summary,
    _quality_score,
    build_data_anomaly_report,
    build_default_kpis,
    _aggregate_kpi_series,
    _aggregation_label,
    _auto_kpi_aggregation,
    _kpi_unit_for_column,
)

def get_dataset_options(client: BackendClient) -> list[dict]:
    try:
        datasets = client.list_datasets()
    except requests.RequestException:
        datasets = []

    merged: dict[str, dict] = {}
    for item in datasets:
        dataset_id = item.get("dataset_id")
        if dataset_id:
            st.session_state["uploaded_datasets"].setdefault(dataset_id, item)
            merged[dataset_id] = item

    for dataset_id, item in st.session_state.get("uploaded_datasets", {}).items():
        if not dataset_id:
            continue
        if _is_local_dataset_id(dataset_id):
            merged[dataset_id] = {
                "dataset_id": dataset_id,
                "original_filename": item.get("original_filename", "Uploaded dataset"),
            }

    selected_id = st.session_state.get("active_dataset_id") or st.session_state.get("selected_dataset_id")
    if selected_id and selected_id in st.session_state.get("uploaded_datasets", {}) and selected_id not in merged:
        selected_item = st.session_state["uploaded_datasets"][selected_id]
        merged[selected_id] = {
            "dataset_id": selected_id,
            "original_filename": selected_item.get("original_filename", "Uploaded dataset"),
        }

    # Safety net: if a local dataframe exists but metadata was not merged yet, synthesize one option.
    local_map = st.session_state.get("local_dataframes", {})
    if not merged and isinstance(local_map, dict) and local_map:
        fallback_id = selected_id if selected_id in local_map else next(iter(local_map.keys()))
        fallback_name = st.session_state.get("uploaded_datasets", {}).get(fallback_id, {}).get("original_filename", "Uploaded dataset")
        merged[fallback_id] = {
            "dataset_id": fallback_id,
            "original_filename": fallback_name,
        }

    return list(merged.values())
def select_dataset(client: BackendClient, key: str | None = None) -> str | None:
    datasets = get_dataset_options(client)
    if not datasets:
        local_map = st.session_state.get("local_dataframes", {})
        if isinstance(local_map, dict) and local_map:
            fallback_id = st.session_state.get("active_dataset_id") or st.session_state.get("selected_dataset_id")
            if fallback_id not in local_map:
                fallback_id = next(iter(local_map.keys()))
            st.session_state["active_dataset_id"] = fallback_id
            st.session_state["selected_dataset_id"] = fallback_id
            return fallback_id
        st.info("No datasets found. Upload a CSV first.")
        return None

    labels = {
        f"{item['original_filename']} — {item['dataset_id']}": item["dataset_id"]
        for item in datasets
    }

    default_label = None
    selected_id = st.session_state.get("active_dataset_id") or st.session_state.get("selected_dataset_id")
    for label, dataset_id in labels.items():
        if dataset_id == selected_id:
            default_label = label
            break

    label_list = list(labels.keys())
    index = label_list.index(default_label) if default_label in label_list else 0
    selected_label = st.selectbox("Select dataset", label_list, index=index, key=key or "select_dataset_default")
    dataset_id = labels[selected_label]
    st.session_state["active_dataset_id"] = dataset_id
    st.session_state["selected_dataset_id"] = dataset_id
    return dataset_id
def _render_local_kpis(df: pd.DataFrame, numeric_columns: list[str]) -> None:
    st.subheader("Dashboard Cards")
    if not numeric_columns:
        cols = st.columns(3)
        cols[0].metric("Rows", f"{len(df):,}")
        cols[1].metric("Columns", f"{len(df.columns):,}")
        cols[2].metric("Duplicates", f"{df.duplicated().sum():,}")
        return

    default_kpis = numeric_columns[: min(4, len(numeric_columns))]
    selected_kpis = st.multiselect("Select KPI columns", numeric_columns, default=default_kpis, key="local_kpi_columns")
    if not selected_kpis:
        st.info("Select one or more numeric columns to show KPI cards.")
        return

    aggregation_options = ["Auto", "Average", "Sum", "Median", "Min", "Max", "Count"]
    selected_aggregation = st.selectbox("KPI aggregation", aggregation_options, key="local_kpi_aggregation")
    cols = st.columns(min(4, len(selected_kpis)))
    for col, column in zip(cols, selected_kpis):
        aggregation = _auto_kpi_aggregation(column) if selected_aggregation == "Auto" else selected_aggregation.lower()
        value = _aggregate_kpi_series(df[column], aggregation)
        unit = _kpi_unit_for_column(column)
        label = f"{_aggregation_label(aggregation)} {str(column).replace('_', ' ').title()}"
        formatted = _format_kpi_value(value, "integer" if aggregation == "count" else "number")
        col.metric(label, f"{formatted} {unit}".strip())
def _render_local_chart_builder(df: pd.DataFrame, palette: list[str]) -> None:
    st.subheader("Chart Preview")
    if df.empty:
        st.info("The uploaded dataset has no rows to chart.")
        return

    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    columns = df.columns.tolist()
    if not columns:
        st.info("The uploaded dataset has no columns to chart.")
        return

    settings, canvas = st.columns([1, 2])
    with settings:
        chart_type = st.selectbox("Chart type", ["Bar", "Line", "Scatter", "Pie", "Table"], key="local_chart_type")
        x_axis = st.selectbox("X-axis", columns, key="local_x_axis")
        y_options = ["Record Count"] + numeric_columns
        y_axis = st.selectbox("Y-axis", y_options, key="local_y_axis")
        aggregation = st.selectbox("Aggregation", ["sum", "mean", "count", "min", "max"], key="local_chart_aggregation")

    if y_axis == "Record Count":
        grouped = df.groupby(x_axis, dropna=False).size().reset_index(name="Record Count")
        value_column = "Record Count"
    else:
        grouped = (
            df.groupby(x_axis, dropna=False)[y_axis]
            .agg(aggregation)
            .reset_index()
            .rename(columns={y_axis: f"{aggregation.title()} {y_axis}"})
        )
        value_column = f"{aggregation.title()} {y_axis}"

    grouped[x_axis] = grouped[x_axis].astype(str)
    grouped = grouped.sort_values(value_column, ascending=False).head(50)

    with canvas:
        if chart_type == "Table":
            st.dataframe(grouped, use_container_width=True, hide_index=True)
            return

        title = f"{value_column} by {x_axis}"
        if chart_type == "Pie":
            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=grouped[x_axis],
                        values=grouped[value_column],
                        hole=0.38,
                        marker={"colors": palette[: len(grouped)]},
                    )
                ]
            )
        elif chart_type == "Line":
            fig = go.Figure(data=[go.Scatter(x=grouped[x_axis], y=grouped[value_column], mode="lines+markers", line={"color": palette[0]})])
        elif chart_type == "Scatter":
            fig = go.Figure(data=[go.Scatter(x=grouped[x_axis], y=grouped[value_column], mode="markers", marker={"color": palette[0], "size": 10})])
        else:
            fig = go.Figure(data=[go.Bar(x=grouped[x_axis], y=grouped[value_column], marker={"color": palette[: len(grouped)]})])
        fig.update_layout(title=title, height=430, margin={"l": 48, "r": 24, "t": 64, "b": 96})
        fig.update_xaxes(automargin=True)
        fig.update_yaxes(automargin=True)
        st.plotly_chart(fig, use_container_width=True)
def _render_local_data_quality_score(df: pd.DataFrame, summary: dict) -> None:
    score, grade, reasons = _quality_score(summary)
    with st.container(border=True):
        st.markdown("#### Data Quality Score")
        cols = st.columns([1, 1, 2])
        cols[0].metric("Score", f"{score}%")
        cols[1].metric("Grade", grade)
        with cols[2]:
            for reason in reasons:
                st.write(f"- {reason}")
def _render_local_key_metrics(df: pd.DataFrame) -> None:
    st.subheader("Key Metrics")
    cards = _local_kpi_cards(df)
    if not cards:
        st.info("No KPI cards could be generated for this dataset.")
        return

    for row_start in range(0, len(cards), 4):
        cols = st.columns(min(4, len(cards) - row_start))
        for col, card in zip(cols, cards[row_start : row_start + 4]):
            label = card.get("label") or card.get("title") or "Metric"
            value = card.get("value") or card.get("formatted_value") or "-"
            help_text = card.get("short_interpretation") or card.get("description") or card.get("business_context")
            col.metric(str(label), str(value), help=help_text)
def _render_local_chart_recommendations(df: pd.DataFrame, palette: list[str]) -> None:
    st.subheader("Chart Recommendations")
    numeric, categorical, datetime_cols = _local_column_groups(df)
    shown = 0
    cols = st.columns(2)
    if categorical:
        column = categorical[0]
        counts = df[column].astype("string").fillna("Unknown").value_counts().head(12).reset_index()
        counts.columns = [column, "Records"]
        fig = go.Figure(data=[go.Bar(x=counts[column], y=counts["Records"], marker_color=palette[: len(counts)])])
        fig.update_layout(title=f"Records by {column}", height=340, margin={"l": 36, "r": 18, "t": 54, "b": 86})
        with cols[shown % 2].container(border=True):
            st.markdown(f"#### Category Concentration: {column}")
            st.plotly_chart(fig, use_container_width=True)
        shown += 1
    if numeric:
        column = numeric[0]
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        fig = go.Figure(data=[go.Histogram(x=series, marker_color=palette[0])])
        fig.update_layout(title=f"Distribution of {column}", height=340, margin={"l": 36, "r": 18, "t": 54, "b": 54})
        with cols[shown % 2].container(border=True):
            st.markdown(f"#### Numeric Distribution: {column}")
            st.plotly_chart(fig, use_container_width=True)
        shown += 1
    if datetime_cols and numeric:
        date_col, metric = datetime_cols[0], numeric[0]
        temp = df[[date_col, metric]].copy()
        temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
        temp[metric] = pd.to_numeric(temp[metric], errors="coerce")
        trend = temp.dropna().groupby(date_col)[metric].mean().reset_index().sort_values(date_col)
        if len(trend) >= 2:
            fig = go.Figure(data=[go.Scatter(x=trend[date_col], y=trend[metric], mode="lines+markers", line={"color": palette[1 % len(palette)]})])
            fig.update_layout(title=f"Trend of {metric} over {date_col}", height=340, margin={"l": 36, "r": 18, "t": 54, "b": 54})
            with cols[shown % 2].container(border=True):
                st.markdown("#### Time Trend")
                st.plotly_chart(fig, use_container_width=True)
            shown += 1
    if shown == 0:
        st.info("No meaningful chart recommendation is available for the current column mix.")
def _render_local_forecast_and_trend(df: pd.DataFrame) -> None:
    numeric, _, datetime_cols = _local_column_groups(df)
    left, right = st.columns(2)
    with left.container(border=True):
        st.markdown("#### Forecast Predictions")
        if not datetime_cols or not numeric:
            st.info("Forecasting requires a date column and a suitable numeric measure.")
        else:
            date_col, metric = datetime_cols[0], numeric[0]
            temp = df[[date_col, metric]].copy()
            temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
            temp[metric] = pd.to_numeric(temp[metric], errors="coerce")
            trend = temp.dropna().groupby(date_col)[metric].mean().reset_index().sort_values(date_col)
            if len(trend) < 4:
                st.info("Forecasting requires a date column and a suitable numeric measure.")
            else:
                y = trend[metric].to_numpy(dtype=float)
                x = list(range(len(y)))
                slope = (y[-1] - y[0]) / max(len(y) - 1, 1)
                projected = y[-1] + slope
                st.metric(f"Next-period {metric}", f"{projected:,.2f}", f"Trend slope {slope:,.2f}", help="Simple directional projection based on the average trend slope. Use as a planning signal, not a formal forecast.")
                st.caption("Simple directional projection from observed trend; use as a planning signal, not a formal forecast.")
    with right.container(border=True):
        st.markdown("#### Trend Analysis")
        if numeric:
            metric = numeric[0]
            series = pd.to_numeric(df[metric], errors="coerce").dropna()
            if len(series) >= 4:
                first = series.head(max(1, len(series)//3)).mean()
                last = series.tail(max(1, len(series)//3)).mean()
                change = ((last - first) / abs(first) * 100) if first else 0
                direction = "increasing" if change > 5 else "decreasing" if change < -5 else "stable"
                st.write(f"The trend suggests {metric} is **{direction}** across the available row order.")
                st.caption(f"Average moved from {first:,.2f} to {last:,.2f}; this is associated with a {change:,.1f}% directional change.")
            else:
                st.info("Trend analysis needs more numeric records.")
        else:
            st.info("Trend analysis requires a numeric measure.")
def _local_anomaly_rows(df: pd.DataFrame) -> list[str]:
    numeric, categorical, _ = _local_column_groups(df)
    rows: list[str] = []
    for column in numeric[:6]:
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if len(series) < 4:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr > 0:
            count = int(((series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)).sum())
            if count:
                rows.append(f"{column}: {count:,} records fall outside the IQR range, which may affect averages and totals.")
    missing = df.isna().sum()
    for column, count in missing[missing > 0].sort_values(ascending=False).head(3).items():
        rows.append(f"{column}: {int(count):,} missing values may reduce confidence in segmented analysis.")
    duplicates = int(df.duplicated().sum())
    if duplicates:
        rows.append(f"Duplicate rows: {duplicates:,} repeated records may inflate counts or sums.")
    for column in categorical[:4]:
        counts = df[column].astype("string").fillna("Unknown").value_counts(normalize=True)
        if not counts.empty and counts.iloc[0] >= 0.75 and len(counts) > 1:
            rows.append(f"{column}: top category represents {counts.iloc[0] * 100:.1f}% of records, suggesting concentration risk.")
    return rows[:8]
def _render_local_anomalies_and_distribution(df: pd.DataFrame) -> None:
    left, right = st.columns(2)
    with left.container(border=True):
        st.markdown("#### Anomalies Detected")
        anomalies = _local_anomaly_rows(df)
        if anomalies:
            for item in anomalies:
                st.write(f"- {item}")
        else:
            st.success("No major statistical anomalies detected in the selected dataset.")
    with right.container(border=True):
        st.markdown("#### Distribution Insights")
        numeric, categorical, _ = _local_column_groups(df)
        insights: list[str] = []
        for column in numeric[:3]:
            series = pd.to_numeric(df[column], errors="coerce").dropna()
            if len(series) >= 3:
                skew = series.skew()
                shape = "right-skewed" if skew > 0.75 else "left-skewed" if skew < -0.75 else "fairly balanced"
                insights.append(f"{column} is {shape}; median {series.median():,.2f}, average {series.mean():,.2f}.")
        for column in categorical[:2]:
            top = df[column].astype("string").fillna("Unknown").value_counts().head(1)
            if not top.empty:
                insights.append(f"{column} is concentrated around '{top.index[0]}' with {int(top.iloc[0]):,} records.")
        if insights:
            for item in insights[:6]:
                st.write(f"- {item}")
        else:
            st.info("Distribution insights require numeric or categorical fields with enough variation.")
def _render_local_executive_summary(df: pd.DataFrame) -> None:
    numeric, categorical, datetime_cols = _local_column_groups(df)
    anomalies = _local_anomaly_rows(df)
    with st.container(border=True):
        st.markdown("#### Executive Summary")
        st.write(f"**What happened:** {len(df):,} records across {len(df.columns):,} fields are available for local executive analysis.")
        risk = anomalies[0] if anomalies else "No major statistical anomalies detected in the selected dataset."
        st.write(f"**Key risk:** {risk}")
        opportunity = "Use category segmentation to compare outcomes." if categorical and numeric else "Add categorical and numeric fields to unlock stronger segmentation."
        if datetime_cols and numeric:
            opportunity = "Use the detected date and numeric fields for trend monitoring and lightweight forecasting."
        st.write(f"**Key opportunity:** {opportunity}")
        st.write("**Recommended next action:** Review the data quality score, then use Dashboard Studio to build one KPI view and one segment comparison.")
def _build_local_visual_schema(df: pd.DataFrame) -> dict:
    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    datetime_columns = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()
    categorical_columns = [
        column for column in df.columns
        if column not in numeric_columns and column not in datetime_columns
    ]
    semantic_layer = []
    for column in df.columns:
        if column in numeric_columns:
            role = "measure"
            semantic_type = "numeric"
        elif column in datetime_columns:
            role = "date"
            semantic_type = "datetime"
        else:
            role = "dimension"
            semantic_type = "categorical"
        semantic_layer.append(
            {
                "name": column,
                "semantic_role": role,
                "semantic_type": semantic_type,
                "unique_count": int(df[column].nunique(dropna=True)),
                "missing_count": int(df[column].isna().sum()),
            }
        )
    dimensions = categorical_columns + datetime_columns or df.columns.tolist()
    measures = numeric_columns
    return {
        "dimensions": [{"name": column} for column in dimensions],
        "measures": [{"name": column} for column in measures],
        "datetime_columns": datetime_columns,
        "categorical_columns": categorical_columns,
        "numeric_columns": numeric_columns,
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "semantic_layer": semantic_layer,
        "filters": {column: {"type": "categorical", "values": sorted(df[column].dropna().astype(str).unique().tolist())[:100]} for column in dimensions},
        "suggested_defaults": {
            "dimension": dimensions[0] if dimensions else None,
            "measure": measures[0] if measures else None,
            "chart_type": "bar",
            "aggregation": "sum" if measures else "count",
        },
        "recommended_visuals": [],
    }
def _apply_local_cleaning_rules(df: pd.DataFrame, payload: dict) -> tuple[pd.DataFrame, dict]:
    cleaned = df.copy()
    rows_before, columns_before = cleaned.shape
    changes: list[dict] = []
    duplicates_before = int(cleaned.duplicated().sum())
    remove_duplicates = bool(payload.get("remove_duplicates", True))
    if duplicates_before and remove_duplicates:
        cleaned = cleaned.drop_duplicates()

    numeric_strategy = payload.get("numeric_missing_strategy", "median")
    categorical_strategy = payload.get("categorical_missing_strategy", "mode")
    casing = payload.get("normalize_casing", "none")

    for column in cleaned.select_dtypes(include="number").columns:
        missing = int(cleaned[column].isna().sum())
        if missing:
            if numeric_strategy == "drop_rows":
                cleaned = cleaned.dropna(subset=[column])
                action = "Dropped rows with missing numeric values"
            elif numeric_strategy == "mean":
                cleaned[column] = cleaned[column].fillna(cleaned[column].mean())
                action = "Filled numeric missing values with mean"
            elif numeric_strategy == "mode":
                mode = cleaned[column].mode(dropna=True)
                cleaned[column] = cleaned[column].fillna(mode.iloc[0] if not mode.empty else 0)
                action = "Filled numeric missing values with mode"
            else:
                cleaned[column] = cleaned[column].fillna(cleaned[column].median())
                action = "Filled numeric missing values with median"
            changes.append({"column": column, "change": action, "rows_affected": missing})

        if payload.get("outlier_strategy") in {"cap", "remove"} and cleaned[column].notna().any():
            q1 = cleaned[column].quantile(0.25)
            q3 = cleaned[column].quantile(0.75)
            iqr = q3 - q1
            if pd.notna(iqr) and iqr > 0:
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                mask = (cleaned[column] < lower) | (cleaned[column] > upper)
                count = int(mask.sum())
                if count and payload.get("outlier_strategy") == "cap":
                    cleaned[column] = cleaned[column].clip(lower, upper)
                    changes.append({"column": column, "change": "Capped IQR outliers", "rows_affected": count})
                elif count and payload.get("outlier_strategy") == "remove":
                    cleaned = cleaned.loc[~mask]
                    changes.append({"column": column, "change": "Removed IQR outlier rows", "rows_affected": count})

    non_numeric = [column for column in cleaned.columns if not pd.api.types.is_numeric_dtype(cleaned[column])]
    for column in non_numeric:
        missing = int(cleaned[column].isna().sum())
        if missing:
            if categorical_strategy == "drop_rows":
                cleaned = cleaned.dropna(subset=[column])
                action = "Dropped rows with missing categorical values"
            elif categorical_strategy == "unknown":
                cleaned[column] = cleaned[column].fillna("Unknown")
                action = "Filled categorical missing values with Unknown"
            else:
                mode = cleaned[column].mode(dropna=True)
                cleaned[column] = cleaned[column].fillna(mode.iloc[0] if not mode.empty else "Unknown")
                action = "Filled categorical missing values with mode"
            changes.append({"column": column, "change": action, "rows_affected": missing})
        if casing in {"lower", "title", "upper"} and cleaned[column].dtype == "object":
            text = cleaned[column].astype("string")
            cleaned[column] = getattr(text.str, casing)()

    missing_before = int(df.isna().sum().sum())
    missing_after = int(cleaned.isna().sum().sum())
    cells_before = max(rows_before * columns_before, 1)
    cells_after = max(cleaned.shape[0] * cleaned.shape[1], 1)
    duplicates_removed = duplicates_before if (duplicates_before and remove_duplicates) else 0
    result = {
        "rows_before": rows_before,
        "rows_after": int(cleaned.shape[0]),
        "columns_before": columns_before,
        "columns_after": int(cleaned.shape[1]),
        "completeness_before_pct": round((1 - missing_before / cells_before) * 100, 2),
        "completeness_after_pct": round((1 - missing_after / cells_after) * 100, 2),
        "duplicates_removed": duplicates_removed,
        "high_missing_columns": [],
        "outlier_flags": {},
        "changes": changes or [{"column": "Dataset", "change": "No missing values or duplicates required changes", "rows_affected": 0}],
        "preview_rows": cleaned.head(50).to_dict(orient="records"),
        "cleaned_filename_csv": "local_cleaned_dataset.csv",
        "cleaned_filename_xlsx": "local_cleaned_dataset.xlsx",
    }
    return cleaned, result
def _render_local_visual(df: pd.DataFrame, spec: dict) -> dict:
    dimension = spec.get("dimension")
    measure = spec.get("measure")
    aggregation = spec.get("aggregation", "sum")
    chart_type = spec.get("chart_type", "bar")
    working = df.copy()
    if not dimension or dimension not in working.columns:
        dimension = working.columns[0] if len(working.columns) else None
    if not dimension:
        return {"chart": {"title": "Dashboard Visual", "plotly": {"data": [], "layout": {}}, "metadata": {"filtered_rows": 0}}}

    if measure and measure in working.columns:
        values = pd.to_numeric(working[measure], errors="coerce")
        working[measure] = values
        agg = str(aggregation or "auto").lower()
        if agg in {"auto", "average"}:
            agg = "mean"
        if agg not in {"sum", "mean", "median", "count", "min", "max"}:
            agg = "mean"
        grouped = getattr(working.groupby(dimension, dropna=False)[measure], agg)().reset_index()
        value_column = measure
    else:
        grouped = working.groupby(dimension, dropna=False).size().reset_index(name="Record Count")
        value_column = "Record Count"
    grouped[dimension] = grouped[dimension].astype(str)
    grouped = grouped.sort_values(value_column, ascending=spec.get("sort") != "ascending").head(30)
    title = spec.get("title") or f"{value_column} by {dimension}"
    palette = st.session_state.get("chart_palette", ["#0078D4", "#004E8C", "#00B7C3", "#F2C811"])

    if chart_type == "line":
        data = [go.Scatter(x=grouped[dimension], y=grouped[value_column], mode="lines+markers", line={"color": palette[0]})]
    elif chart_type == "pie":
        data = [go.Pie(labels=grouped[dimension], values=grouped[value_column], hole=0.35, marker={"colors": palette})]
    elif chart_type == "table":
        data = [go.Table(header={"values": [dimension, value_column]}, cells={"values": [grouped[dimension], grouped[value_column]]})]
    elif chart_type == "horizontal_bar":
        data = [go.Bar(x=grouped[value_column], y=grouped[dimension], orientation="h", marker={"color": palette[: len(grouped)]})]
    else:
        data = [go.Bar(x=grouped[dimension], y=grouped[value_column], marker={"color": palette[: len(grouped)]})]
    fig = go.Figure(data=data)
    fig.update_layout(title=title, height=420, margin={"l": 48, "r": 24, "t": 64, "b": 96})
    return {
        "applied_spec": spec,
        "semantic_warnings": [],
        "chart": {
            "chart_id": None,
            "title": title,
            "fields": [field for field in [dimension, measure] if field],
            "plotly": fig.to_dict(),
            "metadata": {"short_ai_insight": "Local preview generated in this Streamlit session.", "filtered_rows": int(len(grouped))},
        },
    }
def _detect_regional_column(df: pd.DataFrame) -> str | None:
    preferred_tokens = ("region", "country", "state", "province", "city", "territory", "market")
    for column in df.columns:
        lowered = str(column).lower()
        if any(token in lowered for token in preferred_tokens):
            return column
    non_numeric = [col for col in df.columns if not pd.api.types.is_numeric_dtype(df[col])]
    return non_numeric[0] if non_numeric else None
def _detect_metric_column(df: pd.DataFrame) -> str | None:
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    return numeric_cols[0] if numeric_cols else None
def _local_default_figures(df: pd.DataFrame, palette: list[str] | None = None) -> list[dict]:
    palette = palette or st.session_state.get("chart_palette", ["#0078D4", "#004E8C", "#F2C811", "#10B981", "#F97316"])
    numeric, categorical, datetime_cols = _local_column_groups(df)
    figures: list[dict] = []

    for column in numeric[:3]:
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if series.empty:
            continue
        fig = go.Figure(data=[go.Histogram(x=series, marker_color=palette[len(figures) % len(palette)])])
        fig.update_layout(title=f"Distribution of {column}", xaxis_title=column, yaxis_title="Records", height=360, margin={"l": 48, "r": 24, "t": 58, "b": 58})
        figures.append({"title": f"Distribution of {column}", "figure": fig, "kind": "Numeric distribution"})

    for column in categorical[:3]:
        counts = df[column].astype("string").fillna("Unknown").value_counts().head(12).reset_index()
        if counts.empty:
            continue
        counts.columns = [column, "Records"]
        fig = go.Figure(data=[go.Bar(x=counts[column], y=counts["Records"], marker_color=palette[: len(counts)])])
        fig.update_layout(title=f"Top {column}", xaxis_title=column, yaxis_title="Records", height=360, margin={"l": 48, "r": 24, "t": 58, "b": 88})
        fig.update_xaxes(automargin=True)
        figures.append({"title": f"Top {column}", "figure": fig, "kind": "Category frequency"})

    if len(numeric) >= 2:
        temp = df[[numeric[0], numeric[1]]].apply(pd.to_numeric, errors="coerce").dropna().head(500)
        if not temp.empty:
            fig = go.Figure(data=[go.Scatter(x=temp[numeric[0]], y=temp[numeric[1]], mode="markers", marker={"color": palette[1 % len(palette)], "opacity": 0.72})])
            fig.update_layout(title=f"{numeric[1]} vs {numeric[0]}", xaxis_title=numeric[0], yaxis_title=numeric[1], height=360, margin={"l": 48, "r": 24, "t": 58, "b": 58})
            figures.append({"title": f"{numeric[1]} vs {numeric[0]}", "figure": fig, "kind": "Scatter analysis"})

    if len(numeric) >= 3:
        corr = df[numeric[:8]].apply(pd.to_numeric, errors="coerce").corr(numeric_only=True).round(2)
        if not corr.empty:
            fig = go.Figure(data=[go.Heatmap(z=corr.values, x=corr.columns, y=corr.index, colorscale="Blues", zmin=-1, zmax=1)])
            fig.update_layout(title="Correlation heatmap", height=430, margin={"l": 72, "r": 24, "t": 58, "b": 72})
            figures.append({"title": "Correlation heatmap", "figure": fig, "kind": "Correlation"})

    if datetime_cols and numeric:
        date_col, metric = datetime_cols[0], numeric[0]
        temp = df[[date_col, metric]].copy()
        temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
        temp[metric] = pd.to_numeric(temp[metric], errors="coerce")
        trend = temp.dropna().groupby(date_col)[metric].mean().reset_index().sort_values(date_col)
        if len(trend) >= 2:
            fig = go.Figure(data=[go.Scatter(x=trend[date_col], y=trend[metric], mode="lines+markers", line={"color": palette[0]})])
            fig.update_layout(title=f"Trend of {metric} over {date_col}", xaxis_title=date_col, yaxis_title=metric, height=360, margin={"l": 48, "r": 24, "t": 58, "b": 58})
            figures.append({"title": f"Trend of {metric}", "figure": fig, "kind": "Time trend"})
    return figures
def _storyboard_chart_figure(df: pd.DataFrame, chart_ref: dict, figure_catalog: list[dict] | None = None) -> tuple[go.Figure | None, str, str]:
    title = str(chart_ref.get("title") or "Storyboard visual")
    kind = str(chart_ref.get("kind") or "Visual")
    if chart_ref.get("auto_index") is not None:
        figures = figure_catalog if figure_catalog is not None else _local_default_figures(df)
        auto_index = int(chart_ref.get("auto_index"))
        if 0 <= auto_index < len(figures):
            selected = figures[auto_index]
            return selected.get("figure"), str(selected.get("title") or title), str(selected.get("kind") or kind)
        return None, title, kind

    spec = chart_ref.get("spec")
    if isinstance(spec, dict):
        rendered = _render_local_visual(df, spec)
        chart = rendered.get("chart", {})
        plotly_spec = chart.get("plotly", {})
        figure = go.Figure(data=plotly_spec.get("data", []), layout=plotly_spec.get("layout", {}))
        return figure, str(chart.get("title") or title), kind
    return None, title, kind
def _storyboard_slide_text_lines(slide: dict) -> list[str]:
    lines: list[str] = []
    content = slide.get("content", {}) if isinstance(slide.get("content"), dict) else {}

    description = content.get("description")
    if description:
        lines.append(str(description))

    for bullet in content.get("bullets", []):
        if bullet:
            lines.append(f"- {bullet}")

    for item in slide.get("insights", []):
        if item:
            lines.append(f"- {item}")

    for rec in content.get("recommendations", []):
        if isinstance(rec, dict):
            recommendation = str(rec.get("recommendation") or "")
            reason = str(rec.get("reason") or "")
            impact = str(rec.get("expected_impact") or "")
            confidence = str(rec.get("confidence") or "")
            if recommendation:
                lines.append(f"- {recommendation}")
            if reason:
                lines.append(f"  Reason: {reason}")
            if impact:
                lines.append(f"  Expected impact: {impact}")
            if confidence:
                lines.append(f"  Confidence: {confidence}")

    return [str(item)[:180] for item in lines if str(item).strip()][:10]
def _figure_png_bytes(fig: go.Figure) -> bytes:
    try:
        return pio.to_image(fig, format="png", width=1100, height=650, scale=2)
    except Exception:
        import matplotlib.pyplot as plt
        image_buffer = io.BytesIO()
        title = str(fig.layout.title.text or "Dashboard visual")
        plt.figure(figsize=(9, 5))
        plt.text(0.5, 0.5, title, ha="center", va="center", fontsize=18)
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(image_buffer, format="png", dpi=160)
        plt.close()
        return image_buffer.getvalue()
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
def _format_active_filter(column: str, criteria: dict) -> str:
    if criteria.get("values"):
        return f"{column}: {', '.join(map(str, criteria['values']))}"
    if criteria.get("min") is not None or criteria.get("max") is not None:
        return f"{column}: {criteria.get('min', 'Any')} - {criteria.get('max', 'Any')}"
    return column
def _dashboard_studio_slicer_payload(schema: dict, dataset_id: str) -> dict:
    filters: dict = {}
    options = schema.get("filters", {})
    recommendations = schema.get("slicer_recommendations", [])
    recommended_fields = [item["field"] for item in recommendations if item.get("field") in options]
    all_fields = list(options.keys())
    state_prefix = f"dashboard_studio_{dataset_id}"
    selected_key = f"{state_prefix}_slicer_fields"

    if selected_key not in st.session_state:
        st.session_state[selected_key] = recommended_fields[:4]

    st.subheader("Slicers")
    st.selectbox("Apply slicers to", ["All visuals"], index=0)
    st.caption("Slicers currently apply to all Dashboard Studio visuals.")

    left, right = st.columns([3, 1])
    selected_fields = left.multiselect(
        "Choose slicer fields",
        all_fields,
        default=[field for field in st.session_state[selected_key] if field in all_fields],
        key=f"{state_prefix}_slicer_field_picker",
        help="Recommended slicers avoid high-cardinality ID columns by default, but you can manually choose any field.",
    )
    st.session_state[selected_key] = selected_fields
    if right.button("Reset Filters", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith(f"{state_prefix}_slicer_"):
                del st.session_state[key]
        st.session_state[selected_key] = recommended_fields[:4]
        st.rerun()

    if recommendations:
        with st.expander("Recommended Slicer Fields", expanded=False):
            rows = [
                {
                    "Field": item.get("field"),
                    "Slicer Type": item.get("slicer_type"),
                    "Semantic Role": item.get("semantic_role"),
                    "Why Useful": item.get("reason"),
                }
                for item in recommendations
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if not selected_fields:
        st.info("No slicers selected. Add country, gender, category, segment, date, or numeric fields to filter visuals.")

    for column in selected_fields:
        cfg = options.get(column, {})
        filter_type = cfg.get("type")
        key_base = f"{state_prefix}_slicer_{column}"
        if filter_type in {"categorical", "boolean"}:
            values = cfg.get("values", [])
            mode = st.radio(
                f"{column} slicer type",
                ["Multi-select", "Dropdown"],
                horizontal=True,
                key=f"{key_base}_mode",
            )
            if mode == "Dropdown":
                selected_value = st.selectbox(f"Dropdown slicer: {column}", ["All"] + values, key=f"{key_base}_dropdown")
                if selected_value != "All":
                    filters[column] = {"values": [selected_value]}
            else:
                selected_values = st.multiselect(f"Multi-select slicer: {column}", values, key=f"{key_base}_multi")
                if selected_values:
                    filters[column] = {"values": selected_values}
        elif filter_type == "date_range":
            min_date = pd.to_datetime(cfg.get("min")).date() if cfg.get("min") else date.today()
            max_date = pd.to_datetime(cfg.get("max")).date() if cfg.get("max") else min_date
            selected_range = st.date_input(
                f"Date range slicer: {column}",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key=f"{key_base}_date_range",
            )
            if isinstance(selected_range, tuple) and len(selected_range) == 2:
                start, end = selected_range
                if start != min_date or end != max_date:
                    filters[column] = {"min": start.isoformat(), "max": end.isoformat()}
        elif filter_type == "numeric_range":
            min_value = float(cfg.get("min", 0) or 0)
            max_value = float(cfg.get("max", min_value) or min_value)
            if min_value == max_value:
                st.caption(f"{column} has one numeric value: {min_value:g}")
                continue
            selected_min, selected_max = st.slider(
                f"Numeric range slicer: {column}",
                min_value=min_value,
                max_value=max_value,
                value=(min_value, max_value),
                key=f"{key_base}_numeric_range",
            )
            if selected_min != min_value or selected_max != max_value:
                filters[column] = {"min": selected_min, "max": selected_max}

    st.markdown("**Active Filters**")
    if filters:
        for column, criteria in filters.items():
            st.caption(_format_active_filter(column, criteria))
    else:
        st.caption("No filters applied.")
    return filters
def _dataset_display_name(dataset_id: str) -> str:
    uploaded = st.session_state.get("uploaded_datasets", {})
    item = uploaded.get(dataset_id, {}) if isinstance(uploaded, dict) else {}
    return str(item.get("original_filename") or dataset_id)
def _zscore_outlier_notes(df: pd.DataFrame, numeric_columns: list[str]) -> list[str]:
    notes: list[str] = []
    for column in numeric_columns[:6]:
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if len(series) < 8:
            continue
        std = float(series.std())
        if std == 0:
            continue
        z = (series - float(series.mean())) / std
        count = int((z.abs() > 3.0).sum())
        if count:
            notes.append(f"{column}: {count:,} records exceed |z| > 3 and may represent unusually extreme values.")
    return notes
def _local_storyboard_chart_specs(df: pd.DataFrame, dataset_id: str) -> list[dict]:
    """
    Restore missing helper used by _add_recommended_visual_slide.
    Produces storyboard chart "spec refs" (chart_id + auto_index into _local_default_figures).
    No mutation, deterministic per dataset content.
    """
    figures = _local_default_figures(df)
    # Return up to 6 chart candidates to allow slide to pick top 4.
    charts: list[dict] = []
    for idx, fig in enumerate(figures[:6]):
        charts.append(
            {
                "chart_id": f"local_chart_{dataset_id}_{idx}",
                "title": fig.get("title") or "Local storyboard visual",
                "kind": fig.get("kind") or "Visual",
                "auto_index": idx,
            }
        )
    return charts


def _add_recommended_visual_slide(items: list[dict], df: pd.DataFrame, dataset_id: str) -> list[dict]:
    charts = _local_storyboard_chart_specs(df, dataset_id)
    if not charts:
        return items
    existing_ids = {chart.get("chart_id") for slide in items for chart in slide.get("charts", [])}
    fresh = [chart for chart in charts if chart.get("chart_id") not in existing_ids]
    if not fresh:
        return items
    kpis = _local_kpi_cards(df)[:6]
    updated = [*items]
    for offset, chart in enumerate(fresh[:4], start=1):
        kpi = kpis[(len(updated) + offset - 1) % len(kpis)] if kpis else {"label": "Records Analyzed", "value": len(df)}
        recommendation = {
            "recommendation": "Review this recommended visual with its supporting KPI before adding it to an executive decision pack.",
            "reason": "The visual was generated from valid uploaded dataset fields.",
            "expected_impact": "Improves coverage of the storyboard with real chart evidence.",
            "confidence": "Medium",
        }
        insight = f"{chart.get('title', 'Recommended visual')} adds a chart-backed view supported by {kpi.get('label', 'KPI')}."
        updated.append(
            {
                "slide_id": f"slide_recommended_{dataset_id}_{len(updated)+1}",
                "title": chart.get("title") or "Recommended Visual",
                "section_type": "recommended_visual",
                "content": {"description": insight, "recommendation": recommendation["recommendation"]},
                "charts": [chart],
                "kpis": [kpi],
                "insights": [insight],
                "recommendations": [recommendation],
                "theme_snapshot": _storyboard_theme_snapshot(),
            }
        )
    return updated
