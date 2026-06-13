from __future__ import annotations

from typing import Any

import pandas as pd

from backend.processing.data_profiler import profile_dataframe
from backend.services.decision_framework_service import build_decision_framework
from backend.services.kpi_service import compute_business_metrics, compute_kpi_cards
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
    grouped = (
        df.groupby(segment, dropna=False)[metric]
        .sum()
        .sort_values(ascending=False)
    )
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
        return "Impact cannot be projected until comparable period data is available."
    magnitude = abs(delta_pct)
    if delta_pct > 0:
        return f"Sustaining the current momentum could create an estimated {round(magnitude * 0.4, 1)}%-{round(magnitude * 0.8, 1)}% additional uplift next period."
    if delta_pct < 0:
        return f"If unresolved, performance could remain {round(magnitude * 0.4, 1)}%-{round(magnitude * 0.8, 1)}% below prior run-rate next period."
    return "Expected impact is neutral unless the operating pattern changes."


def build_executive_summary(df: pd.DataFrame) -> dict[str, Any]:
    profile = profile_dataframe(df)
    business_metrics = compute_business_metrics(df)
    kpi_cards = compute_kpi_cards(df)
    row_count = int(profile["row_count"])
    column_count = int(profile["column_count"])
    missing_cells = int(profile["total_missing_values"])
    total_cells = max(int(df.size), 1)
    completeness_pct = round((1 - missing_cells / total_cells) * 100, 2)
    segment_leader = business_metrics.get("segment_leader")
    primary_metric = business_metrics.get("primary_metric")
    primary_segment = business_metrics.get("primary_segment")
    metric_summary = _primary_metric_summary(profile, primary_metric)
    segment_perf = _segment_performance(df, primary_metric, primary_segment)
    delta = _metric_delta(df, primary_metric)
    confidence = _confidence(row_count, completeness_pct)
    decision_framework = build_decision_framework(df)

    evidence = [
        f"Rows analyzed: {row_count:,}",
        f"Columns analyzed: {column_count:,}",
        f"Data completeness: {completeness_pct}%",
        f"Duplicate rows: {int(profile['duplicate_rows']):,}",
    ]

    if primary_metric:
        summary = profile["numeric_summary"].get(primary_metric, {})
        evidence.append(f"Total {primary_metric}: {to_json_safe(summary.get('sum'))}")
        evidence.append(f"Average {primary_metric}: {to_json_safe(summary.get('mean'))}")

    if segment_leader:
        evidence.append(
            f"Top {segment_leader['dimension']} by {segment_leader['metric']}: "
            f"{segment_leader['segment']} ({segment_leader['value']})"
        )

    if delta:
        evidence.append(
            f"{primary_metric} {delta['direction']}: {delta['previous_period']} to {delta['current_period']} "
            f"({delta['delta_pct']}%)"
        )

    if primary_metric and segment_leader:
        top_share = segment_perf.get("top_share_pct") if segment_perf else None
        insight = (
            f"{segment_leader['segment']} leads {segment_leader['dimension']} performance "
            f"on {primary_metric}."
        )
        reason = (
            f"The grouped total for {segment_leader['segment']} is {segment_leader['value']}"
            + (f", representing {top_share}% of total {primary_metric}" if top_share is not None else "")
            + "."
        )
        action = (
            f"Review what is driving {segment_leader['segment']} performance and compare it "
            "against weaker segments before setting the next growth target."
        )
    elif primary_metric:
        insight = f"{primary_metric} is the primary measurable business signal in this dataset."
        reason = "The dataset has numeric business columns but no clear categorical segment for comparison."
        action = "Add or select a segment column to make performance differences more actionable."
    else:
        insight = "The dataset is ready for structural review, but no numeric business metric was detected."
        reason = "The current columns are mostly categorical, textual, boolean, or date-like."
        action = "Add a measurable numeric field such as sales, revenue, cost, profit, amount, or score."

    if missing_cells > 0:
        action += " Address missing values before making production decisions."

    key_findings = []
    if primary_metric:
        key_findings.append(
            {
                "title": f"{primary_metric} performance baseline",
                "finding": f"Total {primary_metric} is {to_json_safe(metric_summary.get('sum'))} with average {to_json_safe(metric_summary.get('mean'))}.",
                "evidence": {"metric": primary_metric, **metric_summary},
            }
        )
    if segment_perf:
        key_findings.append(
            {
                "title": f"{segment_perf['dimension']} concentration",
                "finding": (
                    f"{segment_perf['top_segment']} contributes {segment_perf['top_share_pct']}% "
                    f"of total {segment_perf['metric']}."
                ),
                "evidence": segment_perf,
            }
        )
    if delta:
        key_findings.append(
            {
                "title": f"{primary_metric} period movement",
                "finding": (
                    f"{primary_metric} {delta['direction']} from {delta['previous_period']} "
                    f"to {delta['current_period']} ({delta['delta_pct']}%)."
                ),
                "evidence": delta,
            }
        )

    risks = []
    if missing_cells > 0:
        risks.append(
            {
                "risk": "Data quality risk",
                "why_it_matters": f"{missing_cells:,} missing values may distort metric interpretation.",
                "evidence": {"missing_values": missing_cells, "completeness_pct": completeness_pct},
            }
        )
    if int(profile["duplicate_rows"]) > 0:
        risks.append(
            {
                "risk": "Duplicate record risk",
                "why_it_matters": f"{int(profile['duplicate_rows']):,} duplicate rows may inflate totals.",
                "evidence": {"duplicate_rows": int(profile["duplicate_rows"])},
            }
        )
    if segment_perf and segment_perf.get("top_share_pct") and segment_perf["top_share_pct"] >= 60:
        risks.append(
            {
                "risk": "Segment concentration risk",
                "why_it_matters": f"{segment_perf['top_segment']} contributes {segment_perf['top_share_pct']}% of {segment_perf['metric']}.",
                "evidence": segment_perf,
            }
        )

    opportunities = []
    if segment_perf:
        opportunities.append(
            {
                "opportunity": f"Scale what works in {segment_perf['top_segment']}",
                "why": f"{segment_perf['top_segment']} is the strongest {segment_perf['dimension']} by {segment_perf['metric']}.",
                "evidence": segment_perf,
            }
        )
        opportunities.append(
            {
                "opportunity": f"Close the gap in {segment_perf['bottom_segment']}",
                "why": f"{segment_perf['bottom_segment']} trails with {segment_perf['bottom_value']} total {segment_perf['metric']}.",
                "evidence": segment_perf,
            }
        )
    if delta and delta.get("delta_pct") and delta["delta_pct"] > 0:
        opportunities.append(
            {
                "opportunity": "Preserve current growth momentum",
                "why": f"{primary_metric} increased {delta['delta_pct']}% between comparable periods.",
                "evidence": delta,
            }
        )

    recommendations = []
    if segment_perf:
        recommendations.append(
            {
                "recommendation": f"Prioritize {segment_perf['top_segment']} playbook analysis",
                "reason": f"It leads {segment_perf['dimension']} with {segment_perf['top_value']} total {segment_perf['metric']}.",
                "expected_impact": _impact_text(delta.get("delta_pct") if delta else None),
            }
        )
        recommendations.append(
            {
                "recommendation": f"Investigate underperformance in {segment_perf['bottom_segment']}",
                "reason": f"It is the lowest {segment_perf['dimension']} segment by {segment_perf['metric']}.",
                "expected_impact": "Closing the weakest segment gap can improve blended performance and reduce dependence on the top segment.",
            }
        )
    if missing_cells > 0:
        recommendations.append(
            {
                "recommendation": "Resolve missing values before board-level decisions",
                "reason": f"Completeness is {completeness_pct}% with {missing_cells:,} missing cells.",
                "expected_impact": "Improves confidence in KPIs and reduces decision risk.",
            }
        )

    action_plan = [
        {
            "priority": 1,
            "action": action,
            "owner": "Analytics Lead",
            "evidence": evidence[-3:],
        }
    ]
    if segment_perf:
        action_plan.append(
            {
                "priority": 2,
                "action": f"Compare {segment_perf['top_segment']} against {segment_perf['bottom_segment']} to isolate drivers.",
                "owner": "Growth / Operations",
                "evidence": [segment_perf],
            }
        )

    return {
        "insight": insight,
        "reason": reason,
        "action": action,
        "evidence": evidence,
        "metrics_snapshot": {
            "row_count": row_count,
            "column_count": column_count,
            "completeness_pct": completeness_pct,
            "primary_metric": primary_metric,
            "segment_leader": segment_leader,
            "kpi_count": len(kpi_cards),
        },
        "confidence": confidence,
        "key_findings": key_findings,
        "risks": risks,
        "opportunities": opportunities,
        "recommendations": recommendations,
        "action_plan": action_plan,
        "ceo_insights": decision_framework,
        "decision_framework": decision_framework,
    }
