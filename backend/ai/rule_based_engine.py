from __future__ import annotations

import re
from typing import Any

import pandas as pd

from backend.processing.column_detector import detect_column_types
from backend.processing.data_profiler import profile_dataframe
from backend.services.metric_suitability_service import aggregate_label, aggregate_series, metric_suitability
from backend.utils.response_utils import to_json_safe


def _format_number(value: Any) -> str:
    value = to_json_safe(value)
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _find_column(question: str, columns: list[str]) -> str | None:
    normalized_question = question.lower().replace("_", " ")

    # Prefer exact readable matches, e.g. "total sales" -> sales.
    for column in columns:
        readable = column.lower().replace("_", " ")
        if readable in normalized_question:
            return column

    # Then try token-level matching for singular words.
    tokens = set(re.findall(r"[a-zA-Z0-9]+", normalized_question))
    for column in columns:
        column_tokens = set(re.findall(r"[a-zA-Z0-9]+", column.lower().replace("_", " ")))
        if column_tokens and column_tokens.issubset(tokens):
            return column

    return None


def _top_missing_columns(profile: dict, limit: int = 3) -> list[tuple[str, int]]:
    items = profile["missing_values_by_column"].items()
    return sorted(items, key=lambda item: item[1], reverse=True)[:limit]


def generate_rule_based_insights(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Generate predictable, no-cost insights from the dataframe profile."""
    profile = profile_dataframe(df)
    column_types = profile["column_types"]
    numeric_columns = column_types["numeric_columns"]
    categorical_columns = column_types["categorical_columns"]

    insights: list[dict[str, Any]] = []

    insights.append(
        {
            "type": "overview",
            "title": "Dataset overview",
            "message": (
                f"This dataset contains {_format_number(profile['row_count'])} rows "
                f"and {_format_number(profile['column_count'])} columns."
            ),
            "severity": "info",
            "metadata": {
                "row_count": profile["row_count"],
                "column_count": profile["column_count"],
            },
        }
    )

    if profile["total_missing_values"] > 0:
        top_missing = _top_missing_columns(profile)
        top_missing_text = ", ".join(
            f"{column} ({count})" for column, count in top_missing if count > 0
        )
        insights.append(
            {
                "type": "data_quality",
                "title": "Missing values detected",
                "message": (
                    f"There are {_format_number(profile['total_missing_values'])} missing values. "
                    f"Most affected columns: {top_missing_text}."
                ),
                "severity": "warning",
                "metadata": {"missing_values_by_column": profile["missing_values_by_column"]},
            }
        )
    else:
        insights.append(
            {
                "type": "data_quality",
                "title": "No missing values found",
                "message": "No missing values were detected in the cleaned dataset.",
                "severity": "success",
                "metadata": {},
            }
        )

    if profile["duplicate_rows"] > 0:
        insights.append(
            {
                "type": "data_quality",
                "title": "Duplicate rows found",
                "message": f"The dataset contains {_format_number(profile['duplicate_rows'])} duplicate rows.",
                "severity": "warning",
                "metadata": {"duplicate_rows": profile["duplicate_rows"]},
            }
        )

    for column in numeric_columns[:3]:
        summary = profile["numeric_summary"].get(column, {})
        suitability = metric_suitability(column, df[column])
        preferred_aggregation = suitability["recommended_aggregation"]
        preferred_label = aggregate_label(preferred_aggregation)
        preferred_value = aggregate_series(df[column], preferred_aggregation) if suitability["is_valid_metric"] else None
        insights.append(
            {
                "type": "metric",
                "title": f"{column.replace('_', ' ').title()} summary",
                "message": (
                    f"{column} has {preferred_label} {_format_number(round(preferred_value, 4) if preferred_value is not None else None)}, "
                    f"average {_format_number(summary.get('mean'))}, "
                    f"minimum {_format_number(summary.get('min'))}, "
                    f"and maximum {_format_number(summary.get('max'))}. "
                    f"Metric suitability: {suitability['reason']}"
                ),
                "severity": "info",
                "metadata": {"metric_suitability": suitability, **summary},
            }
        )

    if categorical_columns and numeric_columns:
        category_column = categorical_columns[0]
        metric_column = numeric_columns[0]
        suitability = metric_suitability(metric_column, df[metric_column])
        aggregation = suitability["recommended_aggregation"]
        groupby = df.groupby(category_column, dropna=False)[metric_column]
        grouped = (groupby.sum() if aggregation == "sum" else groupby.mean()).sort_values(ascending=False).head(1)
        if not grouped.empty:
            top_label = grouped.index[0]
            top_value = grouped.iloc[0]
            insights.append(
                {
                    "type": "performance",
                    "title": f"Top {category_column.replace('_', ' ')} by {aggregate_label(aggregation)} {metric_column}",
                    "message": (
                        f"{top_label} has the highest {aggregate_label(aggregation)} {metric_column} "
                        f"across {category_column}, with {_format_number(top_value)}. "
                        f"{suitability['reason']}"
                    ),
                    "severity": "success",
                    "metadata": {
                        "category_column": category_column,
                        "metric_column": metric_column,
                        "aggregation": aggregation,
                        "metric_suitability": suitability,
                        "top_label": str(top_label),
                        "top_value": to_json_safe(top_value),
                    },
                }
            )

    return insights


def answer_question(df: pd.DataFrame, question: str) -> dict[str, Any]:
    """Answer simple natural-language questions using deterministic Pandas logic."""
    question = question.strip()
    q = question.lower()

    profile = profile_dataframe(df)
    column_types = detect_column_types(df)
    numeric_columns = column_types["numeric_columns"]
    categorical_columns = column_types["categorical_columns"]
    all_columns = df.columns.tolist()

    if not question:
        return {
            "answer": "Please ask a question about the dataset.",
            "supporting_data": {},
        }

    if any(word in q for word in ["how many rows", "row count", "records", "entries"]):
        return {
            "answer": f"The dataset has {_format_number(len(df))} rows.",
            "supporting_data": {"row_count": int(len(df))},
        }

    if any(word in q for word in ["how many columns", "column count", "fields"]):
        return {
            "answer": f"The dataset has {_format_number(len(df.columns))} columns: {', '.join(all_columns)}.",
            "supporting_data": {"column_count": int(len(df.columns)), "columns": all_columns},
        }

    if "missing" in q or "null" in q or "empty" in q:
        total_missing = profile["total_missing_values"]
        if total_missing == 0:
            answer = "No missing values were detected in the cleaned dataset."
        else:
            top_missing = _top_missing_columns(profile, limit=5)
            top_text = ", ".join(f"{column}: {count}" for column, count in top_missing if count > 0)
            answer = f"The dataset has {_format_number(total_missing)} missing values. Top affected columns: {top_text}."
        return {
            "answer": answer,
            "supporting_data": {"missing_values_by_column": profile["missing_values_by_column"]},
        }

    if "duplicate" in q:
        duplicates = int(df.duplicated().sum())
        return {
            "answer": f"The dataset has {_format_number(duplicates)} duplicate rows.",
            "supporting_data": {"duplicate_rows": duplicates},
        }

    metric_column = _find_column(q, numeric_columns)
    category_column = _find_column(q, categorical_columns)

    if any(word in q for word in ["average", "mean"]):
        if metric_column:
            value = pd.to_numeric(df[metric_column], errors="coerce").mean()
            return {
                "answer": f"The average {metric_column} is {_format_number(value)}.",
                "supporting_data": {metric_column: to_json_safe(value)},
            }
        averages = {
            column: to_json_safe(pd.to_numeric(df[column], errors="coerce").mean())
            for column in numeric_columns
        }
        return {
            "answer": "Here are the averages for numeric columns: " + ", ".join(
                f"{col}: {_format_number(val)}" for col, val in averages.items()
            ),
            "supporting_data": averages,
        }

    if any(word in q for word in ["total", "sum"]):
        if metric_column and category_column:
            grouped = (
                df.groupby(category_column, dropna=False)[metric_column]
                .sum()
                .sort_values(ascending=False)
            )
            values = {str(index): to_json_safe(value) for index, value in grouped.items()}
            return {
                "answer": f"Total {metric_column} by {category_column}: " + ", ".join(
                    f"{key}: {_format_number(value)}" for key, value in list(values.items())[:10]
                ),
                "supporting_data": values,
            }
        if metric_column:
            value = pd.to_numeric(df[metric_column], errors="coerce").sum()
            return {
                "answer": f"The total {metric_column} is {_format_number(value)}.",
                "supporting_data": {metric_column: to_json_safe(value)},
            }

    if any(word in q for word in ["highest", "maximum", "max", "top"]):
        metric_column = metric_column or (numeric_columns[0] if numeric_columns else None)
        if metric_column and category_column:
            grouped = (
                df.groupby(category_column, dropna=False)[metric_column]
                .sum()
                .sort_values(ascending=False)
            )
            if not grouped.empty:
                return {
                    "answer": (
                        f"The top {category_column} by {metric_column} is {grouped.index[0]} "
                        f"with {_format_number(grouped.iloc[0])}."
                    ),
                    "supporting_data": {
                        "category_column": category_column,
                        "metric_column": metric_column,
                        "top_label": str(grouped.index[0]),
                        "top_value": to_json_safe(grouped.iloc[0]),
                    },
                }
        if metric_column:
            value = pd.to_numeric(df[metric_column], errors="coerce").max()
            return {
                "answer": f"The maximum {metric_column} is {_format_number(value)}.",
                "supporting_data": {metric_column: to_json_safe(value)},
            }

    if any(word in q for word in ["lowest", "minimum", "min"]):
        metric_column = metric_column or (numeric_columns[0] if numeric_columns else None)
        if metric_column:
            value = pd.to_numeric(df[metric_column], errors="coerce").min()
            return {
                "answer": f"The minimum {metric_column} is {_format_number(value)}.",
                "supporting_data": {metric_column: to_json_safe(value)},
            }

    if "insight" in q or "summary" in q or "analyze" in q:
        insights = generate_rule_based_insights(df)[:5]
        return {
            "answer": "Key insights: " + " ".join(insight["message"] for insight in insights),
            "supporting_data": {"insights": insights},
        }

    return {
        "answer": (
            "I can answer basic dataset questions about row count, columns, missing values, "
            "duplicates, totals, averages, minimums, maximums, and top categories. "
            "Try: 'Which product has the highest sales?' or 'What is the average profit?'"
        ),
        "supporting_data": {
            "available_numeric_columns": numeric_columns,
            "available_categorical_columns": categorical_columns,
        },
    }
