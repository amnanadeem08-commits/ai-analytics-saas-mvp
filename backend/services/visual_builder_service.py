from __future__ import annotations

from functools import lru_cache

from typing import Any

import pandas as pd

from backend.core.theme_manager import theme_manager
from backend.processing.schema_service import build_column_schema
from backend.services.chart_service import _layout, _spec
from backend.services.dataset_service import load_dataset_dataframe
from backend.services.filter_service import apply_filters, build_filter_options
from backend.services.metric_suitability_service import metric_suitability
from backend.utils.response_utils import to_json_safe


BUSINESS_DIMENSION_KEYWORDS = [
    "country",
    "gender",
    "category",
    "segment",
    "platform",
    "region",
    "product",
    "city",
    "state",
    "channel",
    "department",
    "status",
]
GEO_KEYWORDS = ["country", "state", "province", "region", "city", "territory", "postal", "zip", "latitude", "longitude"]
CURRENCY_KEYWORDS = ["revenue", "sales", "amount", "profit", "cost", "price", "value", "spend", "income"]
PERCENTAGE_KEYWORDS = ["rate", "ratio", "percent", "percentage", "pct", "margin", "churn_risk", "risk_score"]
TARGET_RISK_KEYWORDS = ["target", "risk", "churn", "fraud", "outcome", "label", "score"]


def _display_label(column_name: str) -> str:
    return column_name.replace("_", " ").replace("-", " ").title()


def _normalized(column_name: str) -> str:
    return column_name.lower().replace("-", "_").replace(" ", "_")


def _semantic_role(column: dict[str, Any], row_count: int) -> tuple[str, int, str]:
    name = column["name"]
    text = _normalized(name)
    unique_count = int(column.get("unique_count", 0))
    unique_ratio = unique_count / max(row_count, 1)
    semantic_type = column.get("semantic_type", "")

    if semantic_type == "datetime" or "date" in text or "month" in text:
        return "date_column", 95, ""
    if any(keyword in text for keyword in GEO_KEYWORDS):
        return "geography_column", 92, ""
    if text == "id" or text.endswith("_id") or text.endswith("id") or (unique_ratio > 0.9 and unique_count > 20):
        return (
            "id_column",
            5,
            f"{name} looks like an ID column and may not be useful as a chart axis. Try country, category, gender, segment, or date instead.",
        )
    if any(keyword in text for keyword in CURRENCY_KEYWORDS):
        return "revenue_currency_column", 96, ""
    if any(keyword in text for keyword in PERCENTAGE_KEYWORDS):
        return "percentage_ratio_column", 88, ""
    if any(keyword in text for keyword in TARGET_RISK_KEYWORDS):
        return "target_risk_column", 84, ""
    if any(keyword in text for keyword in BUSINESS_DIMENSION_KEYWORDS):
        return "category_column", 90, ""
    if semantic_type == "numeric":
        return "measure_column", 70, ""
    if semantic_type in {"categorical", "boolean", "text"}:
        return "dimension_column", 65, ""
    return "dimension_column", 40, ""


def _field(column: dict[str, Any], role: str, row_count: int) -> dict[str, Any]:
    semantic_role, priority, helper_message = _semantic_role(column, row_count)
    return {
        "name": column["name"],
        "role": role,
        "dtype": column["dtype"],
        "semantic_type": column["semantic_type"],
        "unique_count": column["unique_count"],
        "sample_values": column["sample_values"],
        "semantic_role": semantic_role,
        "business_priority": priority,
        "helper_message": helper_message,
    }


def _pick_fields(fields: list[dict[str, Any]], roles: set[str]) -> list[dict[str, Any]]:
    return [field for field in fields if field.get("semantic_role") in roles]


def _recommendation(
    visual_id: str,
    title: str,
    business_meaning: str,
    chart_type: str,
    fields_used: list[str],
    reason: str,
    spec: dict[str, Any],
    insight: str,
) -> dict[str, Any]:
    return {
        "visual_id": visual_id,
        "title": title,
        "business_meaning": business_meaning,
        "suggested_chart_type": chart_type,
        "fields_used": fields_used,
        "why_useful": reason,
        "spec": spec,
        "short_ai_insight": insight,
    }


def build_visual_recommendations(schema: list[dict[str, Any]], row_count: int) -> list[dict[str, Any]]:
    fields = sorted(schema, key=lambda field: (-field.get("business_priority", 0), field.get("name", "")))
    dimensions = [field for field in fields if field.get("semantic_role") in {"category_column", "dimension_column", "geography_column"}]
    dates = _pick_fields(fields, {"date_column"})
    measures = [field for field in fields if field.get("semantic_role") in {"measure_column", "revenue_currency_column"}]
    money = _pick_fields(fields, {"revenue_currency_column"})
    ratios = _pick_fields(fields, {"percentage_ratio_column"})
    risks = _pick_fields(fields, {"target_risk_column", "percentage_ratio_column"})
    ids = _pick_fields(fields, {"id_column"})
    recommendations: list[dict[str, Any]] = []

    primary_measure = money[0] if money else (measures[0] if measures else None)
    primary_dimension = dimensions[0] if dimensions else None
    geo_dimension = next((field for field in dimensions if field.get("semantic_role") == "geography_column"), None)
    category_dimension = next((field for field in dimensions if field.get("semantic_role") == "category_column"), primary_dimension)
    date_dimension = dates[0] if dates else None
    risk_measure = risks[0] if risks else None

    recommendations.append(
        _recommendation(
            "kpi_total_records",
            "Total Records",
            "Shows dataset volume so users understand the reporting base.",
            "kpi",
            [],
            "A KPI card is best for one headline count.",
            {"chart_type": "table", "dimension": primary_dimension["name"] if primary_dimension else None, "measure": None, "aggregation": "count"},
            f"The uploaded dataset contains {row_count:,} records available for analysis.",
        )
    )

    if primary_measure:
        measure_name = primary_measure["name"]
        recommendations.append(
            _recommendation(
                f"kpi_{measure_name}",
                f"Total {_display_label(measure_name)}",
                f"Highlights the primary business outcome from {_display_label(measure_name)}.",
                "kpi",
                [measure_name],
                "KPI cards make important measures easy to scan for executives.",
                {
                    "chart_type": "table",
                    "dimension": primary_dimension["name"] if primary_dimension else None,
                    "measure": measure_name,
                    "aggregation": "sum",
                    "number_format": "Currency" if primary_measure["semantic_role"] == "revenue_currency_column" else "Decimal Number",
                },
                f"{_display_label(measure_name)} should anchor the dashboard before segment-level drivers.",
            )
        )
    if primary_measure and category_dimension:
        measure_name = primary_measure["name"]
        dim_name = category_dimension["name"]
        recommendations.append(
            _recommendation(
                f"{measure_name}_by_{dim_name}",
                f"{_display_label(measure_name)} by {_display_label(dim_name)}",
                "Compares business performance across major segments.",
                "bar",
                [dim_name, measure_name],
                "Bar charts are strongest for category comparison.",
                {
                    "chart_type": "bar",
                    "dimension": dim_name,
                    "measure": measure_name,
                    "aggregation": "sum",
                    "sort": "descending",
                    "number_format": "Currency" if primary_measure["semantic_role"] == "revenue_currency_column" else "Decimal Number",
                    "data_labels": True,
                },
                f"Use this to identify which {_display_label(dim_name).lower()} groups are driving {_display_label(measure_name).lower()}.",
            )
        )
    if primary_measure and geo_dimension:
        measure_name = primary_measure["name"]
        dim_name = geo_dimension["name"]
        recommendations.append(
            _recommendation(
                f"{measure_name}_by_{dim_name}",
                f"{_display_label(measure_name)} by {_display_label(dim_name)}",
                "Shows regional performance for market or territory decisions.",
                "horizontal_bar",
                [dim_name, measure_name],
                "Ranking regions horizontally improves label readability.",
                {
                    "chart_type": "horizontal_bar",
                    "dimension": dim_name,
                    "measure": measure_name,
                    "aggregation": "sum",
                    "sort": "descending",
                    "number_format": "Currency" if primary_measure["semantic_role"] == "revenue_currency_column" else "Decimal Number",
                    "data_labels": True,
                },
                f"Use this to spot top and bottom performing {_display_label(dim_name).lower()} markets.",
            )
        )
    if primary_measure and date_dimension:
        measure_name = primary_measure["name"]
        dim_name = date_dimension["name"]
        recommendations.append(
            _recommendation(
                f"{measure_name}_trend_{dim_name}",
                f"{_display_label(measure_name)} Trend by {_display_label(dim_name)}",
                "Tracks movement over time and supports executive trend review.",
                "line",
                [dim_name, measure_name],
                "Line charts are best for date/month trends.",
                {
                    "chart_type": "line",
                    "dimension": dim_name,
                    "measure": measure_name,
                    "aggregation": "sum",
                    "sort": "ascending",
                    "number_format": "Currency" if primary_measure["semantic_role"] == "revenue_currency_column" else "Decimal Number",
                    "data_labels": False,
                },
                f"Use this to see whether {_display_label(measure_name).lower()} is rising, falling, or flattening over time.",
            )
        )
    if risk_measure and primary_dimension:
        risk_name = risk_measure["name"]
        dim_name = primary_dimension["name"]
        recommendations.append(
            _recommendation(
                f"{risk_name}_by_{dim_name}",
                f"{_display_label(risk_name)} by {_display_label(dim_name)}",
                "Identifies segments where risk or churn pressure is concentrated.",
                "bar",
                [dim_name, risk_name],
                "Segmented bar charts make risk concentration easy to compare.",
                {
                    "chart_type": "bar",
                    "dimension": dim_name,
                    "measure": risk_name,
                    "aggregation": "mean",
                    "sort": "descending",
                    "number_format": "Percentage",
                    "data_labels": True,
                },
                f"Use this to prioritize high-risk {_display_label(dim_name).lower()} segments.",
            )
        )
    if primary_measure and ids:
        measure_name = primary_measure["name"]
        id_name = ids[0]["name"]
        recommendations.append(
            _recommendation(
                f"top_{id_name}_by_{measure_name}",
                f"Top {_display_label(id_name)} by {_display_label(measure_name)}",
                "Ranks the most valuable records, customers, or products for follow-up.",
                "horizontal_bar",
                [id_name, measure_name],
                "Top-N ranking works best as a horizontal bar when labels are long.",
                {
                    "chart_type": "horizontal_bar",
                    "dimension": id_name,
                    "measure": measure_name,
                    "aggregation": "sum",
                    "sort": "descending",
                    "number_format": "Currency" if primary_measure["semantic_role"] == "revenue_currency_column" else "Decimal Number",
                    "data_labels": True,
                },
                f"Use this to find the records contributing the most {_display_label(measure_name).lower()}.",
            )
        )
    if primary_measure and primary_dimension:
        recommendations.append(
            _recommendation(
                "matrix_comparison",
                "Detailed Comparison Matrix",
                "Gives analysts an exact-value table for deeper comparisons.",
                "table",
                [primary_dimension["name"], primary_measure["name"]],
                "Matrix/table visuals are best when exact values matter.",
                {
                    "chart_type": "table",
                    "dimension": primary_dimension["name"],
                    "measure": primary_measure["name"],
                    "aggregation": "sum",
                    "sort": "descending",
                },
                "Use this when stakeholders need the numbers behind the visual summary.",
            )
        )
    return recommendations[:10]


def build_slicer_recommendations(schema: list[dict[str, Any]], filters: dict[str, Any]) -> list[dict[str, Any]]:
    priority_roles = {
        "geography_column": 98,
        "category_column": 95,
        "date_column": 92,
        "target_risk_column": 88,
        "percentage_ratio_column": 80,
        "dimension_column": 75,
        "measure_column": 55,
        "revenue_currency_column": 55,
    }
    slicers: list[dict[str, Any]] = []
    for field in schema:
        name = field["name"]
        role = field.get("semantic_role", "")
        if role == "id_column" or name not in filters:
            continue
        filter_cfg = filters[name]
        filter_type = filter_cfg.get("type", "categorical")
        if filter_type == "date_range":
            slicer_type = "date_range"
            reason = "Date slicers let users focus the dashboard on a reporting period."
        elif filter_type == "numeric_range":
            slicer_type = "numeric_range"
            reason = "Numeric range slicers help isolate high or low value records."
        else:
            slicer_type = "category"
            reason = "Category slicers are useful for segment, market, product, and status filtering."
        slicers.append(
            {
                "field": name,
                "label": _display_label(name),
                "slicer_type": slicer_type,
                "semantic_role": role,
                "priority": priority_roles.get(role, 50),
                "reason": reason,
                "config": filter_cfg,
            }
        )
    return sorted(slicers, key=lambda item: (-item["priority"], item["field"]))[:8]


@lru_cache(maxsize=16)
def discover_visual_builder_schema(dataset_id: str) -> dict[str, Any]:
    df = load_dataset_dataframe(dataset_id)
    row_count = int(len(df))
    schema = build_column_schema(df)
    semantic_layer = [_field(col, "semantic", row_count) for col in schema]
    by_name = {field["name"]: field for field in semantic_layer}
    dimensions = [
        {**by_name[col["name"]], "role": "dimension"}
        for col in schema
        if col["semantic_type"] in {"categorical", "boolean", "text", "datetime"}
        or by_name[col["name"]]["semantic_role"] == "id_column"
    ]
    measures = [
        {**by_name[col["name"]], "role": "measure"}
        for col in schema
        if col["semantic_type"] == "numeric"
        and by_name[col["name"]]["semantic_role"] not in {"id_column"}
    ]
    dates = [{**by_name[col["name"]], "role": "date"} for col in schema if col["semantic_type"] == "datetime"]

    dimensions = sorted(dimensions, key=lambda field: (-field["business_priority"], field["name"]))
    measures = sorted(measures, key=lambda field: (-field["business_priority"], field["name"]))
    default_dimension = dimensions[0]["name"] if dimensions else None
    default_measure = measures[0]["name"] if measures else None

    filters = build_filter_options(df)
    return {
        "dataset_id": dataset_id,
        "dimensions": dimensions,
        "measures": measures,
        "dates": dates,
        "semantic_layer": sorted(semantic_layer, key=lambda field: (-field["business_priority"], field["name"])),
        "recommended_visuals": build_visual_recommendations(semantic_layer, row_count),
        "slicer_recommendations": build_slicer_recommendations(semantic_layer, filters),
        "filters": filters,
        "suggested_defaults": {
            "dimension": default_dimension,
            "measure": default_measure,
            "chart_type": "bar" if dimensions and measures else "table",
            "aggregation": "mean" if default_measure and by_name[default_measure]["semantic_role"] in {"percentage_ratio_column"} else "sum",
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


def _semantic_warnings(schema: dict[str, Any], spec: dict[str, Any]) -> list[str]:
    fields = {field["name"]: field for field in schema.get("semantic_layer", [])}
    warnings: list[str] = []
    dimension = spec.get("dimension")
    measure = spec.get("measure")
    if dimension and fields.get(dimension, {}).get("helper_message"):
        warnings.append(fields[dimension]["helper_message"])
    if measure and fields.get(measure, {}).get("semantic_role") == "id_column":
        warnings.append(f"{measure} looks like an ID column. Use Count of records instead of aggregating the ID value.")
    return warnings


def _aggregate(df: pd.DataFrame, dimension: str, measure: str | None, aggregation: str) -> pd.DataFrame:
    if not measure:
        grouped = df[dimension].value_counts(dropna=False).reset_index()
        grouped.columns = [dimension, "count"]
        return grouped

    agg = aggregation.lower()
    if agg == "auto":
        agg = "mean" if metric_suitability(measure, df[measure]).get("recommended_aggregation") == "average" else metric_suitability(measure, df[measure]).get("recommended_aggregation", "sum")
    if agg == "average":
        agg = "mean"
    if agg not in {"sum", "mean", "median", "count", "min", "max"}:
        agg = "sum"
    work = df[[dimension, measure]].copy()
    work[measure] = pd.to_numeric(work[measure], errors="coerce")
    grouped = getattr(work.groupby(dimension, dropna=False)[measure], agg)().reset_index()
    return grouped.sort_values(measure, ascending=False).head(25)


def _format_axis_label(name: str) -> str:
    return _display_label(name)


def _friendly_title(chart_type: str, dimension: str, measure: str | None, aggregation: str) -> str:
    if not measure:
        return f"Count by {_display_label(dimension)}"
    if chart_type == "line":
        return f"{_display_label(measure)} Trend by {_display_label(dimension)}"
    if chart_type == "horizontal_bar":
        return f"Top {_display_label(dimension)} by {_display_label(measure)}"
    if aggregation in {"mean", "average", "auto"}:
        return f"Average {_display_label(measure)} by {_display_label(dimension)}"
    if aggregation == "median":
        return f"Median {_display_label(measure)} by {_display_label(dimension)}"
    return f"{_display_label(measure)} by {_display_label(dimension)}"


def _apply_readability(layout: dict[str, Any], chart_type: str) -> dict[str, Any]:
    layout.setdefault("margin", {"l": 64, "r": 32, "t": 72, "b": 72})
    layout["margin"] = {**layout.get("margin", {}), "t": 76, "b": 82}
    if chart_type in {"bar", "line"}:
        layout.setdefault("xaxis", {})
        layout["xaxis"].update({"tickangle": -30, "automargin": True})
    if chart_type == "horizontal_bar":
        layout.setdefault("yaxis", {})
        layout["yaxis"].update({"automargin": True})
    layout["uniformtext"] = {"mode": "hide", "minsize": 10}
    return layout


def _insight_from_grouped(grouped: pd.DataFrame, dimension: str, value_column: str, title: str) -> str:
    if grouped.empty:
        return f"{title} has no available rows after filters."
    top = grouped.iloc[0]
    return f"{top[dimension]} leads this visual with {_display_label(value_column).lower()} of {to_json_safe(top[value_column])}."


def render_visual_builder_chart(dataset_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    theme = theme_manager.get_theme()
    df = apply_filters(load_dataset_dataframe(dataset_id), spec.get("filters") or {})
    schema = discover_visual_builder_schema(dataset_id)
    dimension = spec.get("dimension") or schema["suggested_defaults"].get("dimension")
    measure = spec.get("measure") or schema["suggested_defaults"].get("measure")
    chart_type = (spec.get("chart_type") or "bar").lower()
    aggregation = spec.get("aggregation") or "sum"
    sort = spec.get("sort") or "descending"
    custom_title = spec.get("title")
    data_labels = bool(spec.get("data_labels", True))

    if not dimension:
        raise ValueError("A dimension column is required to render a visual.")
    if dimension not in df.columns:
        raise ValueError(f"Unknown dimension column: {dimension}")
    if measure and measure not in df.columns:
        raise ValueError(f"Unknown measure column: {measure}")

    grouped = _aggregate(df, dimension, measure, aggregation)
    value_column = measure or "count"
    if chart_type == "line":
        grouped = grouped.sort_values(dimension, ascending=True)
    elif sort == "ascending":
        grouped = grouped.sort_values(value_column, ascending=True)
    elif sort == "descending":
        grouped = grouped.sort_values(value_column, ascending=False)
    x_values = grouped[dimension].astype(str).tolist()
    y_values = [to_json_safe(value) for value in grouped[value_column].tolist()]
    title = custom_title or _friendly_title(chart_type, dimension, measure, aggregation)

    if chart_type == "pie":
        if len(x_values) > 8:
            chart_type = "bar"
            data = [
                {
                    "type": "bar",
                    "x": x_values,
                    "y": y_values,
                    "text": y_values if data_labels else None,
                    "textposition": "auto",
                    "name": title,
                    "marker": {"color": theme.palette[: len(x_values)]},
                }
            ]
            layout = _layout(title, _format_axis_label(dimension), _format_axis_label(value_column), theme.name)
            layout = _apply_readability(layout, chart_type)
        else:
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
            layout = _apply_readability(layout, chart_type)
    elif chart_type == "table":
        data = [
            {
                "type": "table",
                "header": {"values": [_format_axis_label(col) for col in grouped.columns.tolist()]},
                "cells": {"values": [grouped[col].astype(str).tolist() for col in grouped.columns]},
            }
        ]
        layout = _layout(title, theme_name=theme.name)
        layout = _apply_readability(layout, chart_type)
    elif chart_type == "line":
        data = [
            {
                "type": "scatter",
                "mode": "lines+markers+text" if data_labels else "lines+markers",
                "x": x_values,
                "y": y_values,
                "text": y_values if data_labels else None,
                "name": title,
                "line": {"color": theme.primary},
                "marker": {"color": theme.primary},
            }
        ]
        layout = _layout(title, _format_axis_label(dimension), _format_axis_label(value_column), theme.name)
        layout = _apply_readability(layout, chart_type)
    elif chart_type == "horizontal_bar":
        data = [
            {
                "type": "bar",
                "orientation": "h",
                "x": y_values,
                "y": x_values,
                "text": y_values if data_labels else None,
                "textposition": "auto",
                "name": title,
                "marker": {"color": theme.palette[: len(x_values)]},
            }
        ]
        layout = _layout(title, _format_axis_label(value_column), _format_axis_label(dimension), theme.name)
        layout = _apply_readability(layout, chart_type)
    else:
        chart_type = "bar"
        data = [
            {
                "type": "bar",
                "x": x_values,
                "y": y_values,
                "text": y_values if data_labels else None,
                "textposition": "auto",
                "name": title,
                "marker": {"color": theme.palette[: len(x_values)]},
            }
        ]
        layout = _layout(title, _format_axis_label(dimension), _format_axis_label(value_column), theme.name)
        layout = _apply_readability(layout, chart_type)

    chart = _spec(
        f"visual_builder_{chart_type}_{dimension}_{value_column}",
        title,
        chart_type,
        "visual_builder",
        [col for col in [dimension, measure] if col],
        data,
        layout,
        {"aggregation": aggregation, "filtered_rows": int(len(df)), "short_ai_insight": _insight_from_grouped(grouped, dimension, value_column, title)},
        theme,
    )

    applied_spec = {
        "chart_type": chart_type,
        "dimension": dimension,
        "measure": measure,
        "aggregation": aggregation,
        "sort": sort,
        "legend": spec.get("legend"),
        "tooltip": spec.get("tooltip"),
        "number_format": spec.get("number_format", "Auto"),
        "title": custom_title,
        "data_labels": data_labels,
        "filters": spec.get("filters") or {},
    }
    return {
        "dataset_id": dataset_id,
        "chart": chart,
        "applied_spec": applied_spec,
        "suggestions": suggest_visual_types(applied_spec),
        "semantic_warnings": _semantic_warnings(schema, applied_spec),
    }
