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
from frontend.utils.local_helpers import _detect_metric_column, _detect_regional_column, select_dataset

def render_location_insights(client: BackendClient) -> None:
    st.header("Location Insights")
    st.caption("Regional analysis and map-based geographic views in one place.")
    dataset_id = select_dataset(client, key="location_insights_dataset_select")
    if not dataset_id:
        return
    regional_tab, map_tab = st.tabs(["Regional Analysis", "Map View"])
    with regional_tab:
        render_regional_analytics(client, dataset_id=dataset_id)
    with map_tab:
        render_geographic_insights(client, dataset_id=dataset_id)
def render_regional_analytics(client: BackendClient, dataset_id: str | None = None) -> None:
    if dataset_id is None:
        dataset_id = select_dataset(client, key="regional_analytics_dataset")
        if not dataset_id:
            return
    if _is_local_dataset_id(dataset_id):
        local_df = _local_active_dataframe(dataset_id)
        if local_df is None:
            st.info("Upload a dataset first from Dataset Preview.")
            return
        st.info(LOCAL_MODE_INFO_MESSAGE)
        region_col = _detect_regional_column(local_df)
        metric_col = _detect_metric_column(local_df)
        if not region_col:
            st.info("No geographic fields detected.")
            st.write("Recommended columns: country, state, province, region, city, territory, postal code, latitude, longitude.")
            return
        if metric_col:
            grouped = local_df.groupby(region_col, dropna=False)[metric_col].sum().reset_index(name="value")
            metric_label = metric_col
        else:
            grouped = local_df.groupby(region_col, dropna=False).size().reset_index(name="value")
            metric_label = "Record Count"
        grouped[region_col] = grouped[region_col].astype(str)
        grouped = grouped.sort_values("value", ascending=False).head(30)
        st.subheader("Regional Performance")
        st.dataframe(grouped, use_container_width=True)
        fig = go.Figure(
            data=[
                go.Bar(
                    x=grouped[region_col],
                    y=grouped["value"],
                    marker_color=st.session_state.get("primary_color", "#118DFF"),
                )
            ]
        )
        fig.update_layout(
            title=f"Regional {metric_label}",
            xaxis_title=region_col.replace("_", " ").title(),
            yaxis_title=metric_label,
            template="ai_analytics_brand",
            height=360,
        )
        st.plotly_chart(fig, use_container_width=True)
        return
    metric_key = f"regional_metric_{dataset_id}"
    agg_key = f"regional_agg_{dataset_id}"
    try:
        bootstrap = client.get_regional_intelligence(dataset_id)
        if metric_key not in st.session_state:
            st.session_state[metric_key] = bootstrap.get("metric")
        if agg_key not in st.session_state:
            st.session_state[agg_key] = str(bootstrap.get("aggregation", "average")).title()
        metric_options = bootstrap.get("available_metrics", [])
        agg_options = bootstrap.get("aggregation_options", ["Average", "Sum", "Count", "Median"])
    except requests.RequestException as exc:
        _warn_backend_unavailable("Regional analytics")
        return
    control_cols = st.columns([2, 1])
    selected_metric = control_cols[0].selectbox(
        "Regional metric",
        metric_options or [st.session_state.get(metric_key) or "record_count"],
        key=metric_key,
    )
    selected_aggregation = control_cols[1].selectbox(
        "Aggregation",
        agg_options,
        key=agg_key,
    )
    try:
        regional = client.get_regional_intelligence(
            dataset_id,
            metric=selected_metric,
            aggregation=str(selected_aggregation).lower(),
        )
    except requests.RequestException as exc:
        _warn_backend_unavailable("Regional metric settings")
        return
    if not regional.get("available"):
        st.info(regional.get("geo_detection", {}).get("message", "No geographic fields detected."))
        st.write("Recommended columns: country, state, province, region, city, territory, postal code, latitude, longitude.")
        return
    if regional.get("regional_title"):
        st.subheader(regional["regional_title"])
    st.subheader("Regional KPIs")
    cols = st.columns(max(1, min(3, len(regional.get("regional_kpis", [])))))
    for col, kpi in zip(cols, regional.get("regional_kpis", [])):
        col.metric(kpi.get("label", "Region"), kpi.get("region", ""), kpi.get("value", ""))
    if regional.get("regional_rows"):
        st.subheader("Regional Performance")
        regional_df = pd.DataFrame(regional["regional_rows"])
        st.dataframe(regional_df, use_container_width=True)
        fig = go.Figure(
            data=[
                go.Bar(
                    x=regional_df["region"],
                    y=regional_df["value"],
                    marker_color=st.session_state.get("primary_color", "#118DFF"),
                )
            ]
        )
        fig.update_layout(
            title=regional.get("regional_title", "Regional Performance"),
            xaxis_title=regional.get("dimension", "Region").replace("_", " ").title(),
            yaxis_title=regional.get("metric_label", regional.get("metric", "Metric")),
            template="ai_analytics_brand",
            height=360,
        )
        st.plotly_chart(fig, use_container_width=True)
    st.subheader("Executive Regional Insights")
    for item in regional.get("regional_insights", []):
        with st.expander(item.get("title", "Regional Insight"), expanded=True):
            st.write(item.get("insight", ""))
            st.write(f"**Recommendation:** {item.get('recommendation', '')}")
def render_geographic_insights(client: BackendClient, dataset_id: str | None = None) -> None:
    if dataset_id is None:
        dataset_id = select_dataset(client, key="geographic_insights_dataset")
        if not dataset_id:
            return
    if _is_local_dataset_id(dataset_id):
        local_df = _local_active_dataframe(dataset_id)
        if local_df is None:
            st.info("Upload a dataset first from Dataset Preview.")
            return
        st.info(LOCAL_MODE_INFO_MESSAGE)
        lat_col = next((col for col in local_df.columns if str(col).lower() in {"lat", "latitude"}), None)
        lon_col = next((col for col in local_df.columns if str(col).lower() in {"lon", "lng", "longitude"}), None)
        if lat_col and lon_col:
            geo_df = local_df[[lat_col, lon_col]].dropna().head(1000)
            if geo_df.empty:
                st.info("Geographic coordinates are present but no valid rows were found.")
                return
            fig = go.Figure(
                data=[
                    go.Scattergeo(
                        lat=geo_df[lat_col],
                        lon=geo_df[lon_col],
                        mode="markers",
                        marker={"size": 6, "color": st.session_state.get("primary_color", "#118DFF")},
                    )
                ]
            )
            fig.update_layout(height=420, margin={"l": 0, "r": 0, "t": 40, "b": 0}, geo={"showland": True})
            st.plotly_chart(fig, use_container_width=True)
            return

        region_col = _detect_regional_column(local_df)
        if region_col:
            grouped = local_df.groupby(region_col, dropna=False).size().reset_index(name="value")
            grouped[region_col] = grouped[region_col].astype(str)
            grouped = grouped.sort_values("value", ascending=False).head(20)
            fig = go.Figure(data=[go.Bar(x=grouped[region_col], y=grouped["value"])])
            fig.update_layout(title="Geographic distribution (approximate)", height=360)
            st.plotly_chart(fig, use_container_width=True)
            st.info("No latitude/longitude found. Showing regional visuals; any map-like view is explicitly approximate.")
            return

        st.info("No geographic fields detected.")
        st.write("Maps are hidden until location fields are available.")
        return
    metric_key = f"regional_metric_{dataset_id}"
    agg_key = f"regional_agg_{dataset_id}"
    metric = st.session_state.get(metric_key)
    aggregation = st.session_state.get(agg_key, "Average")
    try:
        regional = client.get_regional_intelligence(
            dataset_id,
            metric=metric,
            aggregation=str(aggregation).lower(),
        )
    except requests.RequestException as exc:
        _warn_backend_unavailable("Geographic insights")
        return
    if not regional.get("available"):
        st.info(regional.get("geo_detection", {}).get("message", "No geographic fields detected."))
        st.write("Maps are hidden until location fields are available.")
        return
    charts = regional.get("map_charts", [])
    if not charts:
        st.info("Geographic columns were detected, but no map-ready visual could be generated from the available values.")
        return
    has_precise_map = any(chart.get("metadata", {}).get("precise_map") for chart in charts)
    if has_precise_map:
        st.caption("Map uses detected latitude/longitude coordinates.")
    else:
        st.caption("No latitude/longitude found. Showing regional visuals; any map-like view is explicitly approximate.")
    for chart in charts:
        if chart.get("metadata", {}).get("approximate_map"):
            st.info(chart.get("metadata", {}).get("note", "Approximate regional map view."))
        fig = go.Figure(data=chart.get("plotly", {}).get("data", []), layout=chart.get("plotly", {}).get("layout", {}))
        st.plotly_chart(fig, use_container_width=True)
