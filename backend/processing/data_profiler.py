from __future__ import annotations

import pandas as pd
from threading import Lock

_PROFILE_CACHE: dict[str, dict] = {}
_PROFILE_CACHE_LOCK = Lock()

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


def build_date_summary(df: pd.DataFrame, date_columns: list[str]) -> dict[str, dict[str, str | int | None]]:
    summary: dict[str, dict[str, str | int | None]] = {}
    for column in date_columns:
        series = pd.to_datetime(df[column], errors="coerce").dropna()
        summary[column] = {
            "count": int(series.count()),
            "min": series.min().date().isoformat() if series.count() else None,
            "max": series.max().date().isoformat() if series.count() else None,
            "unique_periods": int(series.dt.to_period("M").nunique()) if series.count() else 0,
        }
    return summary


def build_outlier_summary(df: pd.DataFrame, numeric_columns: list[str], limit: int = 8) -> list[dict]:
    outliers: list[dict] = []
    for column in numeric_columns:
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if len(series) < 8:
            continue
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        if pd.isna(iqr) or iqr == 0:
            continue
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        count = int(((series < lower) | (series > upper)).sum())
        if count:
            outliers.append(
                {
                    "column": column,
                    "method": "IQR",
                    "outlier_count": count,
                    "outlier_pct": to_json_safe(round(count / len(series) * 100, 2)),
                    "lower_bound": to_json_safe(round(float(lower), 4)),
                    "upper_bound": to_json_safe(round(float(upper), 4)),
                }
            )
    return sorted(outliers, key=lambda row: row["outlier_pct"], reverse=True)[:limit]


def build_correlation_summary(df: pd.DataFrame, numeric_columns: list[str], threshold: float = 0.6) -> list[dict]:
    usable = [column for column in numeric_columns if pd.to_numeric(df[column], errors="coerce").nunique(dropna=True) > 1]
    if len(usable) < 2:
        return []
    corr = df[usable].apply(pd.to_numeric, errors="coerce").corr()
    rows: list[dict] = []
    for left_index, left in enumerate(corr.columns):
        for right in corr.columns[left_index + 1 :]:
            value = corr.loc[left, right]
            if pd.notna(value) and abs(float(value)) >= threshold:
                rows.append(
                    {
                        "column_a": left,
                        "column_b": right,
                        "correlation": to_json_safe(round(float(value), 4)),
                        "strength": "strong" if abs(float(value)) >= 0.8 else "moderate",
                        "direction": "positive" if value > 0 else "negative",
                        "caution": "Correlation is not causation; use this as a relationship signal only.",
                    }
                )
    return sorted(rows, key=lambda row: abs(row["correlation"]), reverse=True)[:10]


def build_trend_summary(df: pd.DataFrame, date_columns: list[str], numeric_columns: list[str]) -> list[dict]:
    if not date_columns or not numeric_columns:
        return []
    date_column = date_columns[0]
    rows: list[dict] = []
    for metric in numeric_columns[:5]:
        work = df[[date_column, metric]].copy()
        work[date_column] = pd.to_datetime(work[date_column], errors="coerce")
        work[metric] = pd.to_numeric(work[metric], errors="coerce")
        work = work.dropna()
        if len(work) < 4:
            continue
        work["period"] = work[date_column].dt.to_period("M").astype(str)
        grouped = work.groupby("period")[metric].mean()
        if len(grouped) < 2:
            continue
        first = float(grouped.iloc[0])
        last = float(grouped.iloc[-1])
        change_pct = None if first == 0 else round((last - first) / abs(first) * 100, 2)
        rows.append(
            {
                "date_column": date_column,
                "metric": metric,
                "periods": int(len(grouped)),
                "first_period": str(grouped.index[0]),
                "last_period": str(grouped.index[-1]),
                "first_value": to_json_safe(round(first, 4)),
                "last_value": to_json_safe(round(last, 4)),
                "change_pct": to_json_safe(change_pct),
                "direction": "increased" if change_pct and change_pct > 0 else "decreased" if change_pct and change_pct < 0 else "stable",
            }
        )
    return rows


def build_quality_score(row_count: int, column_count: int, missing_total: int, duplicate_rows: int) -> dict:
    total_cells = max(row_count * column_count, 1)
    completeness_pct = round((1 - missing_total / total_cells) * 100, 2)
    duplicate_pct = round(duplicate_rows / max(row_count, 1) * 100, 2)
    score = max(0.0, min(100.0, completeness_pct - min(25.0, duplicate_pct * 2)))
    grade = "A" if score >= 95 else "B" if score >= 85 else "C" if score >= 70 else "D"
    return {
        "score": to_json_safe(round(score, 2)),
        "grade": grade,
        "completeness_pct": completeness_pct,
        "duplicate_pct": duplicate_pct,
        "explanation": "Score is based on cell completeness with a duplicate-row penalty.",
    }


def profile_dataframe(df: pd.DataFrame) -> dict:
    """Return a compact but useful dataset profile."""
    cache_key = df.attrs.get("_dataset_cache_key")
    if cache_key:
        with _PROFILE_CACHE_LOCK:
            cached = _PROFILE_CACHE.get(cache_key)
        if cached is not None:
            return cached
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
        "date_summary": build_date_summary(df, column_types["date_columns"]),
        "outlier_summary": build_outlier_summary(df, column_types["numeric_columns"]),
        "correlation_summary": build_correlation_summary(df, column_types["numeric_columns"]),
        "trend_summary": build_trend_summary(df, column_types["date_columns"], column_types["numeric_columns"]),
    }
    result["data_quality_score"] = build_quality_score(
        result["row_count"],
        result["column_count"],
        result["total_missing_values"],
        result["duplicate_rows"],
    )

    safe_result = safe_dict(result)
    if cache_key:
        with _PROFILE_CACHE_LOCK:
            if len(_PROFILE_CACHE) >= 16:
                _PROFILE_CACHE.pop(next(iter(_PROFILE_CACHE)))
            _PROFILE_CACHE[cache_key] = safe_result
    return safe_result
