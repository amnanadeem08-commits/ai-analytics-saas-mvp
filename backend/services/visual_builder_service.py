from __future__ import annotations

from typing import Any

import pandas as pd

from backend.core.theme_manager import theme_manager
from backend.processing.schema_service import build_column_schema
from backend.services.chart_service import _layout, _spec
from backend.services.dataset_service import load_dataset_dataframe
from backend.services.filter_service import apply_filters, build_filter_options
from backend.utils.response_utils import to_json_safe


def _field(column: dict[str, Any], role: str) -> dict[str, Any]:
    return {
        "name": column["name"],
        "role": role,
        "dtype": column["dtype"],
        "semantic_type": column["semantic_type"],
        "unique_count": column["unique_count"],
        "sample_values": column["sample_values"],
    }


def discover_visual_builder_schema(dataset_id: str) -> dict[str, Any]:
    df = load_dataset_dataframe(dataset_id)
    schema = build_column_schema(df)
    dimensions = [_field(col, "dimension") for col in schema if col["semantic_type"] in {"categorical", "boolean", "text"}]
    measures = [_field(col, "measure") for col in schema if col["semantic_type"] == "numeric"]
    dates = [_field(col, "date") for col in schema if col["semantic_type"] == "datetime"]

    return {
        "dataset_id": dataset_id,
        "dimensions": dimensions,
        "measures": measures,
        "dates": dates,
        "filters": build_filter_options(df),
        "suggested_defaults": {
            "dimension": dimensions[0]["name"] if dimensions else None,
            "measure": measures[0]["name"] if measures else None,
            "chart_type": "bar" if dimensions and measures else "table",
        },
    }


def suggest_visual_types(spec: dict[str, Any]) -> list[dict[str, Any]]:
    dimension = spec.get("dimension")
    measure = spec.get("measure")
    suggestions: list[dict[str, Any]] = []
    if dimension and measure:
        suggestions.append({"chart_type": "bar", "score": 0.95, "reason": "Dimension plus measure compares segments."})
        suggestions.append({"chart_type": "table", "score": 0.8, "reason": "Tabular ranking is useful for exact values."})
    if dimension and not measure:
        suggestions.append({"chart_type": "pie", "score": 0.75, "reason": "Dimension-only data can show composition."})
        suggestions.append({"chart_type": "bar", "score": 0.7, "reason": "Count by category is readable."})
    if measure and not dimension:
        suggestions.append({"chart_type": "histogram", "score": 0.8, "reason": "Measure-only data can show distribution."})
    if not suggestions:
        suggestions.append({"chart_type": "table", "score": 0.5, "reason": "Default view for selected fields."})
    return suggestions


def _aggregate(df: pd.DataFrame, dimension: str, measure: str | None, aggregation: str) -> pd.DataFrame:
    if not measure:
        grouped = df[dimension].value_counts(dropna=False).reset_index()
        grouped.columns = [dimension, "count"]
        return grouped

    agg = aggregation.lower()
    if agg not in {"sum", "mean", "count", "min", "max"}:
        agg = "sum"
    work = df[[dimension, measure]].copy()
    work[measure] = pd.to_numeric(work[measure], errors="coerce")
    grouped = getattr(work.groupby(dimension, dropna=False)[measure], agg)().reset_index()
    return grouped.sort_values(measure, ascending=False).head(25)


def render_visual_builder_chart(dataset_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    theme = theme_manager.get_theme()
    df = apply_filters(load_dataset_dataframe(dataset_id), spec.get("filters") or {})
    schema = discover_visual_builder_schema(dataset_id)
    dimension = spec.get("dimension") or schema["suggested_defaults"].get("dimension")
    measure = spec.get("measure") or schema["suggested_defaults"].get("measure")
    chart_type = (spec.get("chart_type") or "bar").lower()
    aggregation = spec.get("aggregation") or "sum"

    if not dimension:
        raise ValueError("A dimension column is required to render a visual.")
    if dimension not in df.columns:
        raise ValueError(f"Unknown dimension column: {dimension}")
    if measure and measure not in df.columns:
        raise ValueError(f"Unknown measure column: {measure}")

    grouped = _aggregate(df, dimension, measure, aggregation)
    value_column = measure or "count"
    x_values = grouped[dimension].astype(str).tolist()
    y_values = [to_json_safe(value) for value in grouped[value_column].tolist()]
    title = f"{aggregation.title()} {value_column} by {dimension}" if measure else f"Count by {dimension}"

    if chart_type == "pie":
        data = [
            {
                "type": "pie",
                "labels": x_values,
                "values": y_values,
                "name": title,
                "hole": 0.42,
                "marker": {"colors": theme.palette[: len(x_values)]},
            }
        ]
        layout = _layout(title, theme_name=theme.name)
    elif chart_type == "table":
        data = [
            {
                "type": "table",
                "header": {"values": grouped.columns.tolist()},
                "cells": {"values": [grouped[col].astype(str).tolist() for col in grouped.columns]},
            }
        ]
        layout = _layout(title, theme_name=theme.name)
    else:
        chart_type = "bar"
        data = [
            {
                "type": "bar",
                "x": x_values,
                "y": y_values,
                "name": title,
                "marker": {"color": theme.palette[: len(x_values)]},
            }
        ]
        layout = _layout(title, dimension, value_column, theme.name)

    chart = _spec(
        f"visual_builder_{chart_type}_{dimension}_{value_column}",
        title,
        chart_type,
        "visual_builder",
        [col for col in [dimension, measure] if col],
        data,
        layout,
        {"aggregation": aggregation, "filtered_rows": int(len(df))},
        theme,
    )

    applied_spec = {
        "chart_type": chart_type,
        "dimension": dimension,
        "measure": measure,
        "aggregation": aggregation,
        "filters": spec.get("filters") or {},
    }
    return {
        "dataset_id": dataset_id,
        "chart": chart,
        "applied_spec": applied_spec,
        "suggestions": suggest_visual_types(applied_spec),
    }
