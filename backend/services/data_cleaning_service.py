from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backend.models.dataset_models import CleaningOptions
from backend.processing.data_cleaner import normalize_column_name, make_unique_columns
from backend.services.dataset_service import load_dataset_dataframe


def _safe_completeness(df: pd.DataFrame) -> float:
    total = max(int(df.shape[0] * df.shape[1]), 1)
    missing = int(df.isna().sum().sum())
    return round((1 - missing / total) * 100, 2)


def _save_cleaned_outputs(dataset_id: str, cleaned: pd.DataFrame, datasets_dir: Path) -> tuple[str, str]:
    target_dir = datasets_dir / dataset_id / "cleaned"
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    csv_name = f"{dataset_id}_cleaned_{stamp}.csv"
    xlsx_name = f"{dataset_id}_cleaned_{stamp}.xlsx"
    cleaned.to_csv(target_dir / csv_name, index=False)
    cleaned.to_excel(target_dir / xlsx_name, index=False)
    return csv_name, xlsx_name


def clean_dataset(dataset_id: str, options: CleaningOptions, datasets_dir: Path) -> dict[str, Any]:
    original = load_dataset_dataframe(dataset_id).copy()
    cleaned = original.copy()
    changes: list[dict[str, Any]] = []
    outlier_flags: dict[str, int] = {}

    rows_before = int(len(cleaned))
    cols_before = int(len(cleaned.columns))
    completeness_before = _safe_completeness(cleaned)

    cleaned.columns = make_unique_columns([normalize_column_name(col) for col in cleaned.columns])

    empty_rows = int(cleaned.isna().all(axis=1).sum())
    empty_cols = int(cleaned.isna().all(axis=0).sum())
    if empty_rows:
        cleaned = cleaned.loc[~cleaned.isna().all(axis=1)]
    if empty_cols:
        cleaned = cleaned.loc[:, ~cleaned.isna().all(axis=0)]

    duplicates_before = int(cleaned.duplicated().sum())
    if duplicates_before:
        cleaned = cleaned.drop_duplicates(keep="first")

    object_cols = cleaned.select_dtypes(include=["object"]).columns.tolist()
    datetime_cols = cleaned.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()
    numeric_cols = cleaned.select_dtypes(include=["number"]).columns.tolist()

    for col in object_cols:
        cleaned[col] = cleaned[col].map(lambda v: v.strip() if isinstance(v, str) else v)
        if options.normalize_casing == "lower":
            cleaned[col] = cleaned[col].map(lambda v: v.lower() if isinstance(v, str) else v)
        elif options.normalize_casing == "upper":
            cleaned[col] = cleaned[col].map(lambda v: v.upper() if isinstance(v, str) else v)
        elif options.normalize_casing == "title":
            cleaned[col] = cleaned[col].map(lambda v: v.title() if isinstance(v, str) else v)

    inferred_datetime = []
    for col in cleaned.columns:
        if col in numeric_cols or col in datetime_cols:
            continue
        parsed = pd.to_datetime(cleaned[col], errors="coerce")
        if parsed.notna().mean() >= 0.7:
            cleaned[col] = parsed.dt.strftime("%Y-%m-%d")
            inferred_datetime.append(col)
    datetime_cols = sorted(set(datetime_cols + inferred_datetime))

    high_missing_columns: list[str] = []
    for col in cleaned.columns:
        missing_rate = float(cleaned[col].isna().mean())
        if missing_rate > options.high_missing_unknown_threshold:
            high_missing_columns.append(col)

    for col in numeric_cols:
        missing_count = int(cleaned[col].isna().sum())
        if not missing_count:
            continue
        if options.numeric_missing_strategy == "drop_rows":
            before = len(cleaned)
            cleaned = cleaned.dropna(subset=[col])
            changes.append({"column": col, "action": "missing_values", "method": "drop_rows", "count": int(before - len(cleaned))})
            continue
        if options.numeric_missing_strategy == "mean":
            fill_value = float(pd.to_numeric(cleaned[col], errors="coerce").mean())
        elif options.numeric_missing_strategy == "mode":
            mode = pd.to_numeric(cleaned[col], errors="coerce").mode(dropna=True)
            fill_value = float(mode.iloc[0]) if not mode.empty else 0.0
        else:
            fill_value = float(pd.to_numeric(cleaned[col], errors="coerce").median())
        cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce").fillna(fill_value)
        changes.append({"column": col, "action": "missing_values", "method": options.numeric_missing_strategy, "count": missing_count})

    for col in object_cols:
        missing_count = int(cleaned[col].isna().sum())
        if not missing_count:
            continue
        if options.categorical_missing_strategy == "drop_rows":
            before = len(cleaned)
            cleaned = cleaned.dropna(subset=[col])
            changes.append({"column": col, "action": "missing_values", "method": "drop_rows", "count": int(before - len(cleaned))})
            continue
        if options.categorical_missing_strategy == "unknown" or col in high_missing_columns:
            cleaned[col] = cleaned[col].fillna("Unknown")
            method = "unknown"
        else:
            mode = cleaned[col].mode(dropna=True)
            cleaned[col] = cleaned[col].fillna(mode.iloc[0] if not mode.empty else "Unknown")
            method = "mode"
        changes.append({"column": col, "action": "missing_values", "method": method, "count": missing_count})

    if options.datetime_missing_strategy in {"ffill", "bfill"}:
        for col in datetime_cols:
            missing_count = int(cleaned[col].isna().sum())
            if not missing_count:
                continue
            cleaned[col] = pd.to_datetime(cleaned[col], errors="coerce")
            cleaned[col] = cleaned[col].ffill() if options.datetime_missing_strategy == "ffill" else cleaned[col].bfill()
            cleaned[col] = cleaned[col].dt.strftime("%Y-%m-%d")
            changes.append(
                {"column": col, "action": "missing_values", "method": options.datetime_missing_strategy, "count": missing_count}
            )

    for col in numeric_cols:
        series = pd.to_numeric(cleaned[col], errors="coerce")
        if series.dropna().empty:
            continue
        if options.outlier_method == "zscore":
            std = float(series.std()) or 1.0
            mean = float(series.mean())
            z = (series - mean) / std
            mask = z.abs() > options.outlier_zscore_threshold
            lower = float(series.quantile(0.01))
            upper = float(series.quantile(0.99))
        else:
            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1
            lower = q1 - (1.5 * iqr)
            upper = q3 + (1.5 * iqr)
            mask = (series < lower) | (series > upper)
        flagged = int(mask.sum())
        if not flagged:
            continue
        outlier_flags[col] = flagged
        if options.outlier_strategy == "cap":
            cleaned.loc[series < lower, col] = lower
            cleaned.loc[series > upper, col] = upper
            changes.append({"column": col, "action": "outliers", "method": "cap", "count": flagged})
        elif options.outlier_strategy == "remove":
            cleaned = cleaned.loc[~mask].copy()
            changes.append({"column": col, "action": "outliers", "method": "remove_rows", "count": flagged})

    csv_name, xlsx_name = _save_cleaned_outputs(dataset_id, cleaned, datasets_dir)
    completeness_after = _safe_completeness(cleaned)

    return {
        "dataset_id": dataset_id,
        "cleaned_filename_csv": csv_name,
        "cleaned_filename_xlsx": xlsx_name,
        "rows_before": rows_before,
        "rows_after": int(len(cleaned)),
        "columns_before": cols_before,
        "columns_after": int(len(cleaned.columns)),
        "duplicates_removed": duplicates_before,
        "fully_empty_rows_removed": empty_rows,
        "fully_empty_columns_removed": empty_cols,
        "completeness_before_pct": completeness_before,
        "completeness_after_pct": completeness_after,
        "high_missing_columns": high_missing_columns,
        "outlier_flags": outlier_flags,
        "changes": changes,
        "preview_rows": cleaned.head(20).replace({np.nan: None}).to_dict(orient="records"),
    }
