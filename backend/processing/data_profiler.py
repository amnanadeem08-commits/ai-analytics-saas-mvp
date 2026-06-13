from __future__ import annotations

import pandas as pd

from backend.processing.column_detector import detect_column_types
from backend.utils.response_utils import safe_dict, to_json_safe


def build_numeric_summary(df: pd.DataFrame, numeric_columns: list[str]) -> dict[str, dict[str, float | int | None]]:
    summary: dict[str, dict[str, float | int | None]] = {}

    for column in numeric_columns:
        series = pd.to_numeric(df[column], errors="coerce")
        summary[column] = {
            "count": int(series.count()),
            "mean": to_json_safe(round(series.mean(), 4)) if series.count() else None,
            "median": to_json_safe(round(series.median(), 4)) if series.count() else None,
            "min": to_json_safe(series.min()) if series.count() else None,
            "max": to_json_safe(series.max()) if series.count() else None,
            "sum": to_json_safe(round(series.sum(), 4)) if series.count() else None,
            "std": to_json_safe(round(series.std(), 4)) if series.count() > 1 else None,
        }

    return summary


def build_categorical_summary(df: pd.DataFrame, categorical_columns: list[str], limit: int = 10) -> dict[str, list[dict[str, int | str | None]]]:
    summary: dict[str, list[dict[str, int | str | None]]] = {}

    for column in categorical_columns:
        counts = df[column].value_counts(dropna=False).head(limit)
        summary[column] = [
            {
                "value": None if pd.isna(value) else str(value),
                "count": int(count),
            }
            for value, count in counts.items()
        ]

    return summary


def profile_dataframe(df: pd.DataFrame) -> dict:
    """Return a compact but useful dataset profile."""
    column_types = detect_column_types(df)
    missing_by_column = {column: int(count) for column, count in df.isna().sum().items()}
    dtypes = {column: str(dtype) for column, dtype in df.dtypes.items()}

    result = {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "duplicate_rows": int(df.duplicated().sum()),
        "total_missing_values": int(df.isna().sum().sum()),
        "missing_values_by_column": missing_by_column,
        "dtypes": dtypes,
        "column_types": column_types,
        "numeric_summary": build_numeric_summary(df, column_types["numeric_columns"]),
        "categorical_summary": build_categorical_summary(df, column_types["categorical_columns"]),
    }

    return safe_dict(result)
