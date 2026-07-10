from __future__ import annotations

from typing import Any

from backend.models.ai_analyst_models import (
    AI_ANALYST_SCHEMA_VERSION,
    AIAnalystResponse,
    ActionPlan,
    AnalystMetadata,
    AnalystResponseMode,
    AnalystTraceability,
    BusinessExplanation,
    ConversationContext,
    EvidenceReference,
    ExecutiveAnswer,
    FollowUpQuestion,
    empty_ai_analyst_future_extensions,
)
from backend.models.ai_insight_models import UniversalAIInsightCollection, utc_now_iso
from backend.models.decision_models import DecisionCollection, DecisionRecommendation
from backend.models.executive_reasoning_models import (
    ExecutiveReasoning,
    ExecutiveReasoningCollection,
)
from backend.models.intelligence_bundle_models import IntelligenceBundle
from backend.models.intelligence_registry_models import IntelligenceRegistry
from backend.models.root_cause_models import RootCause, RootCauseCollection
from backend.models.storyboard_models import ExecutiveStoryboard
from backend.models.validation_models import ValidationReport

_UNAVAILABLE = "unavailable"


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _validation_id(report: ValidationReport) -> str:
    return f"validation_{report.validator_version}_{report.validated_at}"


def _text_or_unavailable(value: str | None) -> str:
    if value is None or not str(value).strip():
        return _UNAVAILABLE
    return str(value).strip()


def _resolve_sources(
    *,
    bundle: IntelligenceBundle | None,
    registry: IntelligenceRegistry | None,
    storyboard: ExecutiveStoryboard | None,
    reasonings: ExecutiveReasoningCollection | None,
    decisions: DecisionCollection | None,
    root_causes: RootCauseCollection | None,
    validations: list[ValidationReport] | None,
    insights: UniversalAIInsightCollection | None,
) -> tuple[
    IntelligenceBundle | None,
    IntelligenceRegistry | None,
    ExecutiveStoryboard | None,
    ExecutiveReasoningCollection | None,
    DecisionCollection | None,
    RootCauseCollection | None,
    list[ValidationReport],
    UniversalAIInsightCollection | None,
]:
    """Prefer explicit args; fall back to bundle-held collections. Deep-copy all."""
    bundle_c = bundle.model_copy(deep=True) if bundle is not None else None
    registry_c = registry.model_copy(deep=True) if registry is not None else None
    storyboard_c = (
        storyboard.model_copy(deep=True)
        if storyboard is not None
        else (bundle_c.storyboard.model_copy(deep=True) if bundle_c and bundle_c.storyboard else None)
    )
    reasonings_c = (
        reasonings.model_copy(deep=True)
        if reasonings is not None
        else (bundle_c.reasonings.model_copy(deep=True) if bundle_c and bundle_c.reasonings else None)
    )
    decisions_c = (
        decisions.model_copy(deep=True)
        if decisions is not None
        else (bundle_c.decisions.model_copy(deep=True) if bundle_c and bundle_c.decisions else None)
    )
    root_causes_c = (
        root_causes.model_copy(deep=True)
        if root_causes is not None
        else (bundle_c.root_causes.model_copy(deep=True) if bundle_c and bundle_c.root_causes else None)
    )
    if validations is not None:
        validations_c = [item.model_copy(deep=True) for item in validations]
    elif bundle_c is not None:
        validations_c = [item.model_copy(deep=True) for item in bundle_c.validations]
    else:
        validations_c = []
    insights_c = (
        insights.model_copy(deep=True)
        if insights is not None
        else (bundle_c.insights.model_copy(deep=True) if bundle_c and bundle_c.insights else None)
    )
    return (
        bundle_c,
        registry_c,
        storyboard_c,
        reasonings_c,
        decisions_c,
        root_causes_c,
        validations_c,
        insights_c,
    )


def _primary_reasoning(
    reasonings: ExecutiveReasoningCollection | None,
) -> ExecutiveReasoning | None:
    if reasonings is None or not reasonings.reasonings:
        return None
    ranked = sorted(
        reasonings.reasonings,
        key=lambda item: (item.reasoning_rank is None, item.reasoning_rank or 0),
    )
    return ranked[0]


def _build_traceability(
    *,
    bundle: IntelligenceBundle | None,
    registry: IntelligenceRegistry | None,
    storyboard: ExecutiveStoryboard | None,
    reasonings: ExecutiveReasoningCollection | None,
    decisions: DecisionCollection | None,
    root_causes: RootCauseCollection | None,
    validations: list[ValidationReport],
    insights: UniversalAIInsightCollection | None,
) -> AnalystTraceability:
    reasoning_ids: list[str] = []
    decision_ids: list[str] = []
    root_ids: list[str] = []
    validation_ids: list[str] = []
    insight_ids: list[str] = []
    registry_refs: list[str] = []

    if reasonings is not None:
        reasoning_ids.extend(item.reasoning_id for item in reasonings.reasonings)
    if decisions is not None:
        decision_ids.extend(item.decision_id for item in decisions.decisions)
    if root_causes is not None:
        root_ids.extend(item.root_cause_id for item in root_causes.root_causes)
    if insights is not None:
        insight_ids.extend(item.id for item in insights.insights)
    validation_ids.extend(_validation_id(item) for item in validations)

    if bundle is not None:
        reasoning_ids.extend(bundle.references.reasoning_ids)
        decision_ids.extend(bundle.references.decision_ids)
        root_ids.extend(bundle.references.root_cause_ids)
        validation_ids.extend(bundle.references.validation_ids)
        insight_ids.extend(bundle.references.insight_ids)

    if registry is not None:
        registry_refs.extend(
            asset.reference_id or asset.object_id for asset in registry.assets
        )

    return AnalystTraceability(
        source_bundle=bundle.bundle_id if bundle is not None else None,
        source_storyboard=storyboard.storyboard_id if storyboard is not None else None,
        source_reasoning=_unique(reasoning_ids),
        source_decisions=_unique(decision_ids),
        source_root_causes=_unique(root_ids),
        source_validation=_unique(validation_ids),
        source_insights=_unique(insight_ids),
        registry_reference_ids=_unique(registry_refs),
    )


def _evidence_from_decision(decision: DecisionRecommendation) -> list[EvidenceReference]:
    refs = [
        EvidenceReference(
            reference_id=f"decision:{decision.decision_id}",
            object_type="decision",
            label=decision.title,
            field="recommended_action",
            value=decision.recommended_action or None,
            source_object_id=decision.decision_id,
        )
    ]
    if decision.source_insight_id:
        refs.append(
            EvidenceReference(
                reference_id=f"insight:{decision.source_insight_id}",
                object_type="insight",
                label="source_insight",
                field="source_insight_id",
                value=decision.source_insight_id,
                source_object_id=decision.source_insight_id,
            )
        )
    for kpi in decision.related_kpis:
        refs.append(
            EvidenceReference(
                reference_id=f"kpi:{decision.decision_id}:{kpi}",
                object_type="kpi_reference",
                label=kpi,
                field="related_kpis",
                value=kpi,
                source_object_id=decision.decision_id,
            )
        )
    return refs


def _evidence_from_root_cause(cause: RootCause) -> list[EvidenceReference]:
    refs = [
        EvidenceReference(
            reference_id=f"root_cause:{cause.root_cause_id}",
            object_type="root_cause",
            label=cause.title,
            field="summary",
            value=cause.summary or None,
            source_object_id=cause.root_cause_id,
        )
    ]
    if cause.source_decision_id:
        refs.append(
            EvidenceReference(
                reference_id=f"decision:{cause.source_decision_id}",
                object_type="decision",
                label="source_decision",
                field="source_decision_id",
                value=cause.source_decision_id,
                source_object_id=cause.source_decision_id,
            )
        )
    if cause.source_insight_id:
        refs.append(
            EvidenceReference(
                reference_id=f"insight:{cause.source_insight_id}",
                object_type="insight",
                label="source_insight",
                field="source_insight_id",
                value=cause.source_insight_id,
                source_object_id=cause.source_insight_id,
            )
        )
    return refs


def _mode_prefix(mode: AnalystResponseMode) -> str:
    return {
        AnalystResponseMode.executive: "Executive view",
        AnalystResponseMode.business: "Business view",
        AnalystResponseMode.analyst: "Analyst view",
        AnalystResponseMode.technical: "Technical view",
        AnalystResponseMode.audit: "Audit view",
    }.get(mode, "Analyst view")


def _format_answer_text(
    mode: AnalystResponseMode,
    *,
    headline: str,
    body_parts: list[str],
    unavailable: list[str],
) -> str:
    lines = [f"{_mode_prefix(mode)}: {_text_or_unavailable(headline)}"]
    for part in body_parts:
        if part and part != _UNAVAILABLE:
            lines.append(part)
    if unavailable:
        lines.append(f"Unavailable: {', '.join(unavailable)}.")
    return "\n".join(lines)


def _key_points_for_mode(
    mode: AnalystResponseMode,
    *,
    reasoning: ExecutiveReasoning | None,
    decisions: DecisionCollection | None,
    root_causes: RootCauseCollection | None,
    validations: list[ValidationReport],
    storyboard: ExecutiveStoryboard | None,
) -> list[str]:
    points: list[str] = []

    if mode == AnalystResponseMode.executive:
        if reasoning is not None:
            if reasoning.executive_summary:
                points.append(reasoning.executive_summary)
            if reasoning.narrative.recommended_priority:
                points.append(f"Priority: {reasoning.narrative.recommended_priority}")
        elif storyboard is not None and storyboard.summary.headline:
            points.append(storyboard.summary.headline)
    elif mode == AnalystResponseMode.business:
        if reasoning is not None:
            if reasoning.narrative.business_impact:
                points.append(reasoning.narrative.business_impact)
            if reasoning.narrative.what_happened:
                points.append(reasoning.narrative.what_happened)
        if decisions is not None and decisions.summary.overall_business_health:
            points.append(f"Business health: {decisions.summary.overall_business_health}")
    elif mode == AnalystResponseMode.analyst:
        if decisions is not None:
            for item in decisions.decisions[:3]:
                if item.recommended_action:
                    points.append(f"Decision {item.decision_id}: {item.recommended_action}")
        if root_causes is not None:
            for item in root_causes.root_causes[:3]:
                if item.summary:
                    points.append(f"Root cause {item.root_cause_id}: {item.summary}")
    elif mode == AnalystResponseMode.technical:
        if validations:
            for report in validations[:3]:
                points.append(
                    f"Validation {_validation_id(report)}: status={report.overall_status.value}, "
                    f"score={report.score}"
                )
        if decisions is not None:
            for item in decisions.decisions[:3]:
                points.append(
                    f"Decision {item.decision_id}: confidence={item.confidence}, "
                    f"score={item.decision_score}, status={item.status.value}"
                )
    elif mode == AnalystResponseMode.audit:
        if reasoning is not None:
            points.append(f"reasoning_id={reasoning.reasoning_id}")
            points.extend(f"linked_insight={iid}" for iid in reasoning.linked_insight_ids)
            points.extend(f"linked_decision={did}" for did in reasoning.linked_decision_ids)
            points.extend(f"linked_root_cause={rid}" for rid in reasoning.linked_root_cause_ids)
        for report in validations[:5]:
            points.append(f"validation_id={_validation_id(report)}")
            for warning in report.warnings[:3]:
                points.append(f"warning={warning}")
            for failed in report.failed_checks[:3]:
                points.append(f"failed_check={failed}")

    return [p for p in points if p]


def build_follow_up_context(
    *,
    response: AIAnalystResponse,
    dataset_id: str | None = None,
    domain: str | None = None,
) -> ConversationContext:
    """Build structured follow-up context from a response. No LLM memory."""
    return ConversationContext(
        context_id=f"ctx_{response.response_id}",
        dataset_id=dataset_id or response.dataset_id,
        domain=domain or response.domain,
        last_question=response.answer.question,
        last_mode=response.mode,
        focus_decision_ids=list(response.traceability.source_decisions),
        focus_root_cause_ids=list(response.traceability.source_root_causes),
        focus_insight_ids=list(response.traceability.source_insights),
        open_follow_ups=[item.question for item in response.follow_ups],
        unavailable_topics=list(response.explanation.unavailable_fields),
    )


def recommend_next_questions(
    *,
    decisions: DecisionCollection | None = None,
    root_causes: RootCauseCollection | None = None,
    validations: list[ValidationReport] | None = None,
    reasonings: ExecutiveReasoningCollection | None = None,
    insights: UniversalAIInsightCollection | None = None,
) -> list[FollowUpQuestion]:
    """Rule-based follow-ups from gaps, warnings, and missing evidence. No LLM."""
    follow_ups: list[FollowUpQuestion] = []
    idx = 0

    def add(question: str, rationale: str, source_gap: str, related: list[str], priority: str = "medium") -> None:
        nonlocal idx
        idx += 1
        follow_ups.append(
            FollowUpQuestion(
                question_id=f"followup_{idx}",
                question=question,
                rationale=rationale,
                source_gap=source_gap,
                related_object_ids=_unique(related),
                priority=priority,
            )
        )

    if decisions is not None:
        for item in decisions.decisions:
            if item.status.value in {"incomplete", "blocked"}:
                add(
                    f"What is blocking decision '{item.title}'?",
                    f"Decision status is {item.status.value}.",
                    "decision_gap",
                    [item.decision_id],
                    "high",
                )
            if not item.supporting_evidence:
                add(
                    f"What evidence supports decision '{item.title}'?",
                    "Decision has no supporting_evidence entries.",
                    "missing_evidence",
                    [item.decision_id],
                )
            if item.limitations:
                add(
                    f"How should we address limitations on decision '{item.title}'?",
                    "Decision lists limitations that remain open.",
                    "decision_gap",
                    [item.decision_id],
                )

    if validations:
        for report in validations:
            for warning in report.warnings:
                add(
                    f"How should we resolve validation warning: {warning}?",
                    "Validation report contains a warning.",
                    "validation_warning",
                    [_validation_id(report)],
                    "high",
                )
            for failed in report.failed_checks:
                add(
                    f"What caused validation failure: {failed}?",
                    "Validation report contains a failed check.",
                    "validation_warning",
                    [_validation_id(report)],
                    "high",
                )

    if root_causes is not None:
        for cause in root_causes.root_causes:
            add(
                f"What actions address root cause '{cause.title}'?",
                "Root cause is registered and may need remediation follow-up.",
                "root_cause",
                [cause.root_cause_id],
            )
            if cause.business_impact:
                add(
                    f"What is the quantified business impact of '{cause.title}'?",
                    "Business impact text exists; quantification may still be missing.",
                    "business_impact",
                    [cause.root_cause_id],
                )
            if not cause.supporting_evidence:
                add(
                    f"What additional evidence is needed for root cause '{cause.title}'?",
                    "Root cause has no supporting_evidence entries.",
                    "missing_evidence",
                    [cause.root_cause_id],
                    "high",
                )

    if reasonings is not None:
        for item in reasonings.reasonings:
            if not item.key_risks:
                add(
                    "Are there documented business risks for this dataset?",
                    "Executive reasoning has no key_risks.",
                    "decision_gap",
                    [item.reasoning_id],
                )
            if not item.prioritized_recommendations:
                add(
                    "Which existing decisions should be prioritized next?",
                    "Executive reasoning has no prioritized_recommendations.",
                    "decision_gap",
                    [item.reasoning_id],
                )

    if insights is not None and not insights.insights:
        add(
            "Why are there no insights available for this dataset?",
            "Insight collection is empty.",
            "missing_evidence",
            [],
            "high",
        )

    if not follow_ups:
        add(
            "Which existing decision should we review next?",
            "No specific gaps detected; default navigation question.",
            "decision_gap",
            [],
            "low",
        )

    return follow_ups


def _build_explanation(
    reasoning: ExecutiveReasoning | None,
    decisions: DecisionCollection | None,
    storyboard: ExecutiveStoryboard | None,
) -> BusinessExplanation:
    unavailable: list[str] = []
    headline = ""
    what = ""
    why = ""
    impact = ""
    priority = ""

    if reasoning is not None:
        headline = reasoning.headline or reasoning.executive_summary
        what = reasoning.narrative.what_happened
        why = reasoning.narrative.why_it_happened
        impact = reasoning.narrative.business_impact
        priority = reasoning.narrative.recommended_priority
    elif storyboard is not None:
        headline = storyboard.summary.headline or storyboard.title
        priority = storyboard.summary.top_priority_action
    elif decisions is not None:
        headline = decisions.summary.headline
        impact = decisions.summary.overall_business_health

    if not headline:
        unavailable.append("headline")
    if not what:
        unavailable.append("what_happened")
    if not why:
        unavailable.append("why_it_happened")
    if not impact:
        unavailable.append("business_impact")
    if not priority:
        unavailable.append("recommended_priority")

    return BusinessExplanation(
        explanation_id=f"expl_{(reasoning.reasoning_id if reasoning else 'none')}",
        headline=_text_or_unavailable(headline),
        what_happened=_text_or_unavailable(what),
        why_it_happened=_text_or_unavailable(why),
        business_impact=_text_or_unavailable(impact),
        recommended_priority=_text_or_unavailable(priority),
        unavailable_fields=unavailable,
    )


def _build_action_plan(
    reasoning: ExecutiveReasoning | None,
    decisions: DecisionCollection | None,
) -> ActionPlan:
    actions: list[str] = []
    decision_ids: list[str] = []
    priority_labels: list[str] = []
    unavailable_note = ""

    if reasoning is not None:
        for rec in reasoning.prioritized_recommendations:
            if rec.recommended_action:
                actions.append(rec.recommended_action)
            if rec.decision_id:
                decision_ids.append(rec.decision_id)
        for pri in reasoning.recommended_priorities:
            if pri.label:
                priority_labels.append(pri.label)

    if decisions is not None:
        for item in decisions.decisions:
            decision_ids.append(item.decision_id)
            if item.recommended_action and item.recommended_action not in actions:
                actions.append(item.recommended_action)
        for label in decisions.summary.quick_wins:
            if label and label not in actions:
                actions.append(label)
        for label in decisions.summary.strategic_actions:
            if label and label not in actions:
                actions.append(label)

    if not actions:
        unavailable_note = "No existing decision actions are available."

    plan_seed = reasoning.reasoning_id if reasoning is not None else "none"
    return ActionPlan(
        plan_id=f"plan_{plan_seed}",
        title="Action plan from existing decisions",
        actions=actions,
        decision_ids=_unique(decision_ids),
        priority_labels=_unique(priority_labels),
        unavailable_note=unavailable_note,
    )


def build_ai_response(
    *,
    mode: AnalystResponseMode = AnalystResponseMode.executive,
    question: str = "",
    bundle: IntelligenceBundle | None = None,
    registry: IntelligenceRegistry | None = None,
    storyboard: ExecutiveStoryboard | None = None,
    reasonings: ExecutiveReasoningCollection | None = None,
    decisions: DecisionCollection | None = None,
    root_causes: RootCauseCollection | None = None,
    validations: list[ValidationReport] | None = None,
    insights: UniversalAIInsightCollection | None = None,
    dataset_id: str | None = None,
    domain: str | None = None,
) -> AIAnalystResponse:
    """Assemble an analyst response from existing intelligence only."""
    (
        bundle_c,
        registry_c,
        storyboard_c,
        reasonings_c,
        decisions_c,
        root_causes_c,
        validations_c,
        insights_c,
    ) = _resolve_sources(
        bundle=bundle,
        registry=registry,
        storyboard=storyboard,
        reasonings=reasonings,
        decisions=decisions,
        root_causes=root_causes,
        validations=validations,
        insights=insights,
    )

    reasoning = _primary_reasoning(reasonings_c)
    explanation = _build_explanation(reasoning, decisions_c, storyboard_c)
    action_plan = _build_action_plan(reasoning, decisions_c)
    traceability = _build_traceability(
        bundle=bundle_c,
        registry=registry_c,
        storyboard=storyboard_c,
        reasonings=reasonings_c,
        decisions=decisions_c,
        root_causes=root_causes_c,
        validations=validations_c,
        insights=insights_c,
    )

    unavailable: list[str] = list(explanation.unavailable_fields)
    if bundle_c is None and reasonings_c is None and storyboard_c is None and decisions_c is None:
        unavailable.append("intelligence_sources")

    headline = explanation.headline if explanation.headline != _UNAVAILABLE else _UNAVAILABLE
    body_parts: list[str] = []
    if mode in {AnalystResponseMode.executive, AnalystResponseMode.business}:
        body_parts.extend(
            [
                f"What happened: {explanation.what_happened}",
                f"Why: {explanation.why_it_happened}",
                f"Impact: {explanation.business_impact}",
                f"Priority: {explanation.recommended_priority}",
            ]
        )
    elif mode == AnalystResponseMode.analyst:
        if decisions_c is not None and decisions_c.decisions:
            top = decisions_c.decisions[0]
            body_parts.append(f"Top decision: {top.title} — {top.recommended_action or _UNAVAILABLE}")
        else:
            body_parts.append("Top decision: unavailable")
        if root_causes_c is not None and root_causes_c.root_causes:
            top_rc = root_causes_c.root_causes[0]
            body_parts.append(f"Top root cause: {top_rc.title} — {top_rc.summary or _UNAVAILABLE}")
        else:
            body_parts.append("Top root cause: unavailable")
    elif mode == AnalystResponseMode.technical:
        if validations_c:
            report = validations_c[0]
            body_parts.append(
                f"Validation: {_validation_id(report)} status={report.overall_status.value} score={report.score}"
            )
        else:
            body_parts.append("Validation: unavailable")
            unavailable.append("validation")
        if decisions_c is not None and decisions_c.decisions:
            d0 = decisions_c.decisions[0]
            body_parts.append(
                f"Decision metrics: id={d0.decision_id} confidence={d0.confidence} score={d0.decision_score}"
            )
    elif mode == AnalystResponseMode.audit:
        body_parts.append(f"bundle={traceability.source_bundle or _UNAVAILABLE}")
        body_parts.append(f"storyboard={traceability.source_storyboard or _UNAVAILABLE}")
        body_parts.append(f"reasoning_ids={','.join(traceability.source_reasoning) or _UNAVAILABLE}")
        body_parts.append(f"decision_ids={','.join(traceability.source_decisions) or _UNAVAILABLE}")
        body_parts.append(f"registry_refs={len(traceability.registry_reference_ids)}")

    key_points = _key_points_for_mode(
        mode,
        reasoning=reasoning,
        decisions=decisions_c,
        root_causes=root_causes_c,
        validations=validations_c,
        storyboard=storyboard_c,
    )

    evidence: list[EvidenceReference] = []
    if decisions_c is not None:
        for item in decisions_c.decisions[:5]:
            evidence.extend(_evidence_from_decision(item))
    if root_causes_c is not None:
        for item in root_causes_c.root_causes[:5]:
            evidence.extend(_evidence_from_root_cause(item))
    if reasoning is not None:
        evidence.append(
            EvidenceReference(
                reference_id=f"reasoning:{reasoning.reasoning_id}",
                object_type="executive_reasoning",
                label=reasoning.headline or reasoning.reasoning_id,
                field="executive_summary",
                value=reasoning.executive_summary or None,
                source_object_id=reasoning.reasoning_id,
            )
        )

    confidence = None
    validation_status = ""
    if reasoning is not None:
        confidence = reasoning.executive_confidence
        validation_status = reasoning.overall_validation_status.value
    elif storyboard_c is not None:
        confidence = storyboard_c.summary.executive_confidence
        validation_status = storyboard_c.summary.validation_status.value
    elif validations_c:
        validation_status = validations_c[0].overall_status.value

    answer_text = _format_answer_text(
        mode,
        headline=headline,
        body_parts=body_parts,
        unavailable=_unique(unavailable),
    )
    unavailable_note = ""
    if "intelligence_sources" in unavailable:
        unavailable_note = "Required intelligence sources are unavailable."

    now = utc_now_iso()
    resolved_dataset = dataset_id
    resolved_domain = domain
    for source in (bundle_c, storyboard_c, reasonings_c, decisions_c, root_causes_c, insights_c):
        if source is None:
            continue
        if resolved_dataset is None and getattr(source, "dataset_id", None):
            resolved_dataset = source.dataset_id
        if resolved_domain is None and getattr(source, "domain", None):
            resolved_domain = source.domain

    follow_ups = recommend_next_questions(
        decisions=decisions_c,
        root_causes=root_causes_c,
        validations=validations_c,
        reasonings=reasonings_c,
        insights=insights_c,
    )

    response_id = f"analyst_{resolved_dataset or 'empty'}_{now.replace(':', '').replace('-', '')}"
    answer = ExecutiveAnswer(
        answer_id=f"answer_{response_id}",
        mode=mode,
        question=question,
        headline=_text_or_unavailable(headline if headline != _UNAVAILABLE else ""),
        answer_text=answer_text,
        key_points=key_points,
        confidence=confidence,
        validation_status=validation_status,
        unavailable_note=unavailable_note,
        evidence=evidence,
    )

    response = AIAnalystResponse(
        response_id=response_id,
        schema_version=AI_ANALYST_SCHEMA_VERSION,
        dataset_id=resolved_dataset,
        domain=resolved_domain,
        mode=mode,
        answer=answer,
        explanation=explanation,
        action_plan=action_plan,
        follow_ups=follow_ups,
        traceability=traceability,
        conversation_context=None,
        generated_at=now,
        metadata=AnalystMetadata(
            legacy={"schema": AI_ANALYST_SCHEMA_VERSION},
            debug={
                "mode": mode.value,
                "has_bundle": bundle_c is not None,
                "has_registry": registry_c is not None,
                "has_storyboard": storyboard_c is not None,
                "has_reasonings": reasonings_c is not None,
                "decision_count": len(decisions_c.decisions) if decisions_c else 0,
                "root_cause_count": len(root_causes_c.root_causes) if root_causes_c else 0,
            },
            custom={},
            future_extensions=empty_ai_analyst_future_extensions(),
        ),
    )
    response.conversation_context = build_follow_up_context(
        response=response,
        dataset_id=resolved_dataset,
        domain=resolved_domain,
    )
    return response


def answer_question(
    question: str,
    *,
    mode: AnalystResponseMode = AnalystResponseMode.executive,
    bundle: IntelligenceBundle | None = None,
    registry: IntelligenceRegistry | None = None,
    storyboard: ExecutiveStoryboard | None = None,
    reasonings: ExecutiveReasoningCollection | None = None,
    decisions: DecisionCollection | None = None,
    root_causes: RootCauseCollection | None = None,
    validations: list[ValidationReport] | None = None,
    insights: UniversalAIInsightCollection | None = None,
    dataset_id: str | None = None,
    domain: str | None = None,
) -> AIAnalystResponse:
    """Route a natural-language question to the appropriate existing intelligence view."""
    q = (question or "").strip().lower()
    if any(token in q for token in ("root cause", "why did", "why is", "cause")):
        return explain_root_cause(
            mode=mode,
            question=question,
            bundle=bundle,
            registry=registry,
            storyboard=storyboard,
            reasonings=reasonings,
            decisions=decisions,
            root_causes=root_causes,
            validations=validations,
            insights=insights,
            dataset_id=dataset_id,
            domain=domain,
        )
    if any(token in q for token in ("decision", "recommend", "action", "what should")):
        return explain_decision(
            mode=mode,
            question=question,
            bundle=bundle,
            registry=registry,
            storyboard=storyboard,
            reasonings=reasonings,
            decisions=decisions,
            root_causes=root_causes,
            validations=validations,
            insights=insights,
            dataset_id=dataset_id,
            domain=domain,
        )
    if any(token in q for token in ("technical", "validation", "schema", "score")):
        return technical_summary(
            question=question,
            bundle=bundle,
            registry=registry,
            storyboard=storyboard,
            reasonings=reasonings,
            decisions=decisions,
            root_causes=root_causes,
            validations=validations,
            insights=insights,
            dataset_id=dataset_id,
            domain=domain,
        )
    if any(token in q for token in ("business", "impact", "health")):
        return business_summary(
            question=question,
            bundle=bundle,
            registry=registry,
            storyboard=storyboard,
            reasonings=reasonings,
            decisions=decisions,
            root_causes=root_causes,
            validations=validations,
            insights=insights,
            dataset_id=dataset_id,
            domain=domain,
        )
    return executive_summary(
        question=question,
        mode=mode,
        bundle=bundle,
        registry=registry,
        storyboard=storyboard,
        reasonings=reasonings,
        decisions=decisions,
        root_causes=root_causes,
        validations=validations,
        insights=insights,
        dataset_id=dataset_id,
        domain=domain,
    )


def explain_decision(
    *,
    decision_id: str | None = None,
    mode: AnalystResponseMode = AnalystResponseMode.analyst,
    question: str = "",
    bundle: IntelligenceBundle | None = None,
    registry: IntelligenceRegistry | None = None,
    storyboard: ExecutiveStoryboard | None = None,
    reasonings: ExecutiveReasoningCollection | None = None,
    decisions: DecisionCollection | None = None,
    root_causes: RootCauseCollection | None = None,
    validations: list[ValidationReport] | None = None,
    insights: UniversalAIInsightCollection | None = None,
    dataset_id: str | None = None,
    domain: str | None = None,
) -> AIAnalystResponse:
    """Explain an existing decision by reference. Never invents recommendations."""
    response = build_ai_response(
        mode=mode,
        question=question or "Explain the decision",
        bundle=bundle,
        registry=registry,
        storyboard=storyboard,
        reasonings=reasonings,
        decisions=decisions,
        root_causes=root_causes,
        validations=validations,
        insights=insights,
        dataset_id=dataset_id,
        domain=domain,
    )

    (
        _,
        _,
        _,
        _,
        decisions_c,
        _,
        _,
        _,
    ) = _resolve_sources(
        bundle=bundle,
        registry=registry,
        storyboard=storyboard,
        reasonings=reasonings,
        decisions=decisions,
        root_causes=root_causes,
        validations=validations,
        insights=insights,
    )

    target: DecisionRecommendation | None = None
    if decisions_c is not None and decisions_c.decisions:
        if decision_id:
            target = next((d for d in decisions_c.decisions if d.decision_id == decision_id), None)
        if target is None:
            target = decisions_c.decisions[0]

    if target is None:
        response.answer.answer_text = (
            f"{_mode_prefix(mode)}: Decision explanation is unavailable.\n"
            "Unavailable: decision."
        )
        response.answer.unavailable_note = "No decision is available to explain."
        response.answer.key_points = []
        response.answer.evidence = []
        return response

    points = [
        f"Title: {target.title}",
        f"Action: {_text_or_unavailable(target.recommended_action)}",
        f"Reason: {_text_or_unavailable(target.business_reason)}",
        f"Impact: {_text_or_unavailable(target.business_impact)}",
        f"Expected outcome: {_text_or_unavailable(target.expected_outcome)}",
        f"Priority: {target.priority.value}",
        f"Status: {target.status.value}",
        f"Confidence: {target.confidence}",
    ]
    if target.related_kpis:
        points.append(f"Related KPIs (existing): {', '.join(target.related_kpis)}")
    else:
        points.append("Related KPIs: unavailable")

    response.answer.headline = target.title
    response.answer.answer_text = _format_answer_text(
        mode,
        headline=target.title,
        body_parts=points,
        unavailable=[],
    )
    response.answer.key_points = points
    response.answer.evidence = _evidence_from_decision(target)
    response.answer.confidence = target.confidence
    response.answer.validation_status = target.validation_status.value
    response.traceability.source_decisions = _unique(
        [target.decision_id] + list(response.traceability.source_decisions)
    )
    if target.source_insight_id:
        response.traceability.source_insights = _unique(
            [target.source_insight_id] + list(response.traceability.source_insights)
        )
    return response


def explain_root_cause(
    *,
    root_cause_id: str | None = None,
    mode: AnalystResponseMode = AnalystResponseMode.analyst,
    question: str = "",
    bundle: IntelligenceBundle | None = None,
    registry: IntelligenceRegistry | None = None,
    storyboard: ExecutiveStoryboard | None = None,
    reasonings: ExecutiveReasoningCollection | None = None,
    decisions: DecisionCollection | None = None,
    root_causes: RootCauseCollection | None = None,
    validations: list[ValidationReport] | None = None,
    insights: UniversalAIInsightCollection | None = None,
    dataset_id: str | None = None,
    domain: str | None = None,
) -> AIAnalystResponse:
    """Explain an existing root cause by reference. Never invents causes."""
    response = build_ai_response(
        mode=mode,
        question=question or "Explain the root cause",
        bundle=bundle,
        registry=registry,
        storyboard=storyboard,
        reasonings=reasonings,
        decisions=decisions,
        root_causes=root_causes,
        validations=validations,
        insights=insights,
        dataset_id=dataset_id,
        domain=domain,
    )

    (
        _,
        _,
        _,
        _,
        _,
        root_causes_c,
        _,
        _,
    ) = _resolve_sources(
        bundle=bundle,
        registry=registry,
        storyboard=storyboard,
        reasonings=reasonings,
        decisions=decisions,
        root_causes=root_causes,
        validations=validations,
        insights=insights,
    )

    target: RootCause | None = None
    if root_causes_c is not None and root_causes_c.root_causes:
        if root_cause_id:
            target = next(
                (c for c in root_causes_c.root_causes if c.root_cause_id == root_cause_id),
                None,
            )
        if target is None:
            target = root_causes_c.root_causes[0]

    if target is None:
        response.answer.answer_text = (
            f"{_mode_prefix(mode)}: Root cause explanation is unavailable.\n"
            "Unavailable: root_cause."
        )
        response.answer.unavailable_note = "No root cause is available to explain."
        response.answer.key_points = []
        response.answer.evidence = []
        return response

    points = [
        f"Title: {target.title}",
        f"Summary: {_text_or_unavailable(target.summary)}",
        f"Description: {_text_or_unavailable(target.description)}",
        f"Category: {target.cause_category.value}",
        f"Severity: {target.severity.value}",
        f"Business impact: {_text_or_unavailable(target.business_impact)}",
        f"Confidence: {target.confidence}",
        f"Traceability score: {target.traceability_score}",
    ]
    if target.probability is None:
        points.append("Probability: unavailable")
    else:
        points.append(f"Probability: {target.probability}")

    response.answer.headline = target.title
    response.answer.answer_text = _format_answer_text(
        mode,
        headline=target.title,
        body_parts=points,
        unavailable=[],
    )
    response.answer.key_points = points
    response.answer.evidence = _evidence_from_root_cause(target)
    response.answer.confidence = target.confidence
    response.answer.validation_status = target.validation_status.value
    response.traceability.source_root_causes = _unique(
        [target.root_cause_id] + list(response.traceability.source_root_causes)
    )
    if target.source_decision_id:
        response.traceability.source_decisions = _unique(
            [target.source_decision_id] + list(response.traceability.source_decisions)
        )
    if target.source_insight_id:
        response.traceability.source_insights = _unique(
            [target.source_insight_id] + list(response.traceability.source_insights)
        )
    return response


def executive_summary(
    *,
    question: str = "",
    mode: AnalystResponseMode = AnalystResponseMode.executive,
    bundle: IntelligenceBundle | None = None,
    registry: IntelligenceRegistry | None = None,
    storyboard: ExecutiveStoryboard | None = None,
    reasonings: ExecutiveReasoningCollection | None = None,
    decisions: DecisionCollection | None = None,
    root_causes: RootCauseCollection | None = None,
    validations: list[ValidationReport] | None = None,
    insights: UniversalAIInsightCollection | None = None,
    dataset_id: str | None = None,
    domain: str | None = None,
) -> AIAnalystResponse:
    return build_ai_response(
        mode=mode if mode == AnalystResponseMode.executive else AnalystResponseMode.executive,
        question=question or "Provide an executive summary",
        bundle=bundle,
        registry=registry,
        storyboard=storyboard,
        reasonings=reasonings,
        decisions=decisions,
        root_causes=root_causes,
        validations=validations,
        insights=insights,
        dataset_id=dataset_id,
        domain=domain,
    )


def business_summary(
    *,
    question: str = "",
    bundle: IntelligenceBundle | None = None,
    registry: IntelligenceRegistry | None = None,
    storyboard: ExecutiveStoryboard | None = None,
    reasonings: ExecutiveReasoningCollection | None = None,
    decisions: DecisionCollection | None = None,
    root_causes: RootCauseCollection | None = None,
    validations: list[ValidationReport] | None = None,
    insights: UniversalAIInsightCollection | None = None,
    dataset_id: str | None = None,
    domain: str | None = None,
) -> AIAnalystResponse:
    return build_ai_response(
        mode=AnalystResponseMode.business,
        question=question or "Provide a business summary",
        bundle=bundle,
        registry=registry,
        storyboard=storyboard,
        reasonings=reasonings,
        decisions=decisions,
        root_causes=root_causes,
        validations=validations,
        insights=insights,
        dataset_id=dataset_id,
        domain=domain,
    )


def technical_summary(
    *,
    question: str = "",
    bundle: IntelligenceBundle | None = None,
    registry: IntelligenceRegistry | None = None,
    storyboard: ExecutiveStoryboard | None = None,
    reasonings: ExecutiveReasoningCollection | None = None,
    decisions: DecisionCollection | None = None,
    root_causes: RootCauseCollection | None = None,
    validations: list[ValidationReport] | None = None,
    insights: UniversalAIInsightCollection | None = None,
    dataset_id: str | None = None,
    domain: str | None = None,
) -> AIAnalystResponse:
    return build_ai_response(
        mode=AnalystResponseMode.technical,
        question=question or "Provide a technical summary",
        bundle=bundle,
        registry=registry,
        storyboard=storyboard,
        reasonings=reasonings,
        decisions=decisions,
        root_causes=root_causes,
        validations=validations,
        insights=insights,
        dataset_id=dataset_id,
        domain=domain,
    )


def validate_response(response: AIAnalystResponse) -> dict[str, object]:
    """Structural integrity checks only — never modifies the response."""
    issues: list[str] = []

    if not response.response_id:
        issues.append("Missing response_id")
    if not response.answer.answer_id:
        issues.append("Missing answer_id")
    if not response.answer.answer_text:
        issues.append("Missing answer_text")

    trace = response.traceability
    if (
        not trace.source_bundle
        and not trace.source_storyboard
        and not trace.source_reasoning
        and not trace.source_decisions
        and not trace.source_root_causes
        and not trace.source_validation
        and not trace.source_insights
        and "unavailable" not in response.answer.answer_text.lower()
    ):
        issues.append("Missing traceability sources without unavailable note")

    required_extensions = set(empty_ai_analyst_future_extensions().keys())
    missing_extensions = sorted(required_extensions - set(response.metadata.future_extensions.keys()))
    if missing_extensions:
        issues.append(f"Missing future_extensions: {', '.join(missing_extensions)}")

    if response.conversation_context is None:
        issues.append("Missing conversation_context")

    for evidence in response.answer.evidence:
        if not evidence.reference_id or not evidence.source_object_id:
            issues.append(f"Evidence missing reference: {evidence.reference_id or '?'}")

    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "response_id": response.response_id,
        "mode": response.mode.value,
    }


# ---------------------------------------------------------------------------
# Sprint 7.6 — AI Analyst runtime orchestration (delegates to runtime service)
# Existing Sprint 5.9 build_ai_response / answer_question APIs remain unchanged.
# ---------------------------------------------------------------------------


def create_session(*args: Any, **kwargs: Any):
    from backend.services.ai_analyst_runtime_service import create_session as _create

    return _create(*args, **kwargs)


def analyze_query(*args: Any, **kwargs: Any):
    from backend.services.ai_analyst_runtime_service import analyze_query as _analyze

    return _analyze(*args, **kwargs)


def execute_analysis(*args: Any, **kwargs: Any):
    from backend.services.ai_analyst_runtime_service import execute_analysis as _execute

    return _execute(*args, **kwargs)


def get_session(*args: Any, **kwargs: Any):
    from backend.services.ai_analyst_runtime_service import get_session as _get

    return _get(*args, **kwargs)


def session_summary(*args: Any, **kwargs: Any):
    from backend.services.ai_analyst_runtime_service import session_summary as _summary

    return _summary(*args, **kwargs)


def evaluate_completed_session(*args: Any, **kwargs: Any):
    """Read-only evaluation of a completed analyst session (Sprint 7.7)."""
    from backend.services.evaluation_service import evaluate_session

    return evaluate_session(*args, **kwargs)
