from __future__ import annotations

import pandas as pd


DATE_PARSE_THRESHOLD = 0.7
CATEGORY_UNIQUE_RATIO = 0.5
MAX_CATEGORY_UNIQUE_VALUES = 50


def detect_date_columns(df: pd.DataFrame) -> list[str]:
    """Detect date-like columns by checking parse success ratio."""
    date_columns: list[str] = []

    for column in df.columns:
        series = df[column].dropna()
        if series.empty:
            continue

        if pd.api.types.is_datetime64_any_dtype(series):
            date_columns.append(column)
            continue

        if not pd.api.types.is_object_dtype(series):
            continue

        parsed = pd.to_datetime(series, errors="coerce", utc=False, format="mixed")
        parse_ratio = parsed.notna().mean()
        if parse_ratio >= DATE_PARSE_THRESHOLD:
            date_columns.append(column)

    return date_columns


def detect_column_types(df: pd.DataFrame) -> dict[str, list[str]]:
    """Classify dataframe columns for analytics and UI rendering."""
    date_columns = detect_date_columns(df)
    boolean_columns = [col for col in df.columns if pd.api.types.is_bool_dtype(df[col])]

    numeric_columns = [
        col for col in df.select_dtypes(include=["number"]).columns.tolist()
        if col not in date_columns and col not in boolean_columns
    ]

    categorical_columns: list[str] = []
    for column in df.columns:
        if column in numeric_columns or column in date_columns or column in boolean_columns:
            continue

        unique_count = df[column].nunique(dropna=True)
        row_count = max(len(df), 1)
        unique_ratio = unique_count / row_count

        if unique_count <= MAX_CATEGORY_UNIQUE_VALUES or unique_ratio <= CATEGORY_UNIQUE_RATIO:
            categorical_columns.append(column)

    return {
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "date_columns": date_columns,
        "boolean_columns": boolean_columns,
    }
