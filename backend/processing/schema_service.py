from __future__ import annotations

from typing import Any

import pandas as pd

from backend.processing.column_detector import detect_column_types


def _semantic_type(column: str, column_types: dict[str, list[str]]) -> str:
    if column in column_types["numeric_columns"]:
        return "numeric"
    if column in column_types["date_columns"]:
        return "datetime"
    if column in column_types["boolean_columns"]:
        return "boolean"
    if column in column_types["categorical_columns"]:
        return "categorical"
    return "text"


def build_column_schema(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Build a compact column schema for downstream analytics services."""
    column_types = detect_column_types(df)
    schema: list[dict[str, Any]] = []

    for column in df.columns:
        series = df[column]
        samples = [
            None if pd.isna(value) else str(value)
            for value in series.dropna().head(5).tolist()
        ]
        schema.append(
            {
                "name": column,
                "dtype": str(series.dtype),
                "semantic_type": _semantic_type(column, column_types),
                "missing_count": int(series.isna().sum()),
                "unique_count": int(series.nunique(dropna=True)),
                "sample_values": samples,
            }
        )

    return schema


def build_column_groups(df: pd.DataFrame) -> dict[str, list[str]]:
    column_types = detect_column_types(df)
    return {
        "numeric": column_types["numeric_columns"],
        "categorical": column_types["categorical_columns"],
        "datetime": column_types["date_columns"],
        "boolean": column_types["boolean_columns"],
    }
