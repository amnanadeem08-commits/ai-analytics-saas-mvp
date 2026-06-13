from __future__ import annotations

from typing import Any

import pandas as pd

from backend.core.theme_manager import AnalyticsTheme, theme_manager
from backend.processing.column_detector import detect_column_types
from backend.utils.response_utils import to_json_safe


def _chart_id(prefix: str, *parts: str) -> str:
    slug = "_".join(str(part).lower().replace(" ", "_").replace("-", "_") for part in parts if part)
    return f"{prefix}_{slug}"[:80]


def _layout(title: str, x_title: str = "", y_title: str = "", theme_name: str | None = None) -> dict[str, Any]:
    return theme_manager.plotly_layout(title, x_title=x_title, y_title=y_title, theme_name=theme_name)


def _spec(
    chart_id: str,
    title: str,
    chart_type: str,
    section: str,
    columns: list[str],
    data: list[dict[str, Any]],
    layout: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    theme: AnalyticsTheme | None = None,
) -> dict[str, Any]:
    active_theme = theme or theme_manager.get_theme()
    return {
        "chart_id": chart_id,
        "title": title,
        "chart_type": chart_type,
        "section": section,
        "columns": columns,
        "plotly": {"data": data, "layout": layout},
        "metadata": {
            **(metadata or {}),
            "theme": active_theme.name,
            "theme_display_name": active_theme.display_name,
            "drilldown_ready": True,
            "cross_filter_ready": True,
        },
    }


def _bar_for_category(df: pd.DataFrame, column: str, theme: AnalyticsTheme) -> dict[str, Any]:
    counts = df[column].value_counts(dropna=False).head(10)
    labels = ["Missing" if pd.isna(index) else str(index) for index in counts.index]
    values = [int(value) for value in counts.values]
    title = f"Top {column}"
    return _spec(
        _chart_id("bar", column),
        title,
        "bar",
        "comparisons",
        [column],
        [{"type": "bar", "x": labels, "y": values, "name": column, "marker": {"color": theme.palette[: len(labels)]}}],
        _layout(title, column, "Count", theme.name),
        {"aggregation": "count"},
        theme,
    )


def _pie_for_category(df: pd.DataFrame, column: str, theme: AnalyticsTheme) -> dict[str, Any]:
    counts = df[column].value_counts(dropna=False).head(8)
    labels = ["Missing" if pd.isna(index) else str(index) for index in counts.index]
    values = [int(value) for value in counts.values]
    title = f"{column} Composition"
    return _spec(
        _chart_id("pie", column),
        title,
        "pie",
        "comparisons",
        [column],
        [
            {
                "type": "pie",
                "labels": labels,
                "values": values,
                "name": column,
                "marker": {"colors": theme.palette[: len(labels)]},
                "hole": 0.42,
            }
        ],
        _layout(title, theme_name=theme.name),
        {"aggregation": "share"},
        theme,
    )


def _histogram_for_numeric(df: pd.DataFrame, column: str, theme: AnalyticsTheme) -> dict[str, Any]:
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    title = f"Distribution of {column}"
    return _spec(
        _chart_id("histogram", column),
        title,
        "histogram",
        "distributions",
        [column],
        [
            {
                "type": "histogram",
                "x": [to_json_safe(value) for value in series.tolist()],
                "name": column,
                "marker": {"color": theme.primary, "line": {"color": theme.surface, "width": 1}},
            }
        ],
        _layout(title, column, "Count", theme.name),
        {"aggregation": "count"},
        theme,
    )


def _line_for_trend(df: pd.DataFrame, date_column: str, numeric_column: str, theme: AnalyticsTheme) -> dict[str, Any] | None:
    trend_df = df[[date_column, numeric_column]].copy()
    trend_df[date_column] = pd.to_datetime(trend_df[date_column], errors="coerce")
    trend_df[numeric_column] = pd.to_numeric(trend_df[numeric_column], errors="coerce")
    trend_df = trend_df.dropna()
    if trend_df.empty:
        return None

    trend_df["period"] = trend_df[date_column].dt.to_period("M").astype(str)
    grouped = trend_df.groupby("period")[numeric_column].sum().reset_index()
    title = f"{numeric_column} Over Time"
    return _spec(
        _chart_id("line", date_column, numeric_column),
        title,
        "line",
        "trends",
        [date_column, numeric_column],
        [
            {
                "type": "scatter",
                "mode": "lines+markers",
                "x": grouped["period"].tolist(),
                "y": [to_json_safe(value) for value in grouped[numeric_column].tolist()],
                "name": numeric_column,
                "line": {"color": theme.primary, "width": 3},
                "marker": {"color": theme.accent, "size": 7},
            }
        ],
        _layout(title, "Period", numeric_column, theme.name),
        {"aggregation": "monthly_sum"},
        theme,
    )


def _scatter_for_pair(df: pd.DataFrame, x_column: str, y_column: str, theme: AnalyticsTheme) -> dict[str, Any]:
    work = df[[x_column, y_column]].copy()
    work[x_column] = pd.to_numeric(work[x_column], errors="coerce")
    work[y_column] = pd.to_numeric(work[y_column], errors="coerce")
    work = work.dropna().head(1000)
    title = f"{y_column} vs {x_column}"
    return _spec(
        _chart_id("scatter", x_column, y_column),
        title,
        "scatter",
        "relationships",
        [x_column, y_column],
        [
            {
                "type": "scatter",
                "mode": "markers",
                "x": [to_json_safe(value) for value in work[x_column].tolist()],
                "y": [to_json_safe(value) for value in work[y_column].tolist()],
                "name": title,
                "marker": {"color": theme.secondary, "size": 8, "opacity": 0.72},
            }
        ],
        _layout(title, x_column, y_column, theme.name),
        {"sample_limit": 1000},
        theme,
    )


def generate_chart_specs(df: pd.DataFrame, theme_name: str | None = None) -> list[dict[str, Any]]:
    theme = theme_manager.get_theme(theme_name)
    column_types = detect_column_types(df)
    numeric_columns = column_types["numeric_columns"]
    categorical_columns = column_types["categorical_columns"]
    date_columns = column_types["date_columns"]
    charts: list[dict[str, Any]] = []

    for column in numeric_columns[:4]:
        if df[column].nunique(dropna=True) > 1:
            charts.append(_histogram_for_numeric(df, column, theme))

    for column in categorical_columns[:3]:
        if df[column].nunique(dropna=True) > 1:
            charts.append(_bar_for_category(df, column, theme))
            if df[column].nunique(dropna=True) <= 8:
                charts.append(_pie_for_category(df, column, theme))

    if date_columns and numeric_columns:
        for numeric_column in numeric_columns[:3]:
            trend = _line_for_trend(df, date_columns[0], numeric_column, theme)
            if trend:
                charts.append(trend)

    if len(numeric_columns) >= 2:
        charts.append(_scatter_for_pair(df, numeric_columns[0], numeric_columns[1], theme))

    return charts
