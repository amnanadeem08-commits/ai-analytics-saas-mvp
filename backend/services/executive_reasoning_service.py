from __future__ import annotations

from typing import Any

from backend.models.ai_insight_models import (
    InsightPriority,
    RiskLevel,
    UniversalAIInsight,
    ValidationStatus,
    utc_now_iso,
)
from backend.models.decision_models import DecisionRecommendation, DecisionStatus, DecisionTimeHorizon
from backend.models.executive_reasoning_models import (
    EXECUTIVE_REASONING_SCHEMA_VERSION,
    ExecutiveFinding,
    ExecutiveFindingType,
    ExecutiveMetadata,
    ExecutiveNarrative,
    ExecutiveOpportunity,
    ExecutivePriority,
    ExecutiveReasoning,
    ExecutiveReasoningCollection,
    ExecutiveReasoningSummary,
    ExecutiveRecommendation,
    ExecutiveRisk,
    empty_executive_future_extensions,
)
from backend.models.root_cause_models import CauseSeverity, CauseStatus, RootCause
from backend.models.validation_models import ValidationReport

_PRIORITY_ORDER = {
    InsightPriority.critical: 0,
    InsightPriority.high: 1,
    InsightPriority.medium: 2,
    InsightPriority.low: 3,
}

_SEVERITY_TO_RISK = {
    CauseSeverity.info: RiskLevel.info,
    CauseSeverity.low: RiskLevel.low,
    CauseSeverity.medium: RiskLevel.medium,
    CauseSeverity.high: RiskLevel.high,
    CauseSeverity.critical: RiskLevel.critical,
}

_RISK_RANK = {
    RiskLevel.critical: 0,
    RiskLevel.high: 1,
    RiskLevel.medium: 2,
    RiskLevel.low: 3,
    RiskLevel.info: 4,
}


def _deep_copy_insight(insight: UniversalAIInsight | None) -> UniversalAIInsight | None:
    return insight.model_copy(deep=True) if insight is not None else None


def _deep_copy_decision(decision: DecisionRecommendation | None) -> DecisionRecommendation | None:
    return decision.model_copy(deep=True) if decision is not None else None


def _deep_copy_root_cause(root_cause: RootCause | None) -> RootCause | None:
    return root_cause.model_copy(deep=True) if root_cause is not None else None


def _deep_copy_validation(report: ValidationReport | None) -> ValidationReport | None:
    return report.model_copy(deep=True) if report is not None else None


def _validation_report_id(report: ValidationReport | None) -> str | None:
    if report is None:
        return None
    return f"validation_{report.validator_version}_{report.validated_at}"


def _resolve_validation_status(
    insight: UniversalAIInsight | None,
    decision: DecisionRecommendation | None,
    validation: ValidationReport | None,
) -> ValidationStatus:
    if validation is not None:
        return validation.overall_status
    if insight is not None:
        return insight.validation_status
    if decision is not None:
        return decision.validation_status
    return ValidationStatus.pending


def compute_executive_confidence(
    insight: UniversalAIInsight | None,
    decision: DecisionRecommendation | None,
    root_cause: RootCause | None,
    validation: ValidationReport | None,
) -> float:
    """Derive executive confidence from trusted components; never exceed the lowest trusted score."""
    scores: list[float] = []
    if insight is not None and insight.overall_confidence > 0:
        scores.append(insight.overall_confidence)
    if decision is not None and decision.confidence > 0:
        scores.append(decision.confidence)
    if root_cause is not None and root_cause.confidence > 0:
        scores.append(root_cause.confidence)
    if validation is not None:
        scores.append(max(0.0, min(1.0, validation.score / 100.0)))
    if not scores:
        return 0.0
    return round(min(scores), 4)


def extract_executive_findings(
    insight: UniversalAIInsight | None = None,
    decision: DecisionRecommendation | None = None,
    root_cause: RootCause | None = None,
    validation: ValidationReport | None = None,
) -> list[ExecutiveFinding]:
    """Extract findings only from provided validated objects — no fabrication."""
    findings: list[ExecutiveFinding] = []
    insight_ids = [insight.id] if insight is not None else []
    decision_ids = [decision.decision_id] if decision is not None else []
    root_ids = [root_cause.root_cause_id] if root_cause is not None else []
    validation_ids = [_validation_report_id(validation)] if validation is not None else []
    validation_ids = [item for item in validation_ids if item]

    if insight is not None and (insight.insight.strip() or insight.summary.strip()):
        findings.append(
            ExecutiveFinding(
                finding_id=f"finding_what_{insight.id}",
                finding_type=ExecutiveFindingType.what_happened,
                title="What happened",
                statement=insight.insight.strip() or insight.summary.strip(),
                source_insight_ids=insight_ids,
                confidence=insight.overall_confidence,
            )
        )
    if root_cause is not None and root_cause.description.strip():
        findings.append(
            ExecutiveFinding(
                finding_id=f"finding_why_{root_cause.root_cause_id}",
                finding_type=ExecutiveFindingType.why_it_happened,
                title="Why it happened",
                statement=root_cause.description.strip(),
                source_insight_ids=insight_ids,
                source_root_cause_ids=root_ids,
                confidence=root_cause.confidence,
            )
        )
    elif insight is not None and insight.reason.strip():
        findings.append(
            ExecutiveFinding(
                finding_id=f"finding_why_{insight.id}",
                finding_type=ExecutiveFindingType.why_it_happened,
                title="Why it happened",
                statement=insight.reason.strip(),
                source_insight_ids=insight_ids,
                confidence=insight.overall_confidence,
            )
        )

    impact = ""
    if decision is not None and decision.business_impact.strip():
        impact = decision.business_impact.strip()
    elif insight is not None and insight.business_impact.strip():
        impact = insight.business_impact.strip()
    if impact:
        findings.append(
            ExecutiveFinding(
                finding_id=f"finding_impact_{insight.id if insight else decision.decision_id if decision else 'unknown'}",
                finding_type=ExecutiveFindingType.business_impact,
                title="Business impact",
                statement=impact,
                source_insight_ids=insight_ids,
                source_decision_ids=decision_ids,
                confidence=decision.confidence if decision is not None else (insight.overall_confidence if insight else 0.0),
            )
        )

    if validation is not None and validation.warnings:
        findings.append(
            ExecutiveFinding(
                finding_id=f"finding_validation_{validation.validated_at}",
                finding_type=ExecutiveFindingType.validation,
                title="Validation warnings",
                statement="; ".join(validation.warnings[:5]),
                source_validation_report_ids=validation_ids,
                confidence=max(0.0, min(1.0, validation.score / 100.0)),
            )
        )
    return findings


def extract_executive_risks(
    insight: UniversalAIInsight | None = None,
    decision: DecisionRecommendation | None = None,
    root_cause: RootCause | None = None,
    validation: ValidationReport | None = None,
) -> list[ExecutiveRisk]:
    """Merge decision risks, root-cause severity, and validation warnings — no invention."""
    risks: list[ExecutiveRisk] = []
    decision_ids = [decision.decision_id] if decision is not None else []
    root_ids = [root_cause.root_cause_id] if root_cause is not None else []
    warnings = list(validation.warnings) if validation is not None else []

    if decision is not None and decision.risk_level in {RiskLevel.high, RiskLevel.critical, RiskLevel.medium}:
        risks.append(
            ExecutiveRisk(
                risk_id=f"risk_decision_{decision.decision_id}",
                title=decision.title,
                description=decision.business_impact or decision.business_reason or decision.summary,
                severity=decision.risk_level,
                source_decision_ids=decision_ids,
                source_validation_warnings=warnings[:3],
                confidence=decision.confidence,
            )
        )
    elif decision is not None and decision.category.value.lower().find("risk") >= 0:
        risks.append(
            ExecutiveRisk(
                risk_id=f"risk_decision_cat_{decision.decision_id}",
                title=decision.title,
                description=decision.summary or decision.business_reason,
                severity=decision.risk_level,
                source_decision_ids=decision_ids,
                confidence=decision.confidence,
            )
        )

    if root_cause is not None and root_cause.severity in {
        CauseSeverity.high,
        CauseSeverity.critical,
        CauseSeverity.medium,
    }:
        risks.append(
            ExecutiveRisk(
                risk_id=f"risk_rca_{root_cause.root_cause_id}",
                title=root_cause.title,
                description=root_cause.description or root_cause.summary,
                severity=_SEVERITY_TO_RISK.get(root_cause.severity, RiskLevel.info),
                source_root_cause_ids=root_ids,
                source_decision_ids=decision_ids,
                source_validation_warnings=warnings[:3],
                confidence=root_cause.confidence,
            )
        )

    if insight is not None and insight.risk_level in {RiskLevel.high, RiskLevel.critical}:
        risks.append(
            ExecutiveRisk(
                risk_id=f"risk_insight_{insight.id}",
                title=insight.title,
                description=insight.business_impact or insight.summary,
                severity=insight.risk_level,
                source_decision_ids=decision_ids,
                confidence=insight.overall_confidence,
            )
        )

    if validation is not None:
        for index, warning in enumerate(validation.warnings[:5]):
            risks.append(
                ExecutiveRisk(
                    risk_id=f"risk_validation_{index}",
                    title="Validation warning",
                    description=str(warning),
                    severity=RiskLevel.medium,
                    source_validation_warnings=[str(warning)],
                    confidence=max(0.0, min(1.0, validation.score / 100.0)),
                )
            )

    # Deduplicate by title+description while preserving order
    seen: set[str] = set()
    unique: list[ExecutiveRisk] = []
    for risk in sorted(risks, key=lambda item: (_RISK_RANK.get(item.severity, 99), -item.confidence)):
        key = f"{risk.title}|{risk.description}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(risk)
    return unique


def extract_executive_opportunities(
    insight: UniversalAIInsight | None = None,
    decision: DecisionRecommendation | None = None,
    root_cause: RootCause | None = None,
) -> list[ExecutiveOpportunity]:
    """Merge opportunities from decisions and insights only — no invention."""
    opportunities: list[ExecutiveOpportunity] = []
    insight_ids = [insight.id] if insight is not None else []
    decision_ids = [decision.decision_id] if decision is not None else []

    if decision is not None:
        is_opportunity_category = decision.category.value in {
            "Revenue Growth",
            "Customer Experience",
            "Operational Improvement",
            "Strategic Planning",
            "Cost Reduction",
        }
        is_quick_win = decision.time_horizon in {
            DecisionTimeHorizon.immediate,
            DecisionTimeHorizon.short_term,
        }
        if is_opportunity_category or is_quick_win or decision.expected_outcome.strip():
            opportunities.append(
                ExecutiveOpportunity(
                    opportunity_id=f"opp_decision_{decision.decision_id}",
                    title=decision.title,
                    description=decision.business_impact or decision.summary,
                    expected_outcome=decision.expected_outcome,
                    source_decision_ids=decision_ids,
                    source_insight_ids=insight_ids,
                    time_horizon=decision.time_horizon.value,
                    confidence=decision.confidence,
                )
            )
        for index, alternative in enumerate(decision.alternatives):
            if alternative.action.strip():
                opportunities.append(
                    ExecutiveOpportunity(
                        opportunity_id=f"opp_alt_{decision.decision_id}_{index}",
                        title=alternative.action,
                        description="; ".join(alternative.advantages) if alternative.advantages else alternative.action,
                        expected_outcome=alternative.expected_outcome,
                        source_decision_ids=decision_ids,
                        time_horizon=decision.time_horizon.value,
                        confidence=alternative.confidence,
                    )
                )

    if insight is not None and insight.expected_outcome.strip():
        opportunities.append(
            ExecutiveOpportunity(
                opportunity_id=f"opp_insight_{insight.id}",
                title=insight.title,
                description=insight.summary or insight.insight,
                expected_outcome=insight.expected_outcome,
                source_insight_ids=insight_ids,
                confidence=insight.overall_confidence,
            )
        )

    # Root-cause quick fixes / long-term items only when present in metadata (no invention)
    if root_cause is not None:
        quick_fixes = root_cause.metadata.custom.get("quick_fixes")
        if isinstance(quick_fixes, list):
            for index, fix in enumerate(quick_fixes):
                if str(fix).strip():
                    opportunities.append(
                        ExecutiveOpportunity(
                            opportunity_id=f"opp_rca_fix_{root_cause.root_cause_id}_{index}",
                            title=str(fix),
                            description=str(fix),
                            expected_outcome=str(fix),
                            source_insight_ids=insight_ids,
                            confidence=root_cause.confidence,
                            time_horizon=DecisionTimeHorizon.short_term.value,
                        )
                    )

    seen: set[str] = set()
    unique: list[ExecutiveOpportunity] = []
    for item in opportunities:
        key = f"{item.title}|{item.expected_outcome}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _prioritize_recommendations(
    decisions: list[DecisionRecommendation],
) -> list[ExecutiveRecommendation]:
    """Prioritize existing DecisionRecommendations only — never create new ones."""
    eligible = [
        item
        for item in decisions
        if item.status != DecisionStatus.blocked and item.recommended_action.strip()
    ]
    ordered = sorted(
        eligible,
        key=lambda item: (
            _PRIORITY_ORDER.get(item.priority, 99),
            -item.decision_score,
            -item.confidence,
        ),
    )
    result: list[ExecutiveRecommendation] = []
    for index, decision in enumerate(ordered):
        result.append(
            ExecutiveRecommendation(
                recommendation_id=f"exec_rec_{decision.decision_id}",
                decision_id=decision.decision_id,
                title=decision.title,
                recommended_action=decision.recommended_action,
                business_reason=decision.business_reason,
                expected_outcome=decision.expected_outcome,
                business_impact=decision.business_impact,
                priority=decision.priority,
                decision_score=decision.decision_score,
                confidence=decision.confidence,
                rank=index + 1,
            )
        )
    return result


def _build_priorities(
    recommendations: list[ExecutiveRecommendation],
) -> list[ExecutivePriority]:
    priorities: list[ExecutivePriority] = []
    for index, recommendation in enumerate(recommendations[:5]):
        priorities.append(
            ExecutivePriority(
                priority_id=f"priority_{recommendation.decision_id}",
                label=recommendation.recommended_action,
                rationale=recommendation.business_reason or recommendation.business_impact or recommendation.title,
                linked_decision_ids=[recommendation.decision_id],
                order=index + 1,
            )
        )
    return priorities


def _build_narrative(
    insight: UniversalAIInsight | None,
    decision: DecisionRecommendation | None,
    root_cause: RootCause | None,
    validation: ValidationReport | None,
    recommendations: list[ExecutiveRecommendation],
    risks: list[ExecutiveRisk],
    opportunities: list[ExecutiveOpportunity],
    executive_confidence: float,
) -> ExecutiveNarrative:
    what = ""
    if insight is not None:
        what = insight.insight.strip() or insight.summary.strip()
    why = ""
    if root_cause is not None and root_cause.description.strip():
        why = root_cause.description.strip()
    elif insight is not None:
        why = insight.reason.strip()
    impact = ""
    if decision is not None and decision.business_impact.strip():
        impact = decision.business_impact.strip()
    elif insight is not None:
        impact = insight.business_impact.strip()
    recommended = recommendations[0].recommended_action if recommendations else ""
    status = _resolve_validation_status(insight, decision, validation)
    return ExecutiveNarrative(
        what_happened=what,
        why_it_happened=why,
        business_impact=impact,
        recommended_priority=recommended,
        confidence_statement=f"Executive confidence {executive_confidence:.2f} derived from validated components.",
        validation_status=status,
        top_risks=[item.title for item in risks[:3]],
        top_opportunities=[item.title for item in opportunities[:3]],
    )


def _compose_executive_summary(narrative: ExecutiveNarrative) -> str:
    parts = [
        f"What happened: {narrative.what_happened}" if narrative.what_happened else "",
        f"Why it happened: {narrative.why_it_happened}" if narrative.why_it_happened else "",
        f"Business impact: {narrative.business_impact}" if narrative.business_impact else "",
        f"Recommended priority: {narrative.recommended_priority}" if narrative.recommended_priority else "",
        narrative.confidence_statement,
        f"Validation status: {narrative.validation_status.value}",
    ]
    if narrative.top_risks:
        parts.append(f"Top risks: {'; '.join(narrative.top_risks)}")
    if narrative.top_opportunities:
        parts.append(f"Top opportunities: {'; '.join(narrative.top_opportunities)}")
    return " ".join(part for part in parts if part).strip()


def build_executive_reasoning(
    insight: UniversalAIInsight | None = None,
    decision: DecisionRecommendation | None = None,
    root_cause: RootCause | None = None,
    validation: ValidationReport | None = None,
    *,
    dataset_id: str | None = None,
    domain: str | None = None,
) -> ExecutiveReasoning:
    """Orchestrate validated insight, validation, decision, and RCA into one executive object."""
    if insight is None and decision is None and root_cause is None:
        raise ValueError("At least one of insight, decision, or root_cause is required.")

    insight_c = _deep_copy_insight(insight)
    decision_c = _deep_copy_decision(decision)
    root_cause_c = _deep_copy_root_cause(root_cause)
    validation_c = _deep_copy_validation(validation)

    decisions = [decision_c] if decision_c is not None else []
    recommendations = _prioritize_recommendations(decisions)
    findings = extract_executive_findings(insight_c, decision_c, root_cause_c, validation_c)
    risks = extract_executive_risks(insight_c, decision_c, root_cause_c, validation_c)
    opportunities = extract_executive_opportunities(insight_c, decision_c, root_cause_c)
    priorities = _build_priorities(recommendations)
    executive_confidence = compute_executive_confidence(insight_c, decision_c, root_cause_c, validation_c)
    narrative = _build_narrative(
        insight_c,
        decision_c,
        root_cause_c,
        validation_c,
        recommendations,
        risks,
        opportunities,
        executive_confidence,
    )

    linked_insight_ids = [insight_c.id] if insight_c is not None else []
    linked_decision_ids = [decision_c.decision_id] if decision_c is not None else []
    linked_root_cause_ids = [root_cause_c.root_cause_id] if root_cause_c is not None else []
    validation_id = _validation_report_id(validation_c)
    linked_validation_ids = [validation_id] if validation_id else []

    reasoning_id_seed = (
        (insight_c.id if insight_c else None)
        or (decision_c.decision_id if decision_c else None)
        or (root_cause_c.root_cause_id if root_cause_c else "unknown")
    )
    headline = ""
    if insight_c is not None:
        headline = insight_c.title
    elif decision_c is not None:
        headline = decision_c.title
    elif root_cause_c is not None:
        headline = root_cause_c.title

    resolved_domain = domain
    if resolved_domain is None and insight_c is not None:
        resolved_domain = insight_c.domain
    if resolved_domain is None and decision_c is not None:
        resolved_domain = decision_c.category.value
    if resolved_domain is None and root_cause_c is not None:
        resolved_domain = root_cause_c.business_area

    resolved_dataset = dataset_id
    if resolved_dataset is None and insight_c is not None:
        resolved_dataset = insight_c.metadata.custom.get("dataset_id")
    if resolved_dataset is None and decision_c is not None:
        resolved_dataset = decision_c.source_dataset

    business_context = ""
    if insight_c is not None and insight_c.domain:
        business_context = f"Domain: {insight_c.domain}"
    elif decision_c is not None:
        business_context = f"Decision category: {decision_c.category.value}"

    return ExecutiveReasoning(
        reasoning_id=f"exec_{reasoning_id_seed}",
        dataset_id=str(resolved_dataset) if resolved_dataset else None,
        domain=resolved_domain,
        headline=headline,
        executive_summary=_compose_executive_summary(narrative),
        business_context=business_context,
        narrative=narrative,
        key_findings=findings,
        key_risks=risks,
        key_opportunities=opportunities,
        recommended_priorities=priorities,
        prioritized_recommendations=recommendations,
        executive_confidence=executive_confidence,
        overall_validation_status=_resolve_validation_status(insight_c, decision_c, validation_c),
        linked_insight_ids=linked_insight_ids,
        linked_decision_ids=linked_decision_ids,
        linked_root_cause_ids=linked_root_cause_ids,
        generated_at=utc_now_iso(),
        metadata=ExecutiveMetadata(
            legacy={"schema": EXECUTIVE_REASONING_SCHEMA_VERSION},
            debug={
                "has_insight": insight_c is not None,
                "has_decision": decision_c is not None,
                "has_root_cause": root_cause_c is not None,
                "has_validation": validation_c is not None,
            },
            custom={},
            future_extensions=empty_executive_future_extensions(),
            linked_insight_ids=linked_insight_ids,
            linked_decision_ids=linked_decision_ids,
            linked_root_cause_ids=linked_root_cause_ids,
            linked_validation_report_ids=linked_validation_ids,
        ),
    )


def rank_reasoning(reasonings: list[ExecutiveReasoning]) -> list[ExecutiveReasoning]:
    def _sort_key(item: ExecutiveReasoning) -> tuple:
        top_priority = 99
        top_score = 0.0
        if item.prioritized_recommendations:
            top = item.prioritized_recommendations[0]
            top_priority = _PRIORITY_ORDER.get(top.priority, 99)
            top_score = top.decision_score
        return (
            -item.executive_confidence,
            top_priority,
            -top_score,
            0 if item.prioritized_recommendations else 1,
            item.headline,
        )

    ordered = sorted(reasonings, key=_sort_key)
    return [
        item.model_copy(update={"reasoning_rank": index + 1}, deep=True)
        for index, item in enumerate(ordered)
    ]


def group_reasoning_by_domain(reasonings: list[ExecutiveReasoning]) -> dict[str, list[ExecutiveReasoning]]:
    grouped: dict[str, list[ExecutiveReasoning]] = {}
    for item in reasonings:
        key = item.domain or "Unknown"
        grouped.setdefault(key, []).append(item.model_copy(deep=True))
    return grouped


def summarize_reasoning(reasonings: list[ExecutiveReasoning]) -> ExecutiveReasoningSummary:
    ranked = rank_reasoning(reasonings)
    domains = sorted({item.domain for item in reasonings if item.domain})
    status_breakdown: dict[str, int] = {}
    for item in reasonings:
        key = item.overall_validation_status.value
        status_breakdown[key] = status_breakdown.get(key, 0) + 1

    top = ranked[0] if ranked else None
    avg_confidence = (
        round(sum(item.executive_confidence for item in reasonings) / len(reasonings), 4)
        if reasonings
        else 0.0
    )
    return ExecutiveReasoningSummary(
        total_reasonings=len(reasonings),
        domains=domains,
        headline=top.headline if top else "",
        top_priority_action=(
            top.prioritized_recommendations[0].recommended_action
            if top and top.prioritized_recommendations
            else ""
        ),
        top_risk=top.key_risks[0].title if top and top.key_risks else "",
        top_opportunity=top.key_opportunities[0].title if top and top.key_opportunities else "",
        average_executive_confidence=avg_confidence,
        validation_status_breakdown=status_breakdown,
    )


def build_reasoning_collection(
    reasonings: list[ExecutiveReasoning] | None = None,
    *,
    insights: list[UniversalAIInsight] | None = None,
    decisions: list[DecisionRecommendation] | None = None,
    root_causes: list[RootCause] | None = None,
    validations: list[ValidationReport] | None = None,
    dataset_id: str | None = None,
    domain: str | None = None,
) -> ExecutiveReasoningCollection:
    """Build a ranked collection from prebuilt reasonings or aligned upstream objects."""
    built = [item.model_copy(deep=True) for item in (reasonings or [])]

    if not built and insights:
        decision_by_insight = {
            item.source_insight_id: item for item in (decisions or []) if item.source_insight_id
        }
        rca_by_insight = {
            item.source_insight_id: item for item in (root_causes or []) if item.source_insight_id
        }
        validation_by_index = list(validations or [])
        for index, insight in enumerate(insights):
            validation = validation_by_index[index] if index < len(validation_by_index) else None
            if validation is None:
                raw = insight.metadata.future_extensions.get("validation_engine")
                if isinstance(raw, dict) and "overall_status" in raw:
                    try:
                        validation = ValidationReport.model_validate(raw)
                    except Exception:
                        validation = None
            built.append(
                build_executive_reasoning(
                    insight=insight,
                    decision=decision_by_insight.get(insight.id),
                    root_cause=rca_by_insight.get(insight.id),
                    validation=validation,
                    dataset_id=dataset_id,
                    domain=domain or insight.domain,
                )
            )

    ranked = rank_reasoning(built)
    resolved_domain = domain or next((item.domain for item in ranked if item.domain), None)
    resolved_dataset = dataset_id or next((item.dataset_id for item in ranked if item.dataset_id), None)
    return ExecutiveReasoningCollection(
        dataset_id=resolved_dataset,
        domain=resolved_domain,
        reasonings=ranked,
        summary=summarize_reasoning(ranked),
        generated_at=utc_now_iso(),
        metadata=ExecutiveMetadata(
            legacy={"schema": EXECUTIVE_REASONING_SCHEMA_VERSION},
            debug={"reasoning_count": len(ranked)},
            custom={},
            future_extensions=empty_executive_future_extensions(),
            linked_insight_ids=[insight_id for item in ranked for insight_id in item.linked_insight_ids],
            linked_decision_ids=[decision_id for item in ranked for decision_id in item.linked_decision_ids],
            linked_root_cause_ids=[rca_id for item in ranked for rca_id in item.linked_root_cause_ids],
            linked_validation_report_ids=[
                report_id
                for item in ranked
                for report_id in item.metadata.linked_validation_report_ids
            ],
        ),
    )
