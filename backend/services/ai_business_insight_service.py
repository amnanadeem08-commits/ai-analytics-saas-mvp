from __future__ import annotations

from typing import Any

from backend.services.data_insights_service import build_data_insights
from backend.services.dataset_service import load_dataset_dataframe
from backend.utils.response_utils import to_json_safe

CARD_TYPES = ("Opportunity", "Risk", "Trend", "Outlier Interpretation", "Forecast")


def _confidence(value: Any, default: float = 0.6) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = default
    if score > 1:
        score /= 100
    return round(max(0.0, min(1.0, score)), 2)


def _insufficient(card_type: str, reason: str) -> dict[str, Any]:
    return {
        "type": card_type,
        "title": f"{card_type}: Insufficient Evidence",
        "business_meaning": reason,
        "supporting_evidence": "The validated Data Insights layer did not provide enough evidence for this insight.",
        "expected_business_impact": "No executive decision should be made from this signal until stronger evidence is available.",
        "executive_recommendation": "Add complete business fields or collect more records before acting.",
        "confidence_score": 0.0,
        "evidence_status": "insufficient",
    }


def _best_kpi(data_insights: dict[str, Any]) -> dict[str, Any] | None:
    kpis = data_insights.get("kpi_discovery") or []
    business = [kpi for kpi in kpis if kpi.get("category") == "business"]
    candidates = business or kpis
    if not candidates:
        return None
    return max(candidates, key=lambda item: _confidence(item.get("confidence_score")))


def _opportunity(data_insights: dict[str, Any]) -> dict[str, Any]:
    kpi = _best_kpi(data_insights)
    if not kpi:
        return _insufficient("Opportunity", "No validated KPI was discovered, so an opportunity cannot be stated responsibly.")
    metric = kpi.get("metric_name") or "Validated KPI"
    return {
        "type": "Opportunity",
        "title": f"Opportunity: Focus on {metric}",
        "business_meaning": kpi.get("business_purpose") or "Validated KPI discovery identified this as a useful business signal.",
        "supporting_evidence": f"KPI discovery returned {metric} with value {kpi.get('value')} and confidence {_confidence(kpi.get('confidence_score'))}.",
        "expected_business_impact": "Prioritizing this metric can focus leadership attention on a validated business driver.",
        "executive_recommendation": f"Use {metric} as a primary review point and compare it by available segments before action.",
        "confidence_score": _confidence(kpi.get("confidence_score")),
        "evidence_status": "validated",
    }


def _risk(data_insights: dict[str, Any]) -> dict[str, Any]:
    issues = data_insights.get("business_validation") or []
    if issues:
        issue = max(issues, key=lambda row: int(row.get("affected_records", 0) or 0))
        return {
            "type": "Risk",
            "title": f"Risk: {issue.get('issue', 'Validation issue')}",
            "business_meaning": issue.get("business_meaning", "A validated issue may reduce business confidence."),
            "supporting_evidence": f"Affected records: {int(issue.get('affected_records', 0) or 0):,}. Severity: {issue.get('severity', 'warning')}.",
            "expected_business_impact": "If unresolved, this can distort KPI cards, AI answers, Storyboard claims, and exports.",
            "executive_recommendation": issue.get("recommendation", "Review before executive distribution."),
            "confidence_score": _confidence(issue.get("confidence_score"), 0.75),
            "evidence_status": "validated",
        }
    health = data_insights.get("dataset_health") or {}
    score = float(health.get("overall_data_quality_score", 0) or 0)
    if score >= 85:
        return {
            "type": "Risk",
            "title": "Risk: No Major Validation Risk Detected",
            "business_meaning": "The validated layer did not identify a major business validation issue.",
            "supporting_evidence": f"Data quality score is {score}/100 and duplicate rate is {health.get('duplicate_pct', 0)}%.",
            "expected_business_impact": "Outputs have fewer quality blockers, but review is still required before executive decisions.",
            "executive_recommendation": "Proceed with analysis while keeping validation context visible.",
            "confidence_score": 0.74,
            "evidence_status": "validated",
        }
    return _insufficient("Risk", "No specific validation risk was found, but data quality is not strong enough to clear risk confidently.")


def _trend(data_insights: dict[str, Any]) -> dict[str, Any]:
    trends = data_insights.get("trend_evidence") or []
    if not trends:
        return _insufficient("Trend", "No validated trend evidence exists, so a trend insight cannot be stated.")
    trend = trends[0]
    metric = trend.get("metric", "metric")
    direction = trend.get("direction", "changed")
    return {
        "type": "Trend",
        "title": f"Trend: {metric} {direction}",
        "business_meaning": f"Validated trend evidence shows {metric} {direction} across {trend.get('periods')} periods.",
        "supporting_evidence": f"{trend.get('first_period')} value {trend.get('first_value')} to {trend.get('last_period')} value {trend.get('last_value')}; change {trend.get('change_pct')}%.",
        "expected_business_impact": "Trend movement can indicate momentum or deterioration, but it should be interpreted with data quality context.",
        "executive_recommendation": "Review the trend with segment filters before changing targets or budgets.",
        "confidence_score": 0.76,
        "evidence_status": "validated",
    }


def _outlier(data_insights: dict[str, Any]) -> dict[str, Any]:
    outliers = data_insights.get("outlier_assessment") or []
    if not outliers:
        return _insufficient("Outlier Interpretation", "No validated outlier groups were detected.")
    item = max(outliers, key=lambda row: int(row.get("affected_records", 0) or 0))
    return {
        "type": "Outlier Interpretation",
        "title": f"Outlier: Review {item.get('column_name', 'Metric')}",
        "business_meaning": item.get("business_explanation"),
        "supporting_evidence": f"{item.get('affected_records')} affected records detected by {item.get('method', 'IQR')} with bounds {item.get('bounds', {})}.",
        "expected_business_impact": item.get("potential_impact"),
        "executive_recommendation": item.get("recommendation"),
        "confidence_score": _confidence(item.get("confidence_score"), 0.75),
        "evidence_status": "validated",
    }


def _forecast(data_insights: dict[str, Any]) -> dict[str, Any]:
    trends = data_insights.get("trend_evidence") or []
    readiness = ((data_insights.get("readiness_score") or {}).get("ai_analysis") or {}).get("score", 0)
    rows = int((data_insights.get("dataset_health") or {}).get("row_count", 0) or 0)
    if not trends or rows < 8:
        return _insufficient("Forecast", "Validated trend evidence and enough records are required before making a forecast statement.")
    trend = trends[0]
    return {
        "type": "Forecast",
        "title": "Forecast: Directional Readiness Only",
        "business_meaning": "Validated trend evidence exists, but no forecast model output is available, so future values are not invented.",
        "supporting_evidence": f"Trend metric {trend.get('metric')} has {trend.get('periods')} periods. AI readiness score: {readiness}/100.",
        "expected_business_impact": "The dataset can support a forecast workflow, but published projections need a dedicated forecasting model.",
        "executive_recommendation": "Treat this as forecast readiness; do not publish projected values until a forecast model is run.",
        "confidence_score": 0.66 if float(readiness or 0) >= 70 else 0.45,
        "evidence_status": "validated_limited",
    }


def build_ai_business_insights_from_data_insights(data_insights: dict[str, Any] | None) -> dict[str, Any]:
    payload = data_insights or {}
    if payload.get("status") == "empty" or not ((payload.get("dataset_health") or {}).get("row_count")):
        cards = [_insufficient(card_type, "No validated dataset rows are available.") for card_type in CARD_TYPES]
    else:
        cards = [_opportunity(payload), _risk(payload), _trend(payload), _outlier(payload), _forecast(payload)]
    return to_json_safe({"status": payload.get("status", "empty"), "source": "data_insights", "cards": cards})


def build_ai_business_insights(dataset_id: str) -> dict[str, Any]:
    return build_ai_business_insights_from_data_insights(build_data_insights(load_dataset_dataframe(dataset_id)))
