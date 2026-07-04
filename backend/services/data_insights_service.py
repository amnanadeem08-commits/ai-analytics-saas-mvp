from __future__ import annotations

from typing import Any

import pandas as pd

from backend.processing.data_profiler import profile_dataframe
from backend.services.kpi_service import compute_kpi_cards
from backend.utils.response_utils import to_json_safe


def build_data_insights(df: pd.DataFrame | None) -> dict[str, Any]:
    if df is None or df.empty:
        return {
            "status": "empty",
            "dataset_health": {"row_count": 0, "column_count": 0, "overall_data_quality_score": 0, "grade": "D"},
            "kpi_discovery": [],
            "statistical_profile": [],
            "business_validation": [{"issue": "No dataset rows available", "severity": "warning", "business_meaning": "No validated analysis can be generated without rows.", "recommendation": "Upload or select a dataset with records.", "affected_records": 0, "confidence_score": 1.0}],
            "outlier_assessment": [],
            "trend_evidence": [],
            "readiness_score": {"ai_analysis": {"score": 0, "ready": False, "reason": "No rows available."}},
        }

    profile = profile_dataframe(df)
    quality = profile.get("data_quality_score", {})
    column_types = profile.get("column_types", {})
    row_count = int(profile.get("row_count", 0) or 0)
    column_count = int(profile.get("column_count", 0) or 0)
    numeric_columns = column_types.get("numeric_columns", [])
    date_columns = column_types.get("date_columns", [])
    kpi_cards = compute_kpi_cards(df)

    validation: list[dict[str, Any]] = []
    for column in numeric_columns:
        lowered = str(column).lower()
        if any(token in lowered for token in ("revenue", "sales", "amount", "price")):
            series = pd.to_numeric(df[column], errors="coerce")
            negative = int((series < 0).sum())
            if negative:
                validation.append({"issue": f"Negative values in {column}", "severity": "warning", "business_meaning": "Negative commercial values may be refunds, credits, reversals, or data quality issues.", "recommendation": "Validate these records before using the metric in executive decisions.", "affected_records": negative, "confidence_score": 0.88})

    statistical_profile = []
    for column, summary in (profile.get("numeric_summary") or {}).items():
        statistical_profile.append({
            "column": column,
            "mean": summary.get("mean"),
            "median": summary.get("median"),
            "standard_deviation": summary.get("std"),
            "minimum": summary.get("min"),
            "maximum": summary.get("max"),
            "business_meaning": f"{column} has validated summary statistics available for executive interpretation.",
        })

    outliers = []
    for item in profile.get("outlier_summary", []) or []:
        outliers.append({
            "column_name": item.get("column"),
            "affected_records": item.get("outlier_count", 0),
            "business_explanation": "Statistical outliers may be premium customers, bulk orders, one-off events, or data quality issues.",
            "potential_impact": "Outliers can shift averages, forecasts, and targets if treated blindly.",
            "recommendation": "Review before removing; do not delete automatically.",
            "confidence_score": 0.82,
            "method": item.get("method", "IQR"),
            "bounds": {"lower": item.get("lower_bound"), "upper": item.get("upper_bound")},
        })

    missing_total = int(profile.get("total_missing_values", 0) or 0)
    duplicate_rows = int(profile.get("duplicate_rows", 0) or 0)
    total_cells = max(row_count * column_count, 1)
    readiness = float(quality.get("score", 0) or 0)
    if row_count < 8:
        readiness = min(readiness, 55)

    return to_json_safe({
        "status": "ready",
        "dataset_health": {
            "row_count": row_count,
            "column_count": column_count,
            "numeric_column_count": len(numeric_columns),
            "categorical_column_count": len(column_types.get("categorical_columns", [])),
            "date_column_count": len(date_columns),
            "missing_value_pct": round(missing_total / total_cells * 100, 2),
            "duplicate_pct": round(duplicate_rows / max(row_count, 1) * 100, 2),
            "overall_data_quality_score": quality.get("score", 0),
            "grade": quality.get("grade", "D"),
        },
        "kpi_discovery": [
            {
                "kpi_id": card.get("kpi_id"),
                "metric_name": card.get("label"),
                "value": card.get("value"),
                "formatted_value": card.get("formatted_value"),
                "aggregation": card.get("aggregation"),
                "unit": card.get("unit"),
                "category": card.get("category"),
                "business_purpose": card.get("business_context") or card.get("description"),
                "confidence_score": card.get("confidence_score", 0.75),
                "traceability": card.get("evidence", {}),
            }
            for card in kpi_cards
        ],
        "statistical_profile": statistical_profile,
        "business_validation": validation,
        "outlier_assessment": outliers,
        "trend_evidence": profile.get("trend_summary", []),
        "readiness_score": {"ai_analysis": {"score": round(readiness, 1), "ready": bool(row_count >= 8 and readiness >= 70), "reason": "Requires enough records, quality, and validated metrics for AI business interpretation."}},
    })
