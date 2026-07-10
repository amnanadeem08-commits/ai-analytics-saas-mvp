from __future__ import annotations

from typing import Any

import pandas as pd

from backend.processing.data_profiler import profile_dataframe
from backend.processing.schema_service import build_column_groups, build_column_schema
from backend.utils.response_utils import dataframe_preview


def build_dataset_overview(
    df: pd.DataFrame,
    preview_rows: int = 10,
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the dataset profile used by dataset, dashboard, and insight layers."""
    profile = profile or profile_dataframe(df)
    total_cells = max(int(df.size), 1)
    missing_cells = int(profile["total_missing_values"])

    return {
        "row_count": profile["row_count"],
        "column_count": profile["column_count"],
        "columns": df.columns.tolist(),
        "column_schema": build_column_schema(df, profile["column_types"]),
        "column_groups": build_column_groups(df, profile["column_types"]),
        "missing_summary": {
            "total_missing_values": missing_cells,
            "missing_values_by_column": profile["missing_values_by_column"],
            "completeness_pct": round((1 - missing_cells / total_cells) * 100, 2),
        },
        "duplicate_rows": profile["duplicate_rows"],
        "dtypes": profile["dtypes"],
        "numeric_summary": profile["numeric_summary"],
        "categorical_summary": profile["categorical_summary"],
        "preview": dataframe_preview(df, rows=preview_rows),
    }
