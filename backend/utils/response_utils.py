from __future__ import annotations

import math
from typing import Any

import pandas as pd


def to_json_safe(value: Any) -> Any:
    """Convert pandas/numpy values into JSON-safe native Python values."""
    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        value = value.item()

    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None

    return value


def dataframe_preview(df: pd.DataFrame, rows: int = 10) -> list[dict[str, Any]]:
    """Return a safe preview from a dataframe."""
    preview_df = df.head(rows).copy()
    preview_df = preview_df.where(pd.notnull(preview_df), None)
    records = preview_df.to_dict(orient="records")
    return [
        {column: to_json_safe(value) for column, value in row.items()}
        for row in records
    ]


def safe_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively convert values inside a dictionary to JSON-safe values."""
    output: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            output[key] = safe_dict(value)
        elif isinstance(value, list):
            output[key] = [safe_dict(v) if isinstance(v, dict) else to_json_safe(v) for v in value]
        else:
            output[key] = to_json_safe(value)
    return output
