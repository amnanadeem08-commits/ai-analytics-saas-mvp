from __future__ import annotations

from typing import Any

import pandas as pd

from backend.processing.column_detector import detect_column_types
from backend.utils.response_utils import to_json_safe


def build_filter_options(df: pd.DataFrame) -> dict[str, Any]:
    column_types = detect_column_types(df)
    filters: dict[str, Any] = {}

    for column in column_types["categorical_columns"] + column_types["boolean_columns"]:
        values = df[column].dropna().astype(str).sort_values().unique().tolist()
        filters[column] = {"type": "categorical", "values": values[:100]}

    for column in column_types["date_columns"]:
        parsed = pd.to_datetime(df[column], errors="coerce").dropna()
        filters[column] = {
            "type": "date_range",
            "min": parsed.min().date().isoformat() if not parsed.empty else None,
            "max": parsed.max().date().isoformat() if not parsed.empty else None,
        }

    for column in column_types["numeric_columns"]:
        numeric = pd.to_numeric(df[column], errors="coerce").dropna()
        filters[column] = {
            "type": "numeric_range",
            "min": to_json_safe(numeric.min()) if not numeric.empty else None,
            "max": to_json_safe(numeric.max()) if not numeric.empty else None,
        }

    return filters


def apply_filters(df: pd.DataFrame, filters: dict[str, Any] | None) -> pd.DataFrame:
    if not filters:
        return df

    filtered = df.copy()
    filtered.attrs.pop("_dataset_cache_key", None)
    for column, criteria in filters.items():
        if column not in filtered.columns:
            continue
        if not isinstance(criteria, dict):
            continue

        values = criteria.get("values")
        if values:
            allowed = {str(value) for value in values}
            filtered = filtered[filtered[column].astype(str).isin(allowed)]
            continue

        min_value = criteria.get("min")
        max_value = criteria.get("max")
        if min_value is None and max_value is None:
            continue

        if pd.api.types.is_numeric_dtype(filtered[column]):
            series = pd.to_numeric(filtered[column], errors="coerce")
            if min_value is not None:
                filtered = filtered[series >= float(min_value)]
                series = pd.to_numeric(filtered[column], errors="coerce")
            if max_value is not None:
                filtered = filtered[series <= float(max_value)]
        else:
            series = pd.to_datetime(filtered[column], errors="coerce")
            if min_value is not None:
                filtered = filtered[series >= pd.to_datetime(min_value)]
                series = pd.to_datetime(filtered[column], errors="coerce")
            if max_value is not None:
                filtered = filtered[series <= pd.to_datetime(max_value)]

    return filtered
