from __future__ import annotations

from typing import Any

import pandas as pd


ADDITIVE_HINTS = (
    "revenue",
    "sales",
    "amount",
    "quantity",
    "qty",
    "orders",
    "units",
    "profit",
    "cost",
    "expense",
    "spend",
    "income",
    "price",
    "value",
)

AVERAGE_HINTS = (
    "age",
    "score",
    "rating",
    "satisfaction",
    "risk",
    "rate",
    "percent",
    "percentage",
    "ratio",
    "index",
    "temperature",
    "duration",
)

IDENTIFIER_HINTS = ("id", "code", "zip", "postal", "phone", "ssn", "account", "customer_id")


def _normalized(column: str) -> str:
    return column.lower().replace(" ", "_").replace("-", "_")


def metric_suitability(column: str, series: pd.Series | None = None) -> dict[str, Any]:
    """Classify whether SUM, AVG, or no numeric aggregation is business-suitable."""
    name = _normalized(column)
    unique_ratio = None
    if series is not None:
        clean = pd.to_numeric(series, errors="coerce").dropna()
        unique_ratio = float(clean.nunique() / len(clean)) if len(clean) else None

    if name.endswith("_id") or name == "id" or any(hint == name for hint in IDENTIFIER_HINTS):
        return {
            "metric": column,
            "recommended_aggregation": "none",
            "business_relevance": "low",
            "business_confidence": "low",
            "is_additive": False,
            "is_valid_metric": False,
            "reason": "Identifier/code fields should not be summed or averaged for executive KPIs.",
        }

    if any(hint in name for hint in AVERAGE_HINTS):
        return {
            "metric": column,
            "recommended_aggregation": "average",
            "business_relevance": "medium",
            "business_confidence": "medium",
            "is_additive": False,
            "is_valid_metric": True,
            "reason": f"{column} is not naturally additive; average, median, distribution, or segmentation is more meaningful than total.",
        }

    if any(hint in name for hint in ADDITIVE_HINTS):
        return {
            "metric": column,
            "recommended_aggregation": "sum",
            "business_relevance": "high",
            "business_confidence": "high",
            "is_additive": True,
            "is_valid_metric": True,
            "reason": f"{column} is suitable for additive KPI analysis such as total and segment contribution.",
        }

    if unique_ratio is not None and unique_ratio > 0.95:
        return {
            "metric": column,
            "recommended_aggregation": "average",
            "business_relevance": "medium",
            "business_confidence": "medium",
            "is_additive": False,
            "is_valid_metric": True,
            "reason": f"{column} behaves like a continuous measure; average and distribution are safer than total.",
        }

    return {
        "metric": column,
        "recommended_aggregation": "average",
        "business_relevance": "medium",
        "business_confidence": "medium",
        "is_additive": False,
        "is_valid_metric": True,
        "reason": f"{column} has no clear additive business meaning; use average or distribution before using total.",
    }


def aggregate_series(series: pd.Series, aggregation: str) -> float:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return 0.0
    if aggregation == "sum":
        return float(clean.sum())
    if aggregation == "median":
        return float(clean.median())
    return float(clean.mean())


def aggregate_label(aggregation: str) -> str:
    return {
        "sum": "total",
        "average": "average",
        "median": "median",
        "none": "records",
    }.get(aggregation, aggregation)


def select_primary_metric(df: pd.DataFrame, numeric_columns: list[str]) -> tuple[str | None, dict[str, Any] | None]:
    assessments = [
        metric_suitability(column, df[column])
        for column in numeric_columns
        if column in df.columns
    ]
    valid = [item for item in assessments if item["is_valid_metric"]]
    additive = [item for item in valid if item["recommended_aggregation"] == "sum"]
    selected = (additive or valid or assessments)[:1]
    if not selected:
        return None, None
    return selected[0]["metric"], selected[0]
