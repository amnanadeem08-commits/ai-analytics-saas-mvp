from __future__ import annotations

from typing import Any

import pandas as pd

from backend.processing.data_profiler import profile_dataframe
from backend.services.kpi_service import compute_business_metrics
from backend.utils.response_utils import to_json_safe


def _confidence(row_count: int, completeness_pct: float) -> str:
    if row_count >= 50 and completeness_pct >= 95:
        return "high"
    if row_count >= 10 and completeness_pct >= 85:
        return "medium"
    return "low"


def _primary_metric_summary(profile: dict[str, Any], metric: str | None) -> dict[str, Any]:
    if not metric:
        return {}
    return profile.get("numeric_summary", {}).get(metric, {})


def _segment_performance(df: pd.DataFrame, metric: str | None, segment: str | None) -> dict[str, Any] | None:
    if not metric or not segment or metric not in df.columns or segment not in df.columns:
        return None
    grouped = df.groupby(segment, dropna=False)[metric].sum().sort_values(ascending=False)
    if grouped.empty:
        return None

    total = float(grouped.sum())
    top_value = float(grouped.iloc[0])
    bottom_value = float(grouped.iloc[-1])
    return {
        "dimension": segment,
        "metric": metric,
        "top_segment": str(grouped.index[0]),
        "top_value": to_json_safe(round(top_value, 4)),
        "top_share_pct": round(top_value / total * 100, 2) if total else None,
        "bottom_segment": str(grouped.index[-1]),
        "bottom_value": to_json_safe(round(bottom_value, 4)),
        "segment_count": int(len(grouped)),
        "total": to_json_safe(round(total, 4)),
    }


def _metric_delta(df: pd.DataFrame, metric: str | None) -> dict[str, Any] | None:
    if not metric or metric not in df.columns:
        return None
    series = pd.to_numeric(df[metric], errors="coerce").dropna()
    if len(series) < 2:
        return None

    midpoint = max(len(series) // 2, 1)
    previous = float(series.iloc[:midpoint].sum())
    current = float(series.iloc[midpoint:].sum())
    delta_pct = None if previous == 0 else round((current - previous) / abs(previous) * 100, 2)
    return {
        "metric": metric,
        "previous_period": to_json_safe(round(previous, 4)),
        "current_period": to_json_safe(round(current, 4)),
        "delta_pct": delta_pct,
        "direction": "increased" if delta_pct and delta_pct > 0 else "decreased" if delta_pct and delta_pct < 0 else "stable",
    }


def _impact_text(delta_pct: float | None) -> str:
    if delta_pct is None:
        return "Business impact cannot be projected until comparable period evidence is available."

    magnitude = abs(delta_pct)
    lower = round(magnitude * 0.4, 1)
    upper = round(magnitude * 0.8, 1)
    if delta_pct > 0:
        return f"Sustaining the current pattern could create an estimated {lower}%-{upper}% additional uplift next period."
    if delta_pct < 0:
        return f"If unresolved, performance could remain {lower}%-{upper}% below the prior run-rate next period."
    return "Expected impact is neutral unless the operating pattern changes."


def _format_metric_value(value: Any) -> str:
    safe_value = to_json_safe(value)
    return "not available" if safe_value is None else str(safe_value)


def build_decision_framework(df: pd.DataFrame) -> list[dict[str, Any]]:
    profile = profile_dataframe(df)
    business_metrics = compute_business_metrics(df)
    primary_metric = business_metrics.get("primary_metric")
    primary_segment = business_metrics.get("primary_segment")
    metric_summary = _primary_metric_summary(profile, primary_metric)
    segment_perf = _segment_performance(df, primary_metric, primary_segment)
    delta = _metric_delta(df, primary_metric)

    row_count = int(profile["row_count"])
    missing_cells = int(profile["total_missing_values"])
    duplicate_rows = int(profile["duplicate_rows"])
    total_cells = max(int(df.size), 1)
    completeness_pct = round((1 - missing_cells / total_cells) * 100, 2)
    confidence = _confidence(row_count, completeness_pct)

    blocks: list[dict[str, Any]] = []

    if primary_metric:
        total = _format_metric_value(metric_summary.get("sum"))
        mean = _format_metric_value(metric_summary.get("mean"))
        movement = (
            f" {primary_metric} {delta['direction']} {delta['delta_pct']}% from "
            f"{delta['previous_period']} to {delta['current_period']}."
            if delta and delta.get("delta_pct") is not None
            else ""
        )
        why = (
            f"The dataset total for {primary_metric} is {total}, with an average value of {mean} "
            f"across {row_count:,} records."
        )
        if segment_perf:
            why += (
                f" {segment_perf['top_segment']} is the leading {segment_perf['dimension']} "
                f"with {segment_perf['top_share_pct']}% of total {segment_perf['metric']}."
            )

        blocks.append(
            {
                "block_id": f"{primary_metric}_performance",
                "metric": primary_metric,
                "framework": "what_why_action",
                "what_happened": f"{primary_metric} totals {total}.{movement}",
                "why_it_happened": why,
                "what_to_do": (
                    f"Use {primary_metric} as the primary executive KPI and review the strongest "
                    "and weakest business segments before setting the next operating target."
                ),
                "expected_impact": _impact_text(delta.get("delta_pct") if delta else None),
                "confidence": confidence,
                "priority": 1,
                "severity": "opportunity" if delta and delta.get("delta_pct") and delta["delta_pct"] > 0 else "monitor",
                "evidence": {
                    "row_count": row_count,
                    "metric_summary": {"metric": primary_metric, **metric_summary},
                    "period_delta": delta,
                    "segment_performance": segment_perf,
                },
            }
        )

    if segment_perf:
        concentration = segment_perf.get("top_share_pct") or 0
        blocks.append(
            {
                "block_id": f"{segment_perf['dimension']}_concentration",
                "metric": segment_perf["metric"],
                "framework": "what_why_action",
                "what_happened": (
                    f"{segment_perf['top_segment']} leads {segment_perf['dimension']} with "
                    f"{segment_perf['top_value']} total {segment_perf['metric']}."
                ),
                "why_it_happened": (
                    f"{segment_perf['top_segment']} contributes {segment_perf['top_share_pct']}% of total "
                    f"{segment_perf['metric']}, while {segment_perf['bottom_segment']} contributes "
                    f"{segment_perf['bottom_value']}."
                ),
                "what_to_do": (
                    f"Compare {segment_perf['top_segment']} against {segment_perf['bottom_segment']} "
                    "to identify repeatable drivers and performance gaps."
                ),
                "expected_impact": (
                    "Reducing segment imbalance can improve blended performance and lower dependence "
                    "on one leading segment."
                ),
                "confidence": confidence,
                "priority": 2,
                "severity": "risk" if concentration >= 60 else "opportunity",
                "evidence": segment_perf,
            }
        )

    if missing_cells or duplicate_rows:
        blocks.append(
            {
                "block_id": "data_quality_readiness",
                "metric": "data_quality",
                "framework": "what_why_action",
                "what_happened": (
                    f"Data completeness is {completeness_pct}% with {missing_cells:,} missing values "
                    f"and {duplicate_rows:,} duplicate rows."
                ),
                "why_it_happened": (
                    "The uploaded dataset contains quality issues that can distort KPI totals, averages, "
                    "and segment comparisons."
                ),
                "what_to_do": "Resolve missing values and duplicate rows before using this dataset for board-level decisions.",
                "expected_impact": "Improves reliability of KPI interpretation and reduces executive decision risk.",
                "confidence": confidence,
                "priority": 3,
                "severity": "risk",
                "evidence": {
                    "row_count": row_count,
                    "column_count": int(profile["column_count"]),
                    "missing_values": missing_cells,
                    "duplicate_rows": duplicate_rows,
                    "completeness_pct": completeness_pct,
                },
            }
        )

    if not blocks:
        blocks.append(
            {
                "block_id": "dataset_readiness",
                "metric": "dataset",
                "framework": "what_why_action",
                "what_happened": f"The dataset contains {row_count:,} records but no numeric executive KPI was detected.",
                "why_it_happened": "Detected columns do not include a measurable numeric business metric.",
                "what_to_do": "Add or map a metric column such as revenue, sales, cost, churn, profit, amount, or score.",
                "expected_impact": "A mapped KPI enables evidence-based executive summaries, chart recommendations, and analyst answers.",
                "confidence": confidence,
                "priority": 1,
                "severity": "monitor",
                "evidence": {
                    "row_count": row_count,
                    "column_count": int(profile["column_count"]),
                    "numeric_columns": profile.get("column_types", {}).get("numeric_columns", []),
                },
            }
        )

    return blocks
