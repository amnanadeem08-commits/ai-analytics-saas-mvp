from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from backend.processing.data_profiler import profile_dataframe
from backend.services.analyst.intent_service import AnalystIntent
from backend.services.metric_suitability_service import aggregate_label, metric_suitability
from backend.utils.response_utils import to_json_safe


@dataclass(frozen=True)
class AnalystQueryResult:
    rows: list[dict[str, Any]]
    supporting_data: dict[str, Any]
    render_mode: str = "text"


def _number(value: Any) -> Any:
    return to_json_safe(value)


def execute_intent(df: pd.DataFrame, intent: AnalystIntent) -> AnalystQueryResult:
    profile = profile_dataframe(df)

    if intent.intent == "empty":
        return AnalystQueryResult([], {}, "empty")
    if intent.intent == "row_count":
        return AnalystQueryResult(
            [{"metric": "row_count", "value": int(len(df))}],
            {"row_count": int(len(df))},
            "metric",
        )
    if intent.intent == "column_count":
        columns = df.columns.tolist()
        return AnalystQueryResult(
            [{"metric": "column_count", "value": len(columns)}],
            {"column_count": len(columns), "columns": columns},
            "metric",
        )
    if intent.intent == "missing_values":
        return AnalystQueryResult(
            [
                {"column": column, "missing_values": int(count)}
                for column, count in profile["missing_values_by_column"].items()
            ],
            {"missing_values_by_column": profile["missing_values_by_column"]},
            "table",
        )
    if intent.intent == "duplicates":
        duplicates = int(df.duplicated().sum())
        return AnalystQueryResult(
            [{"metric": "duplicate_rows", "value": duplicates}],
            {"duplicate_rows": duplicates},
            "metric",
        )
    if intent.intent == "average":
        if intent.metric_column:
            value = pd.to_numeric(df[intent.metric_column], errors="coerce").mean()
            return AnalystQueryResult(
                [{"metric": intent.metric_column, "average": _number(value)}],
                {intent.metric_column: _number(value)},
                "metric",
            )
        averages = {
            column: _number(pd.to_numeric(df[column], errors="coerce").mean())
            for column in profile["column_types"]["numeric_columns"]
        }
        return AnalystQueryResult(
            [{"metric": column, "average": value} for column, value in averages.items()],
            averages,
            "table",
        )
    if intent.intent == "total":
        if intent.metric_column:
            value = pd.to_numeric(df[intent.metric_column], errors="coerce").sum()
            return AnalystQueryResult(
                [{"metric": intent.metric_column, "total": _number(value)}],
                {intent.metric_column: _number(value)},
                "metric",
            )
    if intent.intent == "grouped_total" and intent.metric_column and intent.dimension_column:
        suitability = metric_suitability(intent.metric_column, df[intent.metric_column])
        aggregation = suitability["recommended_aggregation"]
        groupby = df.groupby(intent.dimension_column, dropna=False)[intent.metric_column]
        grouped = (groupby.sum() if aggregation == "sum" else groupby.mean()).sort_values(ascending=False)
        rows = [
            {
                intent.dimension_column: str(index),
                intent.metric_column: _number(value),
                "aggregation": aggregation,
            }
            for index, value in grouped.items()
        ]
        return AnalystQueryResult(
            rows,
            {
                "aggregation": aggregation,
                "aggregation_label": aggregate_label(aggregation),
                "metric_suitability": suitability,
                "values": {row[intent.dimension_column]: row[intent.metric_column] for row in rows},
            },
            "ranked_table",
        )
    if intent.intent in {"top", "bottom"} and intent.metric_column:
        if intent.dimension_column:
            suitability = metric_suitability(intent.metric_column, df[intent.metric_column])
            aggregation = suitability["recommended_aggregation"]
            groupby = df.groupby(intent.dimension_column, dropna=False)[intent.metric_column]
            grouped = (groupby.sum() if aggregation == "sum" else groupby.mean()).sort_values(ascending=intent.intent == "bottom")
            if not grouped.empty:
                row = {
                    "dimension": intent.dimension_column,
                    "metric": intent.metric_column,
                    "label": str(grouped.index[0]),
                    "value": _number(grouped.iloc[0]),
                    "aggregation": aggregation,
                    "aggregation_label": aggregate_label(aggregation),
                    "metric_suitability": suitability,
                }
                return AnalystQueryResult([row], row, "ranked_table")
        series = pd.to_numeric(df[intent.metric_column], errors="coerce")
        value = series.min() if intent.intent == "bottom" else series.max()
        return AnalystQueryResult(
            [{"metric": intent.metric_column, "value": _number(value)}],
            {intent.metric_column: _number(value)},
            "metric",
        )
    if intent.intent == "summary":
        return AnalystQueryResult(
            [
                {"metric": "rows", "value": profile["row_count"]},
                {"metric": "columns", "value": profile["column_count"]},
                {"metric": "missing_values", "value": profile["total_missing_values"]},
                {"metric": "duplicates", "value": profile["duplicate_rows"]},
            ],
            profile,
            "summary",
        )

    return AnalystQueryResult(
        [],
        {
            "available_numeric_columns": profile["column_types"]["numeric_columns"],
            "available_categorical_columns": profile["column_types"]["categorical_columns"],
        },
        "unknown",
    )
