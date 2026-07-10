from __future__ import annotations

import re
from typing import Any

from backend.models.ai_insight_models import (
    InsightPriority,
    RecommendedAction,
    RiskLevel,
    UniversalAIInsight,
    UrgencyLevel,
    ValidationStatus,
    utc_now_iso,
)
from backend.models.decision_models import (
    DECISION_SCHEMA_VERSION,
    DecisionAlternative,
    DecisionCategory,
    DecisionCollection,
    DecisionEvidence,
    DecisionMetadata,
    DecisionPathStep,
    DecisionRecommendation,
    DecisionStatus,
    DecisionSummary,
    DecisionTimeHorizon,
    ExpectedOutcomeTarget,
)

_PENDING_VALIDATION_MESSAGE = "Insight must be validated before decision intelligence can run."
_BLOCKED_VALIDATION_STATUSES = {ValidationStatus.rejected}

_DOMAIN_CATEGORY_MAP: dict[str, DecisionCategory] = {
    "sales": DecisionCategory.revenue_growth,
    "finance": DecisionCategory.cost_reduction,
    "financial": DecisionCategory.cost_reduction,
    "healthcare": DecisionCategory.customer_experience,
    "customer churn": DecisionCategory.risk_mitigation,
    "telecom": DecisionCategory.customer_experience,
    "insurance": DecisionCategory.compliance,
    "generic business dataset": DecisionCategory.strategic_planning,
}

_RISK_CATEGORY_MAP: dict[RiskLevel, DecisionCategory] = {
    RiskLevel.high: DecisionCategory.risk_mitigation,
    RiskLevel.critical: DecisionCategory.risk_mitigation,
}

_KEYWORD_CATEGORY_RULES: tuple[tuple[str, DecisionCategory], ...] = (
    ("forecast", DecisionCategory.forecasting),
    ("predict", DecisionCategory.forecasting),
    ("compliance", DecisionCategory.compliance),
    ("regulatory", DecisionCategory.compliance),
    ("data quality", DecisionCategory.data_quality),
    ("completeness", DecisionCategory.data_quality),
    ("missing", DecisionCategory.data_quality),
    ("risk", DecisionCategory.risk_mitigation),
    ("churn", DecisionCategory.risk_mitigation),
    ("customer", DecisionCategory.customer_experience),
    ("experience", DecisionCategory.customer_experience),
    ("cost", DecisionCategory.cost_reduction),
    ("expense", DecisionCategory.cost_reduction),
    ("operational", DecisionCategory.operational_improvement),
    ("efficiency", DecisionCategory.operational_improvement),
    ("strategy", DecisionCategory.strategic_planning),
    ("strategic", DecisionCategory.strategic_planning),
    ("revenue", DecisionCategory.revenue_growth),
    ("growth", DecisionCategory.revenue_growth),
    ("sales", DecisionCategory.revenue_growth),
)

_PRIORITY_SCORE_BOOST = {
    InsightPriority.critical: 20.0,
    InsightPriority.high: 15.0,
    InsightPriority.medium: 5.0,
    InsightPriority.low: 0.0,
}

_URGENCY_HORIZON_MAP = {
    UrgencyLevel.immediate: DecisionTimeHorizon.immediate,
    UrgencyLevel.high: DecisionTimeHorizon.short_term,
    UrgencyLevel.medium: DecisionTimeHorizon.medium_term,
    UrgencyLevel.low: DecisionTimeHorizon.long_term,
    UrgencyLevel.unknown: DecisionTimeHorizon.medium_term,
}


def _require_validated_input(insight: UniversalAIInsight) -> None:
    if insight.validation_status == ValidationStatus.pending:
        raise ValueError(_PENDING_VALIDATION_MESSAGE)


def _text_blob(insight: UniversalAIInsight) -> str:
    return " ".join(
        [
            insight.title,
            insight.summary,
            insight.insight,
            insight.reason,
            insight.business_impact,
            insight.expected_outcome,
            str(insight.metadata.legacy.get("type", "")),
            str(insight.metadata.legacy.get("card_type", "")),
        ]
    ).lower()


def infer_category(insight: UniversalAIInsight) -> tuple[DecisionCategory, str]:
    """Deterministic category inference: metadata -> domain -> risk -> keywords."""
    metadata_category = insight.metadata.custom.get("decision_category") or insight.metadata.legacy.get("category")
    if metadata_category:
        for category in DecisionCategory:
            if category.value.lower() == str(metadata_category).lower() or category.name == str(metadata_category).lower():
                return category, "metadata"

    if insight.domain:
        domain_key = insight.domain.strip().lower()
        if domain_key in _DOMAIN_CATEGORY_MAP:
            return _DOMAIN_CATEGORY_MAP[domain_key], "domain"

    if insight.risk_level in _RISK_CATEGORY_MAP:
        return _RISK_CATEGORY_MAP[insight.risk_level], "risk"

    blob = _text_blob(insight)
    for keyword, category in _KEYWORD_CATEGORY_RULES:
        if keyword in blob:
            return category, "keywords"

    legacy_type = str(insight.metadata.legacy.get("type", "")).lower()
    if legacy_type == "data_quality_score":
        return DecisionCategory.data_quality, "keywords"

    return DecisionCategory.other, "keywords"


def _map_evidence(insight: UniversalAIInsight) -> list[DecisionEvidence]:
    return [
        DecisionEvidence(
            label=item.label,
            value=item.value,
            evidence_type=item.evidence_type,
            source=item.source,
            confidence_score=item.confidence_score,
            raw=item.raw,
        )
        for item in insight.supporting_evidence
    ]


def _expected_outcome_target(
    insight: UniversalAIInsight,
    action: RecommendedAction | None = None,
) -> ExpectedOutcomeTarget | None:
    custom = insight.metadata.custom.get("expected_outcome_target")
    if isinstance(custom, dict):
        return ExpectedOutcomeTarget(
            target_metric=str(custom.get("target_metric") or ""),
            target_value=custom.get("target_value"),
            target_timeframe=str(custom.get("target_timeframe") or ""),
        )

    metric = insight.affected_metrics[0] if insight.affected_metrics else ""
    if not metric and not action:
        return None

    timeframe = ""
    if action and action.urgency == UrgencyLevel.immediate:
        timeframe = DecisionTimeHorizon.immediate.value
    elif action and action.urgency == UrgencyLevel.high:
        timeframe = DecisionTimeHorizon.short_term.value

    if not metric and not timeframe:
        return None

    return ExpectedOutcomeTarget(
        target_metric=str(metric),
        target_value=insight.metadata.custom.get("target_value"),
        target_timeframe=timeframe,
    )


def _primary_action(insight: UniversalAIInsight) -> RecommendedAction | None:
    return insight.recommended_actions[0] if insight.recommended_actions else None


def _map_alternatives(insight: UniversalAIInsight) -> list[DecisionAlternative]:
    alternatives: list[DecisionAlternative] = []
    for action in insight.recommended_actions[1:]:
        alternatives.append(
            DecisionAlternative(
                action=action.action,
                advantages=[action.rationale] if action.rationale else [],
                disadvantages=[item for item in insight.limitations[:1]],
                expected_outcome=action.expected_outcome or action.expected_impact,
                expected_outcome_target=_expected_outcome_target(insight, action),
                estimated_effort=action.estimated_effort,
                confidence=insight.overall_confidence,
            )
        )
    return alternatives


def _implementation_notes(insight: UniversalAIInsight) -> list[str]:
    notes: list[str] = []
    validation_report = insight.metadata.future_extensions.get("validation_engine")
    if isinstance(validation_report, dict):
        notes.extend(str(item) for item in validation_report.get("warnings", [])[:3])
        notes.extend(str(item) for item in validation_report.get("recommendations", [])[:2])
    custom_notes = insight.metadata.custom.get("implementation_notes")
    if isinstance(custom_notes, list):
        notes.extend(str(item) for item in custom_notes)
    elif isinstance(custom_notes, str) and custom_notes.strip():
        notes.append(custom_notes)
    return notes


def _dependency_fields(insight: UniversalAIInsight, decision_id: str) -> tuple[list[str], list[str]]:
    depends_on = [str(item) for item in insight.metadata.custom.get("depends_on", []) if item]
    blocks = [str(item) for item in insight.metadata.custom.get("blocks", []) if item]

    if insight.metadata.custom.get("blocks_other_decisions"):
        blocks.append(decision_id)

    category, _ = infer_category(insight)
    if category == DecisionCategory.data_quality and insight.priority in {InsightPriority.high, InsightPriority.critical}:
        if decision_id not in blocks:
            blocks.append(decision_id)

    return depends_on, blocks


def _infer_time_horizon(insight: UniversalAIInsight, action: RecommendedAction | None) -> DecisionTimeHorizon:
    custom = insight.metadata.custom.get("time_horizon")
    if custom:
        for horizon in DecisionTimeHorizon:
            if horizon.value.lower() == str(custom).lower() or horizon.name == str(custom).lower():
                return horizon

    if action:
        return _URGENCY_HORIZON_MAP.get(action.urgency, DecisionTimeHorizon.medium_term)

    category, _ = infer_category(insight)
    if category == DecisionCategory.risk_mitigation:
        return DecisionTimeHorizon.immediate
    if category == DecisionCategory.strategic_planning:
        return DecisionTimeHorizon.long_term
    if category == DecisionCategory.forecasting:
        return DecisionTimeHorizon.medium_term
    return DecisionTimeHorizon.medium_term


def _evaluate_status(
    *,
    validation_status: ValidationStatus,
    business_reason: str,
    supporting_evidence: list[DecisionEvidence],
    business_impact: str,
    expected_outcome: str,
    recommended_action: str,
    priority: InsightPriority,
    confidence: float,
) -> DecisionStatus:
    if validation_status in _BLOCKED_VALIDATION_STATUSES:
        return DecisionStatus.blocked

    required = [
        business_reason.strip(),
        business_impact.strip(),
        expected_outcome.strip(),
        recommended_action.strip(),
        confidence > 0,
        bool(supporting_evidence),
        priority is not None,
    ]
    if all(required):
        return DecisionStatus.complete
    return DecisionStatus.incomplete


def compute_decision_score(insight: UniversalAIInsight, status: DecisionStatus) -> float:
    if status == DecisionStatus.blocked:
        return 0.0

    score = insight.overall_confidence * 60.0
    score += _PRIORITY_SCORE_BOOST.get(insight.priority, 0.0)
    score += min(len(insight.supporting_evidence) * 5.0, 15.0)

    if insight.validation_status == ValidationStatus.validated:
        validation_report = insight.metadata.future_extensions.get("validation_engine")
        if isinstance(validation_report, dict):
            score += min(float(validation_report.get("score", 0.0)) / 10.0, 10.0)
        else:
            score += 10.0
    elif insight.validation_status == ValidationStatus.insufficient:
        score -= 10.0

    category, _ = infer_category(insight)
    if category == DecisionCategory.risk_mitigation and insight.risk_level in {RiskLevel.high, RiskLevel.critical}:
        score += 5.0

    return round(max(0.0, min(100.0, score)), 2)


def _build_decision_path(
    insight: UniversalAIInsight,
    category: DecisionCategory,
    category_source: str,
    status: DecisionStatus,
) -> list[DecisionPathStep]:
    path = [
        DecisionPathStep(
            step_id="input_validation",
            label="Validated insight input",
            detail=f"Validation status: {insight.validation_status.value}",
            source_field="validation_status",
        ),
        DecisionPathStep(
            step_id="category_inference",
            label="Category inference",
            detail=f"{category.value} inferred from {category_source}",
            source_field="category",
        ),
        DecisionPathStep(
            step_id="evidence_mapping",
            label="Evidence mapping",
            detail=f"{len(insight.supporting_evidence)} evidence item(s) mapped",
            source_field="supporting_evidence",
        ),
        DecisionPathStep(
            step_id="action_selection",
            label="Primary action selection",
            detail="Primary recommendation selected from validated insight actions",
            source_field="recommended_actions",
        ),
        DecisionPathStep(
            step_id="completeness_review",
            label="Completeness review",
            detail=f"Decision marked as {status.value}",
            source_field="status",
        ),
    ]
    return path


def build_decision(
    insight: UniversalAIInsight,
    *,
    source_dataset: str | None = None,
    source_validation_report: dict[str, Any] | None = None,
) -> DecisionRecommendation:
    """Convert one validated UniversalAIInsight into a DecisionRecommendation."""
    _require_validated_input(insight)

    primary = _primary_action(insight)
    evidence = _map_evidence(insight)
    category, category_source = infer_category(insight)
    business_reason = insight.reason.strip()
    business_impact = insight.business_impact.strip()
    expected_outcome = (insight.expected_outcome or (primary.expected_outcome if primary else "")).strip()
    recommended_action = (primary.action if primary else "").strip()
    confidence = insight.overall_confidence
    validation_status = insight.validation_status

    status = _evaluate_status(
        validation_status=validation_status,
        business_reason=business_reason,
        supporting_evidence=evidence,
        business_impact=business_impact,
        expected_outcome=expected_outcome,
        recommended_action=recommended_action,
        priority=insight.priority,
        confidence=confidence,
    )

    decision_id = f"decision_{insight.id}"
    depends_on, blocks = _dependency_fields(insight, decision_id)
    validation_report = source_validation_report
    if validation_report is None:
        raw_report = insight.metadata.future_extensions.get("validation_engine")
        validation_report = raw_report if isinstance(raw_report, dict) else None

    estimated_value = str(insight.metadata.custom.get("estimated_value") or "")

    decision = DecisionRecommendation(
        decision_id=decision_id,
        title=insight.title,
        summary=insight.summary,
        recommended_action=recommended_action,
        business_reason=business_reason,
        expected_outcome=expected_outcome,
        expected_outcome_target=_expected_outcome_target(insight, primary),
        business_impact=business_impact,
        priority=insight.priority,
        urgency=primary.urgency if primary else UrgencyLevel.unknown,
        risk_level=insight.risk_level,
        estimated_effort=primary.estimated_effort if primary else insight.metadata.custom.get("estimated_effort", "unknown"),
        estimated_value=estimated_value,
        confidence=confidence,
        supporting_evidence=evidence,
        affected_metrics=list(insight.affected_metrics),
        related_kpis=list(insight.related_kpis),
        related_charts=list(insight.related_charts),
        assumptions=list(insight.assumptions),
        limitations=list(insight.limitations),
        implementation_notes=_implementation_notes(insight),
        validation_status=validation_status,
        category=category,
        status=status,
        time_horizon=_infer_time_horizon(insight, primary),
        alternatives=_map_alternatives(insight),
        depends_on=depends_on,
        blocks=blocks,
        decision_score=compute_decision_score(insight, status),
        decision_path=_build_decision_path(insight, category, category_source, status),
        source_insight_id=insight.id,
        source_dataset=source_dataset or insight.metadata.custom.get("dataset_id"),
        source_validation_report=validation_report,
        source_schema_version=insight.schema_version,
        generated_at=utc_now_iso(),
        metadata=DecisionMetadata(
            legacy={"source_insight_id": insight.id, "category_source": category_source},
            debug={"insight_generated_by": insight.generated_by.model_dump()},
            custom=dict(insight.metadata.custom),
            future_extensions={
                "prediction": {},
                "simulation": {},
                "workflow": {},
                "approval": {},
                "automation": {},
            },
        ),
    )

    if primary and isinstance(primary.estimated_effort, str):
        pass
    elif not primary:
        from backend.models.ai_insight_models import EffortLevel

        effort_value = insight.metadata.custom.get("estimated_effort")
        if effort_value:
            for effort in EffortLevel:
                if effort.value == str(effort_value).lower():
                    decision.estimated_effort = effort
                    break

    return decision


def rank_decisions(decisions: list[DecisionRecommendation]) -> list[DecisionRecommendation]:
    """Return a new ranked list without mutating the original decisions."""
    ranked = sorted(
        decisions,
        key=lambda item: (
            item.status != DecisionStatus.complete,
            item.status == DecisionStatus.blocked,
            -item.decision_score,
            -item.confidence,
            item.priority.value,
        ),
    )
    return [item.model_copy(update={"decision_rank": index + 1}, deep=True) for index, item in enumerate(ranked)]


def prioritize_decisions(decisions: list[DecisionRecommendation]) -> list[DecisionRecommendation]:
    """Alias for rank_decisions to make priority ordering explicit."""
    return rank_decisions(decisions)


def group_by_category(decisions: list[DecisionRecommendation]) -> dict[str, list[DecisionRecommendation]]:
    grouped: dict[str, list[DecisionRecommendation]] = {}
    for decision in decisions:
        key = decision.category.value
        grouped.setdefault(key, []).append(decision.model_copy(deep=True))
    return grouped


def summarize_decisions(decisions: list[DecisionRecommendation]) -> DecisionSummary:
    complete = [item for item in decisions if item.status == DecisionStatus.complete]
    incomplete = [item for item in decisions if item.status == DecisionStatus.incomplete]
    blocked = [item for item in decisions if item.status == DecisionStatus.blocked]
    ranked = rank_decisions(decisions)
    top = ranked[0] if ranked else None

    category_breakdown: dict[str, int] = {}
    for decision in decisions:
        category_breakdown[decision.category.value] = category_breakdown.get(decision.category.value, 0) + 1

    top_risks = [
        item.title
        for item in ranked
        if item.category == DecisionCategory.risk_mitigation or item.risk_level in {RiskLevel.high, RiskLevel.critical}
    ][:3]
    top_opportunities = [
        item.title for item in ranked if item.category in {DecisionCategory.revenue_growth, DecisionCategory.customer_experience}
    ][:3]
    quick_wins = [
        item.recommended_action
        for item in ranked
        if item.status == DecisionStatus.complete and item.time_horizon in {DecisionTimeHorizon.immediate, DecisionTimeHorizon.short_term}
    ][:3]
    strategic_actions = [
        item.recommended_action
        for item in ranked
        if item.category == DecisionCategory.strategic_planning or item.time_horizon == DecisionTimeHorizon.long_term
    ][:3]

    if complete and top:
        overall_health = "stable"
        if any(item.risk_level in {RiskLevel.high, RiskLevel.critical} for item in complete):
            overall_health = "at_risk"
        elif any(item.category == DecisionCategory.revenue_growth for item in complete):
            overall_health = "growth_focused"
    elif incomplete:
        overall_health = "needs_attention"
    else:
        overall_health = "blocked"

    return DecisionSummary(
        total_decisions=len(decisions),
        complete_count=len(complete),
        incomplete_count=len(incomplete),
        blocked_count=len(blocked),
        top_priority_decision_id=top.decision_id if top else None,
        category_breakdown=category_breakdown,
        headline=top.title if top else "No decision recommendations available.",
        executive_note=top.summary if top else "",
        overall_business_health=overall_health,
        top_risks=top_risks,
        top_opportunities=top_opportunities,
        quick_wins=[item for item in quick_wins if item],
        strategic_actions=[item for item in strategic_actions if item],
    )


def build_decision_collection(
    insights: list[UniversalAIInsight],
    *,
    dataset_id: str | None = None,
    domain: str | None = None,
    source_dataset: str | None = None,
) -> DecisionCollection:
    """Build a ranked decision collection from validated insights."""
    decisions = [
        build_decision(
            insight,
            source_dataset=source_dataset or dataset_id,
        )
        for insight in insights
        if insight.validation_status != ValidationStatus.pending
    ]
    ranked = rank_decisions(decisions)
    resolved_domain = domain or next((item.domain for item in insights if item.domain), None)
    return DecisionCollection(
        dataset_id=dataset_id or source_dataset,
        domain=resolved_domain,
        decisions=ranked,
        summary=summarize_decisions(ranked),
        generated_at=utc_now_iso(),
        metadata=DecisionMetadata(
            legacy={"schema": DECISION_SCHEMA_VERSION},
            debug={"insight_count": len(insights), "decision_count": len(ranked)},
            custom={},
            future_extensions={
                "prediction": {},
                "simulation": {},
                "workflow": {},
                "approval": {},
                "automation": {},
            },
        ),
    )
