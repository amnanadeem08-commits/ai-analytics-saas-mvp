from __future__ import annotations

import pandas as pd

from backend.processing.column_detector import detect_column_types
from backend.processing.data_profiler import profile_dataframe
from backend.utils.response_utils import safe_dict, to_json_safe


def build_summary(df: pd.DataFrame) -> dict:
    """Main analytics summary used by the API."""
    return profile_dataframe(df)


def build_dashboard_stats(df: pd.DataFrame) -> dict:
    """Create simple chart-ready dashboard stats for Streamlit."""
    column_types = detect_column_types(df)
    numeric_columns = column_types["numeric_columns"]
    categorical_columns = column_types["categorical_columns"]
    date_columns = column_types["date_columns"]

    top_categories: dict[str, list[dict]] = {}
    for column in categorical_columns[:5]:
        counts = df[column].value_counts(dropna=False).head(10)
        top_categories[column] = [
            {"label": None if pd.isna(index) else str(index), "value": int(value)}
            for index, value in counts.items()
        ]

    correlations: dict[str, dict[str, float | None]] = {}
    if len(numeric_columns) >= 2:
        correlations = df[numeric_columns].corr(numeric_only=True).round(4).to_dict()

    time_trends: dict[str, list[dict]] = {}
    if date_columns and numeric_columns:
        date_column = date_columns[0]
        parsed_dates = pd.to_datetime(df[date_column], errors="coerce")
        trend_df = df.copy()
        trend_df[date_column] = parsed_dates
        trend_df = trend_df.dropna(subset=[date_column])

        if not trend_df.empty:
            trend_df["period"] = trend_df[date_column].dt.to_period("M").astype(str)
            for numeric_column in numeric_columns[:3]:
                grouped = trend_df.groupby("period")[numeric_column].sum().reset_index()
                time_trends[numeric_column] = [
                    {"period": row["period"], "value": to_json_safe(row[numeric_column])}
                    for _, row in grouped.iterrows()
                ]

    return safe_dict(
        {
            "column_types": column_types,
            "top_categories": top_categories,
            "correlations": correlations,
            "time_trends": time_trends,
        }
    )
