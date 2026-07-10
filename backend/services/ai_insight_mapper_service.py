from __future__ import annotations

import re
from typing import Any, Callable

from backend.models.ai_insight_models import (
    AI_INSIGHT_SCHEMA_VERSION,
    DataQualityScore,
    EffortLevel,
    InsightMetadata,
    InsightPriority,
    InsightProvenance,
    RecommendedAction,
    RiskLevel,
    SupportingEvidenceItem,
    UniversalAIInsight,
    UniversalAIInsightCollection,
    UrgencyLevel,
    ValidationStatus,
    compute_overall_confidence,
    utc_now_iso,
)
from backend.models.insight_models import Insight


def _slug_id(prefix: str, title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return f"{prefix}_{slug}" if slug else prefix


def _confidence_from_value(value: Any, default: float = 0.5) -> float:
    if isinstance(value, (int, float)):
        score = float(value)
        return round(max(0.0, min(1.0, score)), 4)
    if isinstance(value, str):
        normalized = value.strip().lower()
        mapping = {
            "very_high": 0.95,
            "high": 0.85,
            "medium": 0.65,
            "moderate": 0.65,
            "low": 0.4,
            "very_low": 0.25,
        }
        if normalized in mapping:
            return mapping[normalized]
    return default


def _risk_level_from_severity(severity: str | None) -> RiskLevel:
    normalized = (severity or "info").strip().lower()
    mapping = {
        "info": RiskLevel.info,
        "low": RiskLevel.low,
        "warning": RiskLevel.medium,
        "medium": RiskLevel.medium,
        "risk": RiskLevel.high,
        "high": RiskLevel.high,
        "critical": RiskLevel.critical,
    }
    return mapping.get(normalized, RiskLevel.info)


def _severity_from_risk_level(risk_level: RiskLevel) -> str:
    mapping = {
        RiskLevel.info: "info",
        RiskLevel.low: "low",
        RiskLevel.medium: "warning",
        RiskLevel.high: "risk",
        RiskLevel.critical: "critical",
    }
    return mapping.get(risk_level, "info")


def _validation_status_from_evidence_status(status: str | None) -> ValidationStatus:
    normalized = (status or "").strip().lower()
    if normalized in {"validated", "validated_limited"}:
        return ValidationStatus.validated
    if normalized == "insufficient":
        return ValidationStatus.insufficient
    if normalized == "rejected":
        return ValidationStatus.rejected
    return ValidationStatus.pending


def _priority_from_value(value: Any) -> InsightPriority:
    if isinstance(value, int):
        if value <= 1:
            return InsightPriority.critical
        if value == 2:
            return InsightPriority.high
        if value == 3:
            return InsightPriority.medium
        return InsightPriority.low
    normalized = str(value or "medium").strip().lower()
    mapping = {
        "critical": InsightPriority.critical,
        "high": InsightPriority.high,
        "medium": InsightPriority.medium,
        "low": InsightPriority.low,
    }
    return mapping.get(normalized, InsightPriority.medium)


def _effort_from_value(value: Any) -> EffortLevel:
    normalized = str(value or "unknown").strip().lower()
    mapping = {
        "low": EffortLevel.low,
        "medium": EffortLevel.medium,
        "high": EffortLevel.high,
    }
    return mapping.get(normalized, EffortLevel.unknown)


def _urgency_from_value(value: Any) -> UrgencyLevel:
    normalized = str(value or "unknown").strip().lower()
    mapping = {
        "low": UrgencyLevel.low,
        "medium": UrgencyLevel.medium,
        "high": UrgencyLevel.high,
        "immediate": UrgencyLevel.immediate,
    }
    return mapping.get(normalized, UrgencyLevel.unknown)


def _data_quality_score_from_payload(payload: dict[str, Any] | None) -> DataQualityScore | None:
    if not payload:
        return None
    return DataQualityScore(
        score=payload.get("score"),
        grade=str(payload.get("grade") or ""),
        completeness_pct=payload.get("completeness_pct"),
        dimensions={key: value for key, value in payload.items() if key not in {"score", "grade", "completeness_pct"}},
    )


def _recommended_action_from_payload(payload: dict[str, Any]) -> RecommendedAction:
    action_text = (
        payload.get("action")
        or payload.get("recommendation")
        or payload.get("executive_recommendation")
        or payload.get("what_to_do")
        or ""
    )
    return RecommendedAction(
        action=str(action_text),
        rationale=str(payload.get("rationale") or payload.get("reason") or ""),
        owner=str(payload.get("owner") or ""),
        priority=_priority_from_value(payload.get("priority", InsightPriority.medium.value)),
        expected_impact=str(payload.get("expected_impact") or payload.get("expected_business_impact") or ""),
        expected_outcome=str(payload.get("expected_outcome") or payload.get("expected_impact") or ""),
        estimated_effort=_effort_from_value(payload.get("estimated_effort")),
        urgency=_urgency_from_value(payload.get("urgency")),
        evidence_refs=[str(item) for item in payload.get("evidence_refs", []) if item],
    )


def _supporting_evidence_from_strings(evidence: list[Any], source: str) -> list[SupportingEvidenceItem]:
    items: list[SupportingEvidenceItem] = []
    for index, entry in enumerate(evidence):
        if isinstance(entry, dict):
            items.append(
                SupportingEvidenceItem(
                    label=str(entry.get("label") or f"Evidence {index + 1}"),
                    value=entry.get("value"),
                    evidence_type=str(entry.get("evidence_type") or entry.get("type") or "text"),
                    source=str(entry.get("source") or source),
                    confidence_score=entry.get("confidence_score"),
                    raw=entry,
                )
            )
        else:
            items.append(
                SupportingEvidenceItem(
                    label=f"Evidence {index + 1}",
                    value=entry,
                    evidence_type="text",
                    source=source,
                )
            )
    return items


def from_rule_based_insight(
    payload: dict[str, Any],
    *,
    domain: str | None = None,
    generated_at: str | None = None,
) -> UniversalAIInsight:
    metadata = payload.get("metadata") or {}
    data_confidence = _confidence_from_value(metadata.get("confidence_score"), default=0.7)
    reasoning_confidence = _confidence_from_value(payload.get("severity"), default=0.6)
    recommended_action = metadata.get("recommended_action")
    actions = [_recommended_action_from_payload({"action": recommended_action})] if recommended_action else []
    evidence = _supporting_evidence_from_strings(
        [metadata.get("evidence_from_data")] if metadata.get("evidence_from_data") else [],
        source="rule_based_engine",
    )
    if metadata.get("what_happened"):
        evidence.append(
            SupportingEvidenceItem(
                label="What happened",
                value=metadata.get("what_happened"),
                evidence_type="narrative",
                source="rule_based_engine",
            )
        )
    return UniversalAIInsight(
        id=_slug_id(str(payload.get("type") or "insight"), str(payload.get("title") or "insight")),
        title=str(payload.get("title") or "Insight"),
        summary=str(payload.get("message") or ""),
        insight=str(metadata.get("what_happened") or payload.get("message") or ""),
        reason=str(metadata.get("why_it_matters") or ""),
        supporting_evidence=evidence,
        affected_metrics=[str(item) for item in metadata.get("affected_metrics", []) if item],
        business_impact=str(metadata.get("why_it_matters") or ""),
        expected_outcome=str(metadata.get("expected_outcome") or metadata.get("recommended_action") or ""),
        risk_level=_risk_level_from_severity(payload.get("severity")),
        priority=_priority_from_value(metadata.get("priority", InsightPriority.medium.value)),
        recommended_actions=actions,
        data_confidence=data_confidence,
        reasoning_confidence=reasoning_confidence,
        overall_confidence=compute_overall_confidence(data_confidence, reasoning_confidence),
        confidence_reason=str(metadata.get("confidence_reason") or "Derived from rule-based evidence strength."),
        assumptions=[str(item) for item in metadata.get("assumptions", []) if item],
        limitations=[str(item) for item in metadata.get("limitations", []) if item],
        related_charts=[str(item) for item in metadata.get("related_charts", []) if item],
        related_kpis=[str(item) for item in metadata.get("related_kpis", []) if item],
        domain=domain,
        generated_by=InsightProvenance(engine="rule_based_engine", provider="platform", engine_version="1.0.0"),
        generated_at=generated_at or utc_now_iso(),
        validation_status=ValidationStatus.validated,
        data_quality_score=_data_quality_score_from_payload(metadata.get("data_quality_score")),
        metadata=InsightMetadata(
            legacy={
                "type": payload.get("type"),
                "severity": payload.get("severity"),
                "source": "rule_based_engine",
            },
            debug={"original_metadata_keys": sorted(metadata.keys())},
            custom={},
            future_extensions={},
        ),
    )


def from_executive_summary(
    payload: dict[str, Any],
    *,
    domain: str | None = None,
    generated_at: str | None = None,
) -> UniversalAIInsight:
    metrics_snapshot = payload.get("metrics_snapshot") or {}
    data_confidence = _confidence_from_value(payload.get("data_confidence") or payload.get("confidence"), default=0.7)
    reasoning_confidence = _confidence_from_value(payload.get("business_confidence"), default=0.65)
    recommendations = [
        _recommended_action_from_payload(item)
        for item in payload.get("recommendations", [])
        if isinstance(item, dict)
    ]
    if payload.get("action") and not recommendations:
        recommendations.append(_recommended_action_from_payload({"action": payload.get("action")}))
    for plan in payload.get("action_plan", []):
        if isinstance(plan, dict):
            recommendations.append(_recommended_action_from_payload(plan))
    return UniversalAIInsight(
        id="executive_summary",
        title="Executive Summary",
        summary=str(payload.get("insight") or ""),
        insight=str(payload.get("insight") or ""),
        reason=str(payload.get("reason") or ""),
        supporting_evidence=_supporting_evidence_from_strings(payload.get("evidence") or [], source="executive_insight_service"),
        affected_metrics=[str(metrics_snapshot.get("primary_metric"))] if metrics_snapshot.get("primary_metric") else [],
        business_impact=str(payload.get("action") or ""),
        expected_outcome=str(
            recommendations[0].expected_outcome
            if recommendations
            else payload.get("action") or ""
        ),
        risk_level=RiskLevel.medium if payload.get("risks") else RiskLevel.info,
        priority=InsightPriority.high,
        recommended_actions=recommendations,
        data_confidence=data_confidence,
        reasoning_confidence=reasoning_confidence,
        overall_confidence=compute_overall_confidence(data_confidence, reasoning_confidence),
        confidence_reason=str(payload.get("confidence") or "Derived from executive summary confidence labels."),
        assumptions=[],
        limitations=[],
        related_charts=[],
        related_kpis=[],
        domain=domain,
        generated_by=InsightProvenance(engine="executive_insight_service", provider="platform", engine_version="1.0.0"),
        generated_at=generated_at or utc_now_iso(),
        validation_status=ValidationStatus.validated,
        data_quality_score=_data_quality_score_from_payload(metrics_snapshot.get("data_quality_score")),
        metadata=InsightMetadata(
            legacy={
                "source": "executive_insight_service",
                "key_findings_count": len(payload.get("key_findings") or []),
                "risks_count": len(payload.get("risks") or []),
                "opportunities_count": len(payload.get("opportunities") or []),
            },
            debug={"metrics_snapshot_keys": sorted(metrics_snapshot.keys())},
            custom={},
            future_extensions={},
        ),
    )


def from_ai_business_card(
    payload: dict[str, Any],
    *,
    domain: str | None = None,
    generated_at: str | None = None,
) -> UniversalAIInsight:
    data_confidence = _confidence_from_value(payload.get("confidence_score"), default=0.5)
    reasoning_confidence = _confidence_from_value(payload.get("evidence_status"), default=0.55)
    recommendation = payload.get("executive_recommendation")
    actions = [_recommended_action_from_payload(payload)] if recommendation else []
    return UniversalAIInsight(
        id=_slug_id(str(payload.get("type") or "card"), str(payload.get("title") or "insight")),
        title=str(payload.get("title") or "Business Insight"),
        summary=str(payload.get("business_meaning") or payload.get("title") or ""),
        insight=str(payload.get("business_meaning") or ""),
        reason=str(payload.get("supporting_evidence") or ""),
        supporting_evidence=[
            SupportingEvidenceItem(
                label="Supporting evidence",
                value=payload.get("supporting_evidence"),
                evidence_type="narrative",
                source="ai_business_insight_service",
                confidence_score=data_confidence,
            )
        ],
        affected_metrics=[str(item) for item in payload.get("affected_metrics", []) if item],
        business_impact=str(payload.get("expected_business_impact") or ""),
        expected_outcome=str(payload.get("expected_business_impact") or recommendation or ""),
        risk_level=_risk_level_from_severity(payload.get("type") if str(payload.get("type")).lower() == "risk" else payload.get("severity")),
        priority=_priority_from_value("high" if str(payload.get("type")).lower() == "risk" else "medium"),
        recommended_actions=actions,
        data_confidence=data_confidence,
        reasoning_confidence=reasoning_confidence,
        overall_confidence=compute_overall_confidence(data_confidence, reasoning_confidence),
        confidence_reason=str(payload.get("evidence_status") or "Derived from validated business insight evidence."),
        assumptions=[],
        limitations=["Insufficient evidence"] if payload.get("evidence_status") == "insufficient" else [],
        related_charts=[],
        related_kpis=[],
        domain=domain,
        generated_by=InsightProvenance(engine="ai_business_insight_service", provider="platform", engine_version="1.0.0"),
        generated_at=generated_at or utc_now_iso(),
        validation_status=_validation_status_from_evidence_status(payload.get("evidence_status")),
        data_quality_score=None,
        metadata=InsightMetadata(
            legacy={
                "type": payload.get("type"),
                "card_type": payload.get("type"),
                "source": "ai_business_insight_service",
            },
            debug={"payload_keys": sorted(payload.keys())},
            custom={},
            future_extensions={},
        ),
    )


def from_analyst_response(
    payload: dict[str, Any],
    *,
    question: str = "",
    domain: str | None = None,
    generated_at: str | None = None,
) -> UniversalAIInsight:
    analyst = payload.get("analyst") or {}
    supporting_data = payload.get("supporting_data") or {}
    data_confidence = _confidence_from_value(analyst.get("confidence"), default=0.6)
    reasoning_confidence = _confidence_from_value(analyst.get("intent"), default=0.55)
    selected_block = supporting_data.get("selected_block") if isinstance(supporting_data, dict) else None
    actions: list[RecommendedAction] = []
    if isinstance(selected_block, dict):
        actions.append(_recommended_action_from_payload(selected_block))
    return UniversalAIInsight(
        id=_slug_id("analyst", question or str(payload.get("answer") or "response")[:48]),
        title=question or "Analyst response",
        summary=str(payload.get("answer") or ""),
        insight=str(payload.get("answer") or ""),
        reason=str((selected_block or {}).get("why_it_happened") or ""),
        supporting_evidence=_supporting_evidence_from_strings(
            [supporting_data] if supporting_data else [],
            source="analyst_service",
        ),
        affected_metrics=[str(analyst.get("metric_column"))] if analyst.get("metric_column") else [],
        business_impact=str((selected_block or {}).get("expected_impact") or ""),
        expected_outcome=str((selected_block or {}).get("expected_impact") or ""),
        risk_level=RiskLevel.high if analyst.get("intent") == "executive_decision" and "risk" in question.lower() else RiskLevel.info,
        priority=InsightPriority.high if analyst.get("intent") == "executive_decision" else InsightPriority.medium,
        recommended_actions=actions,
        data_confidence=data_confidence,
        reasoning_confidence=reasoning_confidence,
        overall_confidence=compute_overall_confidence(data_confidence, reasoning_confidence),
        confidence_reason=str(analyst.get("intent") or "Derived from analyst intent confidence."),
        assumptions=[],
        limitations=[],
        related_charts=[],
        related_kpis=[],
        domain=domain,
        generated_by=InsightProvenance(engine="analyst_service", provider="platform", engine_version="1.0.0"),
        generated_at=generated_at or utc_now_iso(),
        validation_status=ValidationStatus.validated,
        data_quality_score=None,
        metadata=InsightMetadata(
            legacy={
                "source": "analyst_service",
                "question": question,
                "intent": analyst.get("intent"),
            },
            debug={"render_mode": analyst.get("render_mode")},
            custom={},
            future_extensions={},
        ),
    )


def collect_insights(
    items: list[dict[str, Any]],
    mapper: Callable[..., UniversalAIInsight],
    **mapper_kwargs: Any,
) -> list[UniversalAIInsight]:
    return [mapper(item, **mapper_kwargs) for item in items]


def build_insight_collection(
    insights: list[UniversalAIInsight],
    *,
    dataset_id: str | None = None,
    domain: str | None = None,
    generated_at: str | None = None,
) -> UniversalAIInsightCollection:
    return UniversalAIInsightCollection(
        dataset_id=dataset_id,
        domain=domain,
        insights=insights,
        generated_at=generated_at or utc_now_iso(),
    )


def to_legacy_insight(insight: UniversalAIInsight) -> Insight:
    legacy_metadata = {
        "schema_version": insight.schema_version,
        "summary": insight.summary,
        "insight": insight.insight,
        "reason": insight.reason,
        "business_impact": insight.business_impact,
        "expected_outcome": insight.expected_outcome,
        "data_confidence": insight.data_confidence,
        "reasoning_confidence": insight.reasoning_confidence,
        "overall_confidence": insight.overall_confidence,
        "confidence_reason": insight.confidence_reason,
        "validation_status": insight.validation_status.value,
        "generated_at": insight.generated_at,
        "generated_by": insight.generated_by.model_dump(),
        "supporting_evidence": [item.model_dump() for item in insight.supporting_evidence],
        "recommended_actions": [item.model_dump() for item in insight.recommended_actions],
        "affected_metrics": insight.affected_metrics,
        "related_charts": insight.related_charts,
        "related_kpis": insight.related_kpis,
        "assumptions": insight.assumptions,
        "limitations": insight.limitations,
        "data_quality_score": insight.data_quality_score.model_dump() if insight.data_quality_score else None,
        "metadata": insight.metadata.model_dump(),
    }
    legacy_metadata.update(insight.metadata.legacy)
    return Insight(
        type=str(insight.metadata.legacy.get("type") or "universal"),
        title=insight.title,
        message=insight.summary or insight.insight,
        severity=_severity_from_risk_level(insight.risk_level),
        metadata=legacy_metadata,
    )
