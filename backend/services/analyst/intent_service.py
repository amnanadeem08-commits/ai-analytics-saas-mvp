from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from backend.processing.column_detector import detect_column_types


@dataclass(frozen=True)
class AnalystIntent:
    intent: str
    metric_column: str | None = None
    dimension_column: str | None = None
    confidence: float = 0.5


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9]+", text.lower().replace("_", " ")))


def _find_column(question: str, columns: list[str]) -> str | None:
    normalized = question.lower().replace("_", " ")
    for column in columns:
        readable = column.lower().replace("_", " ")
        if readable in normalized:
            return column

    question_tokens = _tokens(normalized)
    for column in columns:
        column_tokens = _tokens(column)
        if column_tokens and column_tokens.issubset(question_tokens):
            return column
    return None


def detect_intent(question: str, df: pd.DataFrame) -> AnalystIntent:
    q = question.strip().lower()
    column_types = detect_column_types(df)
    numeric_columns = column_types["numeric_columns"]
    categorical_columns = column_types["categorical_columns"]
    metric = _find_column(q, numeric_columns)
    dimension = _find_column(q, categorical_columns)

    if not q:
        return AnalystIntent("empty", confidence=1.0)
    if any(phrase in q for phrase in ("how many rows", "row count", "records", "entries")):
        return AnalystIntent("row_count", confidence=0.95)
    if any(phrase in q for phrase in ("how many columns", "column count", "fields")):
        return AnalystIntent("column_count", confidence=0.95)
    if any(word in q for word in ("missing", "null", "empty")):
        return AnalystIntent("missing_values", confidence=0.9)
    if "duplicate" in q:
        return AnalystIntent("duplicates", confidence=0.9)
    if any(word in q for word in ("average", "mean")):
        return AnalystIntent("average", metric_column=metric, confidence=0.85 if metric else 0.7)
    if any(word in q for word in ("total", "sum")):
        intent = "grouped_total" if metric and dimension else "total"
        return AnalystIntent(intent, metric_column=metric, dimension_column=dimension, confidence=0.85)
    if any(word in q for word in ("highest", "maximum", "max", "top", "best")):
        return AnalystIntent(
            "top",
            metric_column=metric or (numeric_columns[0] if numeric_columns else None),
            dimension_column=dimension,
            confidence=0.8,
        )
    if any(word in q for word in ("lowest", "minimum", "min", "bottom", "worst")):
        return AnalystIntent(
            "bottom",
            metric_column=metric or (numeric_columns[0] if numeric_columns else None),
            dimension_column=dimension,
            confidence=0.8,
        )
    if any(word in q for word in ("insight", "summary", "analyze", "analysis")):
        return AnalystIntent("summary", confidence=0.85)
    return AnalystIntent("unknown", metric_column=metric, dimension_column=dimension, confidence=0.3)

