from __future__ import annotations

from typing import Any

from backend.services.analyst.intent_service import AnalystIntent
from backend.services.analyst.query_service import AnalystQueryResult


def _format_number(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def build_answer(question: str, intent: AnalystIntent, result: AnalystQueryResult) -> str:
    if intent.intent == "empty":
        return "Please ask a question about the dataset."
    if intent.intent == "row_count":
        return f"The dataset has {_format_number(result.supporting_data['row_count'])} rows."
    if intent.intent == "column_count":
        columns = result.supporting_data["columns"]
        return f"The dataset has {_format_number(len(columns))} columns: {', '.join(columns)}."
    if intent.intent == "missing_values":
        total = sum(result.supporting_data["missing_values_by_column"].values())
        if total == 0:
            return "No missing values were detected in the cleaned dataset."
        top = [
            f"{column}: {count}"
            for column, count in sorted(
                result.supporting_data["missing_values_by_column"].items(),
                key=lambda item: item[1],
                reverse=True,
            )
            if count > 0
        ][:5]
        return f"The dataset has {_format_number(total)} missing values. Top affected columns: {', '.join(top)}."
    if intent.intent == "duplicates":
        return f"The dataset has {_format_number(result.supporting_data['duplicate_rows'])} duplicate rows."
    if intent.intent == "average":
        if intent.metric_column:
            return f"The average {intent.metric_column} is {_format_number(result.supporting_data[intent.metric_column])}."
        return "Here are the averages for numeric columns: " + ", ".join(
            f"{column}: {_format_number(value)}" for column, value in result.supporting_data.items()
        )
    if intent.intent == "total":
        if intent.metric_column:
            return f"The total {intent.metric_column} is {_format_number(result.supporting_data[intent.metric_column])}."
    if intent.intent == "grouped_total" and intent.metric_column and intent.dimension_column:
        pairs = list(result.supporting_data.items())[:10]
        return f"Total {intent.metric_column} by {intent.dimension_column}: " + ", ".join(
            f"{key}: {_format_number(value)}" for key, value in pairs
        )
    if intent.intent in {"top", "bottom"} and result.rows:
        row = result.rows[0]
        label = "top" if intent.intent == "top" else "bottom"
        if "dimension" in row:
            return (
                f"The {label} {row['dimension']} by {row['metric']} is {row['label']} "
                f"with {_format_number(row['value'])}."
            )
        return f"The {label} {row['metric']} value is {_format_number(row['value'])}."
    if intent.intent == "summary":
        values = {row["metric"]: row["value"] for row in result.rows}
        return (
            f"Dataset summary: {_format_number(values['rows'])} rows, "
            f"{_format_number(values['columns'])} columns, "
            f"{_format_number(values['missing_values'])} missing values, "
            f"and {_format_number(values['duplicates'])} duplicate rows."
        )
    return (
        "I can answer dataset questions about row count, columns, missing values, duplicates, "
        "totals, averages, minimums, maximums, top categories, and summaries."
    )

