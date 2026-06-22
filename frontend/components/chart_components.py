from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PLOTLY_CONFIG = {
    "displayModeBar": True,
    "responsive": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
}


def _chart_key(chart: dict, index: int) -> str:
    return f"chart_{index}_{chart.get('chart_id') or chart.get('title', 'visual')}"


def _prepare_figure(chart: dict) -> go.Figure | None:
    plotly_spec = chart.get("plotly", {})
    traces = plotly_spec.get("data", [])
    layout = plotly_spec.get("layout", {})
    if not traces:
        return None
    fig = go.Figure(data=traces, layout=layout)
    fig.update_layout(
        title=None,
        height=380,
        autosize=True,
        margin=dict(l=52, r=24, t=24, b=72),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True)
    return fig


def _render_chart_header(chart: dict) -> None:
    metadata = chart.get("metadata", {})
    title = chart.get("title", "Chart")
    chart_type = chart.get("chart_type", "chart").replace("_", " ").title()
    subtitle = metadata.get("subtitle", "")
    st.markdown(
        f"""
        <div class="chart-card-header">
          <div>
            <div class="chart-card-title">{title}</div>
            <div class="chart-card-subtitle">{subtitle or chart_type}</div>
          </div>
          <div class="chart-card-pill">{chart_type}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def inject_chart_styles() -> None:
    st.markdown(
        """
        <style>
        .chart-card-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 16px;
            padding: 12px 4px 2px;
            border-bottom: 1px solid rgba(148, 163, 184, 0.22);
            margin-bottom: 6px;
        }
        .chart-card-title {
            font-size: 1rem;
            font-weight: 800;
            color: var(--text-color);
            line-height: 1.2;
        }
        .chart-card-subtitle {
            font-size: 0.78rem;
            color: rgba(100, 116, 139, 0.95);
            margin-top: 4px;
            line-height: 1.35;
        }
        .chart-card-pill {
            font-size: 0.68rem;
            font-weight: 700;
            color: var(--brand-primary);
            background: color-mix(in srgb, var(--brand-primary) 8%, transparent);
            border: 1px solid var(--brand-primary);
            border-radius: 999px;
            padding: 4px 9px;
            white-space: nowrap;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_top_categories(dashboard: dict) -> None:
    top_categories = dashboard.get("top_categories", {})
    if not top_categories:
        st.info("No categorical columns were detected, so category ranking charts are hidden.")
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
        st.info("No date plus numeric column combination was found, so time trend charts are hidden.")
        return

    for metric, values in time_trends.items():
        st.subheader(f"Monthly trend: {metric}")
        trend_df = pd.DataFrame(values)
        if trend_df.empty:
            continue
        st.line_chart(trend_df.set_index("period"))


def render_plotly_chart_specs(
    dashboard: dict,
    *,
    on_add_to_storyboard=None,
    on_add_to_report=None,
) -> None:
    chart_specs = dashboard.get("chart_specs", [])
    if not chart_specs:
        st.info("No chart-ready column combinations were detected. Add numeric, categorical, or date fields to generate visuals.")
        return
    inject_chart_styles()

    for offset in range(0, len(chart_specs), 2):
        cols = st.columns(2)
        for index, (col, chart) in enumerate(zip(cols, chart_specs[offset : offset + 2]), start=offset):
            fig = _prepare_figure(chart)
            if fig is None:
                col.info(f"{chart.get('title', 'Chart')} could not be rendered because no trace data was available.")
                continue
            with col.container(border=True):
                _render_chart_header(chart)
                st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG, key=_chart_key(chart, index))
                metadata = chart.get("metadata", {})
                if metadata.get("metric_suitability"):
                    suitability = metadata["metric_suitability"]
                    st.caption(f"Metric rule: {suitability.get('reason', '')}")
                if metadata.get("statistical_explanation"):
                    st.caption(metadata["statistical_explanation"])
                actions = st.columns([1, 1])
                if actions[0].button("➕ Storyboard", key=f"dashboard_chart_story_{chart.get('chart_id')}", use_container_width=True):
                    if callable(on_add_to_storyboard):
                        on_add_to_storyboard(chart)
                if actions[1].button("📌 Report", key=f"dashboard_chart_report_{chart.get('chart_id')}", use_container_width=True):
                    if callable(on_add_to_report):
                        on_add_to_report(chart)
