from __future__ import annotations

from threading import Lock

import pandas as pd


DATE_PARSE_THRESHOLD = 0.7
CATEGORY_UNIQUE_RATIO = 0.5
MAX_CATEGORY_UNIQUE_VALUES = 50
_TYPE_CACHE: dict[str, dict[str, list[str]]] = {}
_TYPE_CACHE_LOCK = Lock()


def detect_date_columns(df: pd.DataFrame) -> list[str]:
    """Detect date-like columns from a bounded representative sample."""
    date_columns: list[str] = []
    for column in df.columns:
        series = df[column].dropna()
        if series.empty:
            continue
        if pd.api.types.is_datetime64_any_dtype(series):
            date_columns.append(column)
            continue
        if not pd.api.types.is_object_dtype(series) and not isinstance(series.dtype, pd.StringDtype):
            continue
        sample = series.iloc[:10_000]
        parsed = pd.to_datetime(sample, errors="coerce", utc=False, format="mixed")
        if parsed.notna().mean() >= DATE_PARSE_THRESHOLD:
            date_columns.append(column)
    return date_columns


def detect_column_types(df: pd.DataFrame) -> dict[str, list[str]]:
    """Classify columns, reusing results for immutable dataset-hash dataframes."""
    cache_key = df.attrs.get("_dataset_cache_key")
    if cache_key:
        with _TYPE_CACHE_LOCK:
            cached = _TYPE_CACHE.get(cache_key)
        if cached is not None:
            return cached

    date_columns = detect_date_columns(df)
    boolean_columns = [col for col in df.columns if pd.api.types.is_bool_dtype(df[col])]
    numeric_columns = [
        col for col in df.select_dtypes(include=["number"]).columns.tolist()
        if col not in date_columns and col not in boolean_columns
    ]
    categorical_columns: list[str] = []
    row_count = max(len(df), 1)
    for column in df.columns:
        if column in numeric_columns or column in date_columns or column in boolean_columns:
            continue
        unique_count = df[column].nunique(dropna=True)
        if unique_count <= MAX_CATEGORY_UNIQUE_VALUES or unique_count / row_count <= CATEGORY_UNIQUE_RATIO:
            categorical_columns.append(column)

    result = {
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "date_columns": date_columns,
        "boolean_columns": boolean_columns,
    }
    if cache_key:
        with _TYPE_CACHE_LOCK:
            if len(_TYPE_CACHE) >= 16:
                _TYPE_CACHE.pop(next(iter(_TYPE_CACHE)))
            _TYPE_CACHE[cache_key] = result
    return result