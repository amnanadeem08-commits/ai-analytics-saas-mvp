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

def render_visual_builder(client: BackendClient) -> None:
    st.header("Dashboard Studio")
    st.caption("Build Power BI/Tableau-style visuals using semantic field roles, safer defaults, and business-friendly settings.")
    dataset_id = select_dataset(client)
    if not dataset_id:
        return

    local_visual_df = None
    if is_local_dataset_id(dataset_id):
        local_visual_df = _local_active_dataframe(dataset_id)
        if local_visual_df is None:
            st.info("Upload a dataset first from Dataset Preview.")
            return
        schema = _build_local_visual_schema(local_visual_df)
    else:
        try:
            schema = client.get_visual_builder_schema(dataset_id)
        except requests.RequestException:
            _warn_backend_unavailable("Dashboard Studio")
            return
    dimensions = [field["name"] for field in schema.get("dimensions", [])]
    measures = [field["name"] for field in schema.get("measures", [])]
    semantic_fields = {field["name"]: field for field in schema.get("semantic_layer", [])}
    defaults = schema.get("suggested_defaults", {})
    storyboard_key = f"dashboard_studio_storyboard_{dataset_id}"
    selected_spec_key = f"dashboard_studio_spec_{dataset_id}"
    builder_mode_key = f"dashboard_studio_builder_mode_{dataset_id}"
    st.session_state.setdefault(storyboard_key, [])
    st.session_state.setdefault(builder_mode_key, "chart")

    if not dimensions:
        st.info("No business dimension fields are available for Dashboard Studio. Add category, region, date, product, or segment fields to build visuals.")
        return

    # Active toolbar with builder mode switching
    toolbar = st.columns(6)
    if toolbar[0].button("Add KPI", use_container_width=True, type="primary" if st.session_state[builder_mode_key] == "kpi" else "secondary"):
        st.session_state[builder_mode_key] = "kpi"
        st.rerun()
    if toolbar[1].button("Add Chart", use_container_width=True, type="primary" if st.session_state[builder_mode_key] == "chart" else "secondary"):
        st.session_state[builder_mode_key] = "chart"
        st.rerun()
    if toolbar[2].button("Add Table", use_container_width=True, type="primary" if st.session_state[builder_mode_key] == "table" else "secondary"):
        st.session_state[builder_mode_key] = "table"
        st.rerun()
    if toolbar[3].button("Add Slicer", use_container_width=True, type="primary" if st.session_state[builder_mode_key] == "slicer" else "secondary"):
        st.session_state[builder_mode_key] = "slicer"
        st.rerun()
    if toolbar[4].button("Add Insight", use_container_width=True, type="primary" if st.session_state[builder_mode_key] == "insight" else "secondary"):
        st.session_state[builder_mode_key] = "insight"
        st.rerun()
    has_spec = bool(st.session_state.get(selected_spec_key))
    if toolbar[5].button("Storyboard", use_container_width=True, disabled=not has_spec):
        spec_item = st.session_state[selected_spec_key]
        result = add_storyboard_entry(st.session_state[storyboard_key], spec_item)
        if result.get("added"):
            st.success("Current visual added to storyboard for this session.")
        else:
            st.info("This visual already exists in the storyboard.")
    if not has_spec:
        st.caption("Create or select a visual before adding to Storyboard.")

    recommended_visuals = schema.get("recommended_visuals", [])
    if recommended_visuals:
        st.subheader("Recommended Visuals")
        for offset in range(0, min(len(recommended_visuals), 6), 3):
            rec_cols = st.columns(3)
            for local_idx, (col, recommendation) in enumerate(
                zip(rec_cols, recommended_visuals[offset : offset + 3])
            ):
                idx = offset + local_idx
                with col.container(border=True):
                    st.markdown(f"**{recommendation.get('title', 'Recommended Visual')}**")
                    st.caption(recommendation.get("business_meaning", ""))
                    st.write(f"Chart: `{recommendation.get('suggested_chart_type', '')}`")
                    fields_used = ", ".join(recommendation.get("fields_used", [])) or "Dataset records"
                    st.write(f"Fields: {fields_used}")
                    st.caption(recommendation.get("why_useful", ""))
                    if recommendation.get("short_ai_insight"):
                        st.info(recommendation["short_ai_insight"])
                    action_cols = st.columns(2)
                    if action_cols[0].button("Use this Visual", key=f"use_{recommendation.get('visual_id')}_{idx}", use_container_width=True):
                        st.session_state[selected_spec_key] = recommendation.get("spec", {})
                        st.session_state[builder_mode_key] = recommendation.get("spec", {}).get("chart_type", "chart") if recommendation.get("spec", {}).get("chart_type") != "kpi" else "chart"
                        st.rerun()
                    if action_cols[1].button("Storyboard", key=f"story_{recommendation.get('visual_id')}_{idx}", use_container_width=True):
                        result = add_storyboard_entry(st.session_state[storyboard_key], recommendation)
                        if result.get("added"):
                            st.success("Added to storyboard for this session.")
                        else:
                            st.info("This visual already exists in the storyboard.")

    # Builder panels based on active mode
    builder_mode = st.session_state[builder_mode_key]
    if builder_mode == "kpi":
        with st.container(border=True):
            st.subheader("KPI Builder")
            st.caption("Configure a headline KPI metric for the dashboard.")
            kpi_measure = st.selectbox("KPI Metric", ["Count"] + measures, key=f"kpi_measure_{dataset_id}")
            kpi_label = st.text_input("KPI Label", value=kpi_measure if kpi_measure != "Count" else "Total Records", key=f"kpi_label_{dataset_id}")
            if st.button("Create KPI", key=f"create_kpi_{dataset_id}", use_container_width=True, type="primary"):
                kpi_spec = {
                    "chart_type": "table",
                    "dimension": dimensions[0] if dimensions else None,
                    "measure": None if kpi_measure == "Count" else kpi_measure,
                    "aggregation": "count" if kpi_measure == "Count" else "sum",
                    "sort": "descending",
                    "title": kpi_label,
                    "data_labels": True,
                    "filters": {},
                }
                st.session_state[selected_spec_key] = kpi_spec
                st.rerun()

    elif builder_mode == "table":
        with st.container(border=True):
            st.subheader("Table / Matrix Builder")
            st.caption("Configure a tabular view of your data.")
            table_dim = st.selectbox("Rows", dimensions, key=f"table_dim_{dataset_id}")
            table_meas = st.selectbox("Values", ["Count"] + measures, key=f"table_meas_{dataset_id}")
            table_agg = st.selectbox("Aggregation", ["sum", "mean", "count", "min", "max"], key=f"table_agg_{dataset_id}")
            if st.button("Create Table", key=f"create_table_{dataset_id}", use_container_width=True, type="primary"):
                table_spec = {
                    "chart_type": "table",
                    "dimension": table_dim,
                    "measure": None if table_meas == "Count" else table_meas,
                    "aggregation": table_agg,
                    "sort": "descending",
                    "title": f"{table_meas or 'Count'} by {table_dim}",
                    "data_labels": True,
                    "filters": {},
                }
                st.session_state[selected_spec_key] = table_spec
                st.rerun()

    elif builder_mode == "slicer":
        with st.container(border=True):
            st.subheader("Slicer Builder")
            st.caption("Add interactive filters to the dashboard canvas.")
            st.info("Slicers are configured in the Slicers panel below. Select fields to filter by.")
            slicer_fields = list(schema.get("filters", {}).keys())
            if slicer_fields:
                chosen = st.multiselect("Available filter fields", slicer_fields, key=f"slicer_fields_{dataset_id}")
                if chosen:
                    st.success(f"Slicers active for: {', '.join(chosen)}")
            else:
                st.info("No filter-eligible fields detected in the current dataset.")

    elif builder_mode == "insight":
        with st.container(border=True):
            st.subheader("Insight Card Builder")
            st.caption("Add an AI-generated insight card to the canvas.")
            if local_visual_df is not None:
                st.info("AI insight cards require backend connection. Local chart and table builders are available.")
                return
            try:
                insight_payload = client.get_insights(dataset_id)
                insights = insight_payload.get("insights", [])
                if insights:
                    chosen_insight = st.selectbox("Select insight", [i.get("title", i.get("message", "")) for i in insights], key=f"insight_sel_{dataset_id}")
                    if st.button("Add Insight to Canvas", key=f"add_insight_{dataset_id}", use_container_width=True, type="primary"):
                        matched = next((i for i in insights if i.get("title", i.get("message", "")) == chosen_insight), insights[0])
                        st.session_state[selected_spec_key] = {"insight": matched, "chart_type": "insight"}
                        st.rerun()
                else:
                    st.info("No AI insights are available for the current dataset.")
            except requests.RequestException:
                st.info("Could not load insights for insight card builder.")

    # Chart builder (always visible, active when builder_mode == "chart")
    filters = _dashboard_studio_slicer_payload(schema, dataset_id)
    canvas, settings = st.columns([2.2, 1])
    selected_spec = st.session_state.get(selected_spec_key, {})
    with settings:
        st.subheader("Visual Settings")
        selected_dimension_default = selected_spec.get("dimension") or defaults.get("dimension")
        dimension = st.selectbox(
            "Dimension / Axis",
            dimensions,
            index=dimensions.index(selected_dimension_default) if selected_dimension_default in dimensions else 0,
        )
        measure_options = ["Count"] + measures
        default_measure = selected_spec.get("measure") or (defaults.get("measure") if defaults.get("measure") in measures else "Count")
        default_measure = default_measure if default_measure in measure_options else "Count"
        measure_label = st.selectbox(
            "Measure / Value",
            measure_options,
            index=measure_options.index(default_measure) if default_measure in measure_options else 0,
        )
        chart_options = ["bar", "horizontal_bar", "line", "pie", "table"]
        default_chart = selected_spec.get("chart_type") or (defaults.get("chart_type") if defaults.get("chart_type") in chart_options else "bar")
        if default_chart not in chart_options:
            default_chart = "bar"
        chart_type = st.selectbox("Chart Type", chart_options, index=chart_options.index(default_chart))
        aggregation_options = ["sum", "mean", "count", "min", "max"]
        default_aggregation = selected_spec.get("aggregation") or defaults.get("aggregation", "sum")
        aggregation = st.selectbox(
            "Aggregation",
            aggregation_options,
            index=aggregation_options.index(default_aggregation) if default_aggregation in aggregation_options else 0,
        )
        sort_options = ["descending", "ascending", "none"]
        default_sort = selected_spec.get("sort", "descending")
        sort = st.selectbox("Sort", sort_options, index=sort_options.index(default_sort) if default_sort in sort_options else 0)
        legend = st.selectbox("Legend", ["None"] + dimensions, index=0)
        tooltip = st.selectbox("Tooltip", ["Auto"] + dimensions + measures, index=0)
        number_formats = ["Auto", "Whole Number", "Decimal Number", "Currency", "Percentage"]
        default_number_format = selected_spec.get("number_format", "Auto")
        number_format = st.selectbox(
            "Number Format",
            number_formats,
            index=number_formats.index(default_number_format) if default_number_format in number_formats else 0,
        )
        title = st.text_input("Title", value=selected_spec.get("title") or "")
        data_labels = st.checkbox("Data Labels", value=bool(selected_spec.get("data_labels", True)))
        selected_dimension_meta = semantic_fields.get(dimension, {})
        selected_measure_meta = semantic_fields.get(measure_label, {}) if measure_label != "Count" else {}
        if selected_dimension_meta.get("helper_message"):
            st.warning(selected_dimension_meta["helper_message"])
        if selected_measure_meta.get("helper_message"):
            st.warning(selected_measure_meta["helper_message"])
        st.caption(
            f"Axis role: {selected_dimension_meta.get('semantic_role', 'unknown')} | "
            f"Measure role: {selected_measure_meta.get('semantic_role', 'count') if measure_label != 'Count' else 'count'}"
        )

    spec = {
        "chart_type": chart_type,
        "dimension": dimension,
        "measure": None if measure_label == "Count" else measure_label,
        "aggregation": aggregation,
        "sort": sort,
        "legend": None if legend == "None" else legend,
        "tooltip": None if tooltip == "Auto" else tooltip,
        "number_format": number_format,
        "title": title.strip() or None,
        "data_labels": data_labels,
        "filters": filters,
    }

    if builder_mode == "chart" or spec.get("chart_type") not in {"insight"}:
        if local_visual_df is not None:
            visual = _render_local_visual(local_visual_df, spec)
        else:
            try:
                visual = client.render_visual(dataset_id, spec)
            except requests.RequestException:
                _warn_backend_unavailable("Dashboard visual rendering")
                return
        for warning in visual.get("semantic_warnings", []):
            st.warning(warning)

        with canvas:
            st.subheader("Dashboard Canvas")
            chart = visual.get("chart", {})
            plotly_spec = chart.get("plotly", {})
            fig = go.Figure(data=plotly_spec.get("data", []), layout=plotly_spec.get("layout", {}))
            with st.container(border=True):
                st.markdown(f"**{chart.get('title', 'Dashboard Visual')}**")
                st.caption(chart.get("metadata", {}).get("short_ai_insight", "Use this visual to compare business performance across the selected fields."))
                filtered_rows = chart.get("metadata", {}).get("filtered_rows")
                if filtered_rows == 0:
                    st.warning("No data matches the selected filters.")
                else:
                    st.plotly_chart(fig, use_container_width=True)
                card_cols = st.columns(3)
                if card_cols[0].button("Storyboard", key="add_current_visual_storyboard", use_container_width=True):
                    result = add_storyboard_entry(
                        st.session_state[storyboard_key],
                        {
                            "chart_id": chart.get("chart_id"),
                            "title": chart.get("title", "Dashboard Visual"),
                            "business_meaning": chart.get("metadata", {}).get("short_ai_insight", ""),
                            "suggested_chart_type": visual.get("applied_spec", {}).get("chart_type", ""),
                            "fields_used": chart.get("fields", []),
                            "spec": visual.get("applied_spec", {}),
                            "short_ai_insight": chart.get("metadata", {}).get("short_ai_insight", ""),
                        },
                    )
                    if result.get("added"):
                        st.success("Current visual added to storyboard for this session.")
                    else:
                        st.info("This visual already exists in the storyboard.")
                if card_cols[1].button("Add to report", key="add_current_visual_report", use_container_width=True):
                    if not chart.get("chart_id"):
                        st.warning("This visual is missing a chart ID and cannot be added to Reports.")
                    else:
                        try:
                            registration = client.register_visual(dataset_id, chart)
                            if registration.get("registered"):
                                st.success("Visual added to Reports.")
                            else:
                                st.info("Visual already exists in Reports and was reused.")
                        except requests.RequestException as exc:
                            _warn_backend_unavailable("Adding visual to Reports")
                card_cols[2].caption("Use Reports to export selected visuals as PDF, PPTX, PNG, JSON, CSV, or Excel.")
                st.caption(
                    "Known issue: legend, tooltip, and number format options may not be fully applied by the renderer, "
                    "so exports can differ from the Dashboard Studio preview."
                )
            storyboard = st.session_state.get(storyboard_key, [])
            if storyboard:
                with st.expander(f"Storyboard ({len(storyboard)} visuals)", expanded=False):
                    for item in storyboard:
                        st.write(f"**{item.get('title')}**")
                        st.caption(item.get("business_meaning") or item.get("short_ai_insight", ""))
            with st.expander("Semantic Layer"):
                semantic_rows = [
                    {
                        "Column": field.get("name"),
                        "Role": field.get("semantic_role"),
                        "Type": field.get("semantic_type"),
                        "Unique Values": field.get("unique_count"),
                        "Priority": field.get("business_priority"),
                    }
                    for field in schema.get("semantic_layer", [])
                ]
                st.dataframe(pd.DataFrame(semantic_rows), use_container_width=True, hide_index=True)

        with st.expander("Suggestions"):
            st.dataframe(pd.DataFrame(visual.get("suggestions", [])), use_container_width=True)
