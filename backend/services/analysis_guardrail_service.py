from __future__ import annotations

from typing import Any

import pandas as pd

from backend.processing.column_detector import detect_column_types


def build_analysis_guardrails(df: pd.DataFrame) -> dict[str, Any]:
    column_types = detect_column_types(df)
    numeric = column_types["numeric_columns"]
    categorical = column_types["categorical_columns"]
    dates = column_types["date_columns"]
    boolean = column_types["boolean_columns"]
    supports = {
        "kpi_tracking": bool(numeric),
        "trend_analysis": bool(dates and numeric),
        "comparison_analysis": bool((categorical or boolean) and numeric),
        "segmentation_analysis": bool(categorical or boolean),
        "root_cause_analysis": bool(numeric and (categorical or boolean)),
        "distribution_analysis": bool(numeric),
        "time_intelligence": bool(dates and numeric),
        "geographic_analysis": any(
            hint in str(column).lower()
            for column in df.columns
            for hint in ["country", "state", "province", "region", "city", "territory", "postal", "latitude", "longitude"]
        ),
    }
    invalid_methods = []
    if not supports["time_intelligence"]:
        invalid_methods.append("Do not generate YTD, MoM, YoY, rolling-period, or Date-table measures without a date/time field.")
    if not numeric:
        invalid_methods.append("Do not generate SUM, AVG, variance, or KPI tracking for text-only datasets.")
    if not categorical and not boolean:
        invalid_methods.append("Do not claim segment drivers unless grouping fields exist.")
    return {
        "field_types": {
            "numeric": numeric,
            "categorical": categorical,
            "date_time": dates,
            "boolean": boolean,
        },
        "supports": supports,
        "invalid_methods": invalid_methods,
        "visual_guidance": {
            "kpi_cards": supports["kpi_tracking"],
            "line_charts": supports["trend_analysis"],
            "bar_charts": supports["comparison_analysis"] or bool(categorical),
            "histograms": supports["distribution_analysis"],
            "maps": supports["geographic_analysis"],
        },
        "summary": "Analysis options are constrained by detected field types; unsupported methods are hidden or corrected before output.",
    }
