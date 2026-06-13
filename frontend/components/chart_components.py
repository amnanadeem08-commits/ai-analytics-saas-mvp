from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def render_top_categories(dashboard: dict) -> None:
    top_categories = dashboard.get("top_categories", {})
    if not top_categories:
        st.info("No categorical columns available for category charts.")
        return

    for column, values in top_categories.items():
        st.subheader(f"Top values: {column}")
        chart_df = pd.DataFrame(values)
        if chart_df.empty:
            continue
        chart_df = chart_df.rename(columns={"label": column, "value": "count"})
        st.bar_chart(chart_df.set_index(column))


def render_time_trends(dashboard: dict) -> None:
    time_trends = dashboard.get("time_trends", {})
    if not time_trends:
        st.info("No date + numeric column combination found for time trends.")
        return

    for metric, values in time_trends.items():
        st.subheader(f"Monthly trend: {metric}")
        trend_df = pd.DataFrame(values)
        if trend_df.empty:
            continue
        st.line_chart(trend_df.set_index("period"))


def render_plotly_chart_specs(dashboard: dict) -> None:
    chart_specs = dashboard.get("chart_specs", [])
    if not chart_specs:
        st.info("No chart specs generated for this dataset.")
        return

    for chart in chart_specs:
        plotly_spec = chart.get("plotly", {})
        traces = plotly_spec.get("data", [])
        layout = plotly_spec.get("layout", {})
        if not traces:
            continue
        st.subheader(chart.get("title", "Chart"))
        fig = go.Figure(data=traces, layout=layout)
        st.plotly_chart(fig, width="stretch")
