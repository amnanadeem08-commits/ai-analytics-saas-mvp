from __future__ import annotations

from typing import Any

from backend.models.domain_context_models import DomainContext
from backend.services.data_insights_service import build_data_insights
from backend.services.dataset_service import load_dataset_dataframe
from backend.services.domain_intelligence_service import build_domain_context, detect_domain, ensure_domain_context
from backend.services.domain_policy_service import apply_language_policy, build_domain_policy
from backend.services.domain_profile_service import DOMAIN_PROFILES, canonical_domain, domain_profile
from backend.utils.response_utils import to_json_safe

CARD_TYPES = ("Opportunity", "Risk", "Trend", "Outlier Interpretation", "Forecast")

SUPPORTED_DOMAINS = set(DOMAIN_PROFILES)


def _confidence(value: Any, default: float = 0.6) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = default
    if score > 1:
        score /= 100
    return round(max(0.0, min(1.0, score)), 2)


def _normalize_domain(domain: Any) -> str:
    return canonical_domain(str(domain or "Generic Business Dataset"))


def _domain_confidence(domain_detection: dict[str, Any] | None) -> float:
    if not domain_detection:
        return 0.0
    if "confidence_score" in domain_detection:
        return _confidence(domain_detection.get("confidence_score"))
    confidence = str(domain_detection.get("confidence") or "").lower()
    if confidence == "high":
        return 0.9
    if confidence == "medium":
        return 0.65
    if confidence == "low":
        return 0.35
    return _confidence(domain_detection.get("score"), 0.5)


def _domain_route(domain_detection: dict[str, Any] | None) -> dict[str, Any]:
    detected_domain = (domain_detection or {}).get("domain")
    domain = _normalize_domain(detected_domain)
    policy = build_domain_policy(domain)
    return {
        "detected_domain": detected_domain or "General",
        "domain": domain,
        "prompt": policy.get("prompt", "GENERAL_ANALYST_PROMPT"),
        "policy": policy,
        "confidence_score": _domain_confidence(domain_detection),
    }


def _apply_domain_route(card: dict[str, Any], route: dict[str, Any]) -> dict[str, Any]:
    routed = {**card, "domain": route["domain"], "prompt": route["prompt"]}
    policy = route.get("policy") or build_domain_policy(route["domain"])
    for key in (
        "title",
        "business_meaning",
        "supporting_evidence",
        "expected_business_impact",
        "executive_recommendation",
    ):
        routed[key] = apply_language_policy(routed.get(key), policy)
    return routed


def _language(route: dict[str, Any]) -> dict[str, str]:
    policy = route.get("policy") or build_domain_policy(route["domain"])
    terms = policy.get("terms") or {}
    if terms:
        return terms
    profile = domain_profile(route["domain"])
    return {
        "lens": profile["context"].lower(),
        "leader": "business leadership team",
        "metric": "KPI",
        "metrics": "KPIs",
        "driver": (profile.get("root_causes") or ["evidence-backed driver"])[0],
        "summary_action": f"prioritize {profile['metrics'][0].lower()} and the strongest validated recommendations",
    }


def _apply_domain_language(value: Any, route: dict[str, Any]) -> Any:
    policy = route.get("policy") or build_domain_policy(route["domain"])
    return apply_language_policy(value, policy)


def _confidence_label(value: Any) -> str:
    score = _confidence(value)
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _top_validated_cards(cards: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    validated = [card for card in cards if card.get("evidence_status") != "insufficient"]
    candidates = validated or cards
    return sorted(candidates, key=lambda card: _confidence(card.get("confidence_score")), reverse=True)[:limit]


def _build_executive_summary(payload: dict[str, Any], cards: list[dict[str, Any]], route: dict[str, Any]) -> dict[str, Any]:
    health = payload.get("dataset_health") or {}
    terms = _language(route)
    top_card = (_top_validated_cards(cards, 1) or [{}])[0]
    row_count = int(health.get("row_count", 0) or 0)
    quality_score = health.get("overall_data_quality_score", 0)
    lead = top_card.get("business_meaning") or f"The dataset has limited validated evidence for {terms['lens']}."
    summary = (
        f"The {route['domain']} insight engine reviewed {row_count:,} records through a {terms['lens']} lens. "
        f"Data quality is {quality_score}/100, and the strongest signal is: {lead}"
    )
    action = f"Ask the {terms['leader']} to {terms['summary_action']}."
    result = {
        "headline": f"{route['domain']} Executive Summary",
        "summary": summary,
        "recommended_action": action,
        "confidence": _confidence_label(top_card.get("confidence_score", route.get("confidence_score"))),
        "confidence_score": _confidence(top_card.get("confidence_score", route.get("confidence_score"))),
        "domain": route["domain"],
    }
    return _apply_domain_language(result, route)


def _build_key_findings(cards: list[dict[str, Any]], route: dict[str, Any]) -> list[dict[str, Any]]:
    findings = []
    for card in _top_validated_cards(cards, 5):
        findings.append(
            {
                "finding": card.get("title", "Validated finding"),
                "insight": card.get("business_meaning") or card.get("supporting_evidence", "Validated evidence is limited."),
                "evidence": card.get("supporting_evidence", "Validated evidence is limited."),
                "confidence": _confidence_label(card.get("confidence_score")),
                "confidence_score": _confidence(card.get("confidence_score")),
                "domain": route["domain"],
            }
        )
    return _apply_domain_language(findings, route)


def _build_kpis(payload: dict[str, Any], cards: list[dict[str, Any]], route: dict[str, Any]) -> list[dict[str, Any]]:
    terms = _language(route)
    kpis = []
    for item in (payload.get("kpi_discovery") or [])[:6]:
        name = item.get("metric_name") or item.get("label") or terms["metric"]
        kpis.append(
            {
                "label": name,
                "value": item.get("formatted_value", item.get("value", "N/A")),
                "raw_value": item.get("value", "N/A"),
                "aggregation": item.get("aggregation"),
                "unit": item.get("unit"),
                "meaning": item.get("business_purpose") or f"Validated {terms['metric']} for {terms['lens']} review.",
                "confidence_score": _confidence(item.get("confidence_score")),
                "domain": route["domain"],
            }
        )
    if kpis:
        return _apply_domain_language(kpis, route)

    health = payload.get("dataset_health") or {}
    fallback = [
        {
            "label": "Dataset Records",
            "value": int(health.get("row_count", 0) or 0),
            "meaning": f"Record volume available for {terms['lens']} review.",
            "confidence_score": 1.0 if health.get("row_count") else 0.0,
            "domain": route["domain"],
        },
        {
            "label": "Data Quality Score",
            "value": health.get("overall_data_quality_score", 0),
            "meaning": f"Readiness of the dataset for trusted {terms['metrics']} and recommendations.",
            "confidence_score": 0.7 if health else 0.0,
            "domain": route["domain"],
        },
    ]
    if cards:
        fallback.append(
            {
                "label": "Insight Confidence",
                "value": max(_confidence(card.get("confidence_score")) for card in cards),
                "meaning": f"Highest confidence among generated {route['domain']} insight cards.",
                "confidence_score": max(_confidence(card.get("confidence_score")) for card in cards),
                "domain": route["domain"],
            }
        )
    return _apply_domain_language(fallback, route)


def _section_from_cards(cards: list[dict[str, Any]], route: dict[str, Any], card_types: set[str], default_title: str) -> list[dict[str, Any]]:
    selected = [card for card in cards if card.get("type") in card_types]
    if not selected:
        selected = cards[:1]
    section = []
    for card in selected[:5]:
        section.append(
            {
                "title": card.get("title", default_title),
                "insight": card.get("business_meaning") or card.get("supporting_evidence", "Validated evidence is limited."),
                "evidence": card.get("supporting_evidence", "Validated evidence is limited."),
                "recommendation": card.get("executive_recommendation", "Review validated evidence before acting."),
                "confidence": _confidence_label(card.get("confidence_score")),
                "confidence_score": _confidence(card.get("confidence_score")),
                "domain": route["domain"],
            }
        )
    return _apply_domain_language(section, route)


def _build_recommendations(cards: list[dict[str, Any]], route: dict[str, Any]) -> list[dict[str, Any]]:
    terms = _language(route)
    recommendations = []
    for card in _top_validated_cards(cards, 5):
        recommendations.append(
            {
                "recommendation": card.get("executive_recommendation") or f"Review this {terms['driver']} before taking action.",
                "why": card.get("business_meaning") or card.get("supporting_evidence", "Validated evidence is limited."),
                "expected_impact": card.get("expected_business_impact", f"Sharper decisions across {terms['lens']}.") or f"Sharper decisions across {terms['lens']}.",
                "priority": "High" if _confidence(card.get("confidence_score")) >= 0.75 else "Medium",
                "confidence": _confidence_label(card.get("confidence_score")),
                "confidence_score": _confidence(card.get("confidence_score")),
                "domain": route["domain"],
            }
        )
    if recommendations:
        return _apply_domain_language(recommendations, route)
    return _apply_domain_language(
        [
            {
                "recommendation": f"Collect more complete evidence before making {route['domain']} decisions.",
                "why": "The validated Data Insights layer did not provide enough evidence.",
                "expected_impact": f"Improves confidence in {terms['metrics']} and recommendations.",
                "priority": "Medium",
                "confidence": "low",
                "confidence_score": 0.0,
                "domain": route["domain"],
            }
        ],
        route,
    )


def _build_insight_engine_sections(payload: dict[str, Any], cards: list[dict[str, Any]], route: dict[str, Any]) -> dict[str, Any]:
    return {
        "executive_summary": _build_executive_summary(payload, cards, route),
        "key_findings": _build_key_findings(cards, route),
        "kpis": _build_kpis(payload, cards, route),
        "risks": _section_from_cards(cards, route, {"Risk", "Outlier Interpretation", "Forecast"}, "Risk"),
        "opportunities": _section_from_cards(cards, route, {"Opportunity", "Trend"}, "Opportunity"),
        "recommendations": _build_recommendations(cards, route),
    }


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


def build_ai_business_insights_from_data_insights(
    data_insights: dict[str, Any] | None,
    domain_detection: dict[str, Any] | None = None,
    domain_context: DomainContext | dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = data_insights or {}
    context = ensure_domain_context(domain_context or ({"detection": domain_detection} if domain_detection else None))
    route = _domain_route(
        {
            "domain": context.detected_domain,
            "confidence": context.confidence,
            "confidence_score": context.confidence_score,
            "signals": context.detection_signals,
        }
    )
    route["policy"] = context.language_policy or route.get("policy")
    if payload.get("status") == "empty" or not ((payload.get("dataset_health") or {}).get("row_count")):
        cards = [_insufficient(card_type, "No validated dataset rows are available.") for card_type in CARD_TYPES]
    else:
        cards = [_opportunity(payload), _risk(payload), _trend(payload), _outlier(payload), _forecast(payload)]
    routed_cards = [_apply_domain_route(card, route) for card in cards]
    sections = _build_insight_engine_sections(payload, routed_cards, route)
    return to_json_safe(
        {
            "status": payload.get("status", "empty"),
            "source": "data_insights",
            "domain_router": route,
            **sections,
            "cards": routed_cards,
        }
    )


def build_ai_business_insights(dataset_id: str) -> dict[str, Any]:
    df = load_dataset_dataframe(dataset_id)
    context = build_domain_context(df)
    return build_ai_business_insights_from_data_insights(build_data_insights(df), domain_context=context)
