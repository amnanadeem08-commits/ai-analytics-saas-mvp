from __future__ import annotations

from backend.models.ai_insight_models import ValidationStatus, utc_now_iso
from backend.models.decision_models import DecisionCollection
from backend.models.executive_reasoning_models import (
    ExecutiveReasoning,
    ExecutiveReasoningCollection,
)
from backend.models.root_cause_models import RootCauseCollection
from backend.models.storyboard_models import (
    STORYBOARD_SCHEMA_VERSION,
    STORYBOARD_SLIDE_ORDER,
    ExecutiveStoryboard,
    StoryboardCollection,
    StoryboardMetadata,
    StoryboardSection,
    StoryboardSectionId,
    StoryboardSlide,
    StoryboardSlideType,
    StoryboardSummary,
    empty_storyboard_future_extensions,
)
from backend.models.validation_models import ValidationReport

_SECTION_PLAN: tuple[tuple[StoryboardSectionId, str, tuple[StoryboardSlideType, ...]], ...] = (
    (
        StoryboardSectionId.overview,
        "Overview",
        (StoryboardSlideType.executive_summary, StoryboardSlideType.business_health),
    ),
    (
        StoryboardSectionId.analysis,
        "Analysis",
        (
            StoryboardSlideType.key_findings,
            StoryboardSlideType.root_causes,
            StoryboardSlideType.business_risks,
            StoryboardSlideType.business_opportunities,
        ),
    ),
    (
        StoryboardSectionId.actions,
        "Actions",
        (StoryboardSlideType.recommended_decisions, StoryboardSlideType.priority_roadmap),
    ),
    (
        StoryboardSectionId.evidence,
        "Evidence",
        (StoryboardSlideType.kpi_highlights, StoryboardSlideType.supporting_evidence),
    ),
    (
        StoryboardSectionId.appendix,
        "Appendix",
        (StoryboardSlideType.appendix,),
    ),
)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _copy_reasoning_collection(
    collection: ExecutiveReasoningCollection | None,
) -> ExecutiveReasoningCollection | None:
    return collection.model_copy(deep=True) if collection is not None else None


def _copy_decision_collection(collection: DecisionCollection | None) -> DecisionCollection | None:
    return collection.model_copy(deep=True) if collection is not None else None


def _copy_root_cause_collection(collection: RootCauseCollection | None) -> RootCauseCollection | None:
    return collection.model_copy(deep=True) if collection is not None else None


def _copy_validations(reports: list[ValidationReport] | None) -> list[ValidationReport]:
    return [item.model_copy(deep=True) for item in (reports or [])]


def _primary_reasoning(
    reasonings: ExecutiveReasoningCollection | None,
) -> ExecutiveReasoning | None:
    if reasonings is None or not reasonings.reasonings:
        return None
    return reasonings.reasonings[0]


def _aggregate_traceability(
    reasonings: ExecutiveReasoningCollection | None,
    decisions: DecisionCollection | None,
    root_causes: RootCauseCollection | None,
    validations: list[ValidationReport],
) -> StoryboardMetadata:
    insight_ids: list[str] = []
    decision_ids: list[str] = []
    root_ids: list[str] = []
    validation_ids: list[str] = []
    reasoning_ids: list[str] = []

    if reasonings is not None:
        insight_ids.extend(reasonings.metadata.linked_insight_ids)
        decision_ids.extend(reasonings.metadata.linked_decision_ids)
        root_ids.extend(reasonings.metadata.linked_root_cause_ids)
        validation_ids.extend(reasonings.metadata.linked_validation_report_ids)
        for item in reasonings.reasonings:
            reasoning_ids.append(item.reasoning_id)
            insight_ids.extend(item.linked_insight_ids)
            decision_ids.extend(item.linked_decision_ids)
            root_ids.extend(item.linked_root_cause_ids)
            validation_ids.extend(item.metadata.linked_validation_report_ids)

    if decisions is not None:
        for decision in decisions.decisions:
            decision_ids.append(decision.decision_id)
            if decision.source_insight_id:
                insight_ids.append(decision.source_insight_id)

    if root_causes is not None:
        for cause in root_causes.root_causes:
            root_ids.append(cause.root_cause_id)
            if cause.source_insight_id:
                insight_ids.append(cause.source_insight_id)
            if cause.source_decision_id:
                decision_ids.append(cause.source_decision_id)

    for report in validations:
        validation_ids.append(f"validation_{report.validator_version}_{report.validated_at}")

    return StoryboardMetadata(
        future_extensions=empty_storyboard_future_extensions(),
        linked_insight_ids=_unique(insight_ids),
        linked_decision_ids=_unique(decision_ids),
        linked_root_cause_ids=_unique(root_ids),
        linked_validation_report_ids=_unique(validation_ids),
        linked_reasoning_ids=_unique(reasoning_ids),
    )


def _slide_trace(
    base: StoryboardMetadata,
    *,
    insight_ids: list[str] | None = None,
    decision_ids: list[str] | None = None,
    root_ids: list[str] | None = None,
    validation_ids: list[str] | None = None,
    reasoning_ids: list[str] | None = None,
) -> StoryboardMetadata:
    return StoryboardMetadata(
        future_extensions=empty_storyboard_future_extensions(),
        linked_insight_ids=_unique((insight_ids or []) or base.linked_insight_ids),
        linked_decision_ids=_unique((decision_ids or []) or base.linked_decision_ids),
        linked_root_cause_ids=_unique((root_ids or []) or base.linked_root_cause_ids),
        linked_validation_report_ids=_unique((validation_ids or []) or base.linked_validation_report_ids),
        linked_reasoning_ids=_unique((reasoning_ids or []) or base.linked_reasoning_ids),
    )


def _non_empty_bullets(values: list[str]) -> list[str]:
    return [item.strip() for item in values if str(item).strip()]


def _build_slide(
    slide_type: StoryboardSlideType,
    order: int,
    *,
    primary: ExecutiveReasoning | None,
    reasonings: ExecutiveReasoningCollection | None,
    decisions: DecisionCollection | None,
    root_causes: RootCauseCollection | None,
    validations: list[ValidationReport],
    trace: StoryboardMetadata,
) -> StoryboardSlide:
    slide_id = f"slide_{order:02d}_{slide_type.name}"
    reasoning_ids = [primary.reasoning_id] if primary is not None else []
    bullets: list[str] = []
    body = ""
    insight_ids = list(trace.linked_insight_ids)
    decision_ids = list(trace.linked_decision_ids)
    root_ids = list(trace.linked_root_cause_ids)
    validation_ids = list(trace.linked_validation_report_ids)

    if slide_type == StoryboardSlideType.executive_summary:
        if primary is not None:
            body = primary.executive_summary
            bullets = _non_empty_bullets(
                [
                    primary.narrative.what_happened,
                    primary.narrative.why_it_happened,
                    primary.narrative.business_impact,
                    primary.narrative.recommended_priority,
                    primary.narrative.confidence_statement,
                ]
            )
            insight_ids = primary.linked_insight_ids
            decision_ids = primary.linked_decision_ids
            root_ids = primary.linked_root_cause_ids
            validation_ids = primary.metadata.linked_validation_report_ids
        elif reasonings is not None and reasonings.summary.headline:
            body = reasonings.summary.headline
            bullets = _non_empty_bullets(
                [
                    reasonings.summary.top_priority_action,
                    reasonings.summary.top_risk,
                    reasonings.summary.top_opportunity,
                ]
            )

    elif slide_type == StoryboardSlideType.business_health:
        if decisions is not None and decisions.summary.overall_business_health:
            bullets.append(f"Business health: {decisions.summary.overall_business_health}")
        if primary is not None:
            bullets.append(f"Validation status: {primary.overall_validation_status.value}")
            bullets.append(f"Executive confidence: {primary.executive_confidence:.2f}")
            if primary.business_context:
                bullets.append(primary.business_context)
        if reasonings is not None:
            for key, count in reasonings.summary.validation_status_breakdown.items():
                bullets.append(f"Validation {key}: {count}")
        if validations:
            for report in validations[:3]:
                bullets.append(f"Validation score: {report.score:.1f}")
                validation_ids.append(f"validation_{report.validator_version}_{report.validated_at}")
                bullets.extend(report.warnings[:2])
        bullets = _non_empty_bullets(bullets)

    elif slide_type == StoryboardSlideType.key_findings:
        if primary is not None:
            for finding in primary.key_findings:
                bullets.append(finding.statement)
                insight_ids.extend(finding.source_insight_ids)
                decision_ids.extend(finding.source_decision_ids)
                root_ids.extend(finding.source_root_cause_ids)
                validation_ids.extend(finding.source_validation_report_ids)
        bullets = _non_empty_bullets(bullets)

    elif slide_type == StoryboardSlideType.root_causes:
        if root_causes is not None:
            if root_causes.summary.top_cause:
                bullets.append(root_causes.summary.top_cause)
            bullets.extend(root_causes.summary.contributing_factors[:5])
            bullets.extend(root_causes.summary.top_risks[:3])
            for cause in root_causes.root_causes[:5]:
                if cause.description:
                    bullets.append(cause.description)
                root_ids.append(cause.root_cause_id)
        elif primary is not None and primary.narrative.why_it_happened:
            bullets.append(primary.narrative.why_it_happened)
        bullets = _non_empty_bullets(bullets)

    elif slide_type == StoryboardSlideType.business_risks:
        if primary is not None:
            for risk in primary.key_risks:
                bullets.append(f"{risk.title}: {risk.description}" if risk.description else risk.title)
                decision_ids.extend(risk.source_decision_ids)
                root_ids.extend(risk.source_root_cause_ids)
        if decisions is not None:
            bullets.extend(decisions.summary.top_risks[:5])
        if root_causes is not None:
            bullets.extend(root_causes.summary.top_risks[:5])
        bullets = _non_empty_bullets(bullets)

    elif slide_type == StoryboardSlideType.business_opportunities:
        if primary is not None:
            for opportunity in primary.key_opportunities:
                text = opportunity.title
                if opportunity.expected_outcome:
                    text = f"{opportunity.title}: {opportunity.expected_outcome}"
                bullets.append(text)
                decision_ids.extend(opportunity.source_decision_ids)
                insight_ids.extend(opportunity.source_insight_ids)
        if decisions is not None:
            bullets.extend(decisions.summary.top_opportunities[:5])
            bullets.extend(decisions.summary.quick_wins[:3])
            bullets.extend(decisions.summary.strategic_actions[:3])
        bullets = _non_empty_bullets(bullets)

    elif slide_type == StoryboardSlideType.recommended_decisions:
        if primary is not None:
            for recommendation in primary.prioritized_recommendations:
                bullets.append(recommendation.recommended_action or recommendation.title)
                decision_ids.append(recommendation.decision_id)
        if decisions is not None:
            for decision in decisions.decisions[:8]:
                if decision.recommended_action:
                    bullets.append(decision.recommended_action)
                    decision_ids.append(decision.decision_id)
        bullets = _non_empty_bullets(bullets)

    elif slide_type == StoryboardSlideType.priority_roadmap:
        if primary is not None:
            for priority in primary.recommended_priorities:
                bullets.append(priority.label)
                decision_ids.extend(priority.linked_decision_ids)
        if decisions is not None:
            bullets.extend(decisions.summary.quick_wins[:5])
            bullets.extend(decisions.summary.strategic_actions[:5])
        bullets = _non_empty_bullets(bullets)

    elif slide_type == StoryboardSlideType.kpi_highlights:
        if primary is not None:
            for finding in primary.key_findings:
                if finding.finding_type.value == "business_impact" and finding.statement:
                    bullets.append(finding.statement)
            if primary.narrative.business_impact:
                bullets.append(primary.narrative.business_impact)
        if decisions is not None and decisions.summary.executive_note:
            bullets.append(decisions.summary.executive_note)
        if root_causes is not None:
            for cause in root_causes.root_causes[:5]:
                bullets.extend(cause.affected_metrics[:3])
                bullets.extend(cause.related_kpis[:3])
        bullets = _non_empty_bullets(bullets)

    elif slide_type == StoryboardSlideType.supporting_evidence:
        if primary is not None:
            for finding in primary.key_findings:
                bullets.append(finding.statement)
            for risk in primary.key_risks[:3]:
                bullets.extend(risk.source_validation_warnings[:2])
        if root_causes is not None:
            for cause in root_causes.root_causes[:3]:
                for evidence in cause.supporting_evidence[:3]:
                    bullets.append(f"{evidence.label}: {evidence.value}")
                    root_ids.append(cause.root_cause_id)
        if validations:
            for report in validations[:2]:
                bullets.extend(report.passed_checks[:3])
                bullets.extend(report.warnings[:3])
                validation_ids.append(f"validation_{report.validator_version}_{report.validated_at}")
        bullets = _non_empty_bullets(bullets)

    elif slide_type == StoryboardSlideType.appendix:
        if primary is not None:
            bullets.append(f"Reasoning ID: {primary.reasoning_id}")
            bullets.append(f"Validation status: {primary.overall_validation_status.value}")
            bullets.extend(f"Insight: {item}" for item in primary.linked_insight_ids)
            bullets.extend(f"Decision: {item}" for item in primary.linked_decision_ids)
            bullets.extend(f"Root cause: {item}" for item in primary.linked_root_cause_ids)
        if decisions is not None:
            bullets.append(f"Decision count: {len(decisions.decisions)}")
        if root_causes is not None:
            bullets.append(f"Root cause count: {len(root_causes.root_causes)}")
            bullets.append(f"Identified causes: {root_causes.summary.identified_count}")
        bullets = _non_empty_bullets(bullets)

    metadata = _slide_trace(
        trace,
        insight_ids=insight_ids,
        decision_ids=decision_ids,
        root_ids=root_ids,
        validation_ids=validation_ids,
        reasoning_ids=reasoning_ids,
    )
    return StoryboardSlide(
        slide_id=slide_id,
        slide_type=slide_type,
        title=slide_type.value,
        order=order,
        bullets=bullets,
        body=body,
        linked_insight_ids=metadata.linked_insight_ids,
        linked_decision_ids=metadata.linked_decision_ids,
        linked_root_cause_ids=metadata.linked_root_cause_ids,
        linked_validation_report_ids=metadata.linked_validation_report_ids,
        linked_reasoning_ids=metadata.linked_reasoning_ids,
        metadata=metadata,
    )


def _build_summary(
    *,
    primary: ExecutiveReasoning | None,
    reasonings: ExecutiveReasoningCollection | None,
    decisions: DecisionCollection | None,
    root_causes: RootCauseCollection | None,
    slides: list[StoryboardSlide],
    sections: list[StoryboardSection],
    domain: str | None,
) -> StoryboardSummary:
    headline = ""
    top_priority = ""
    top_risk = ""
    top_opportunity = ""
    top_root_cause = ""
    confidence = 0.0
    validation_status = ValidationStatus.pending

    if primary is not None:
        headline = primary.headline
        confidence = primary.executive_confidence
        validation_status = primary.overall_validation_status
        if primary.prioritized_recommendations:
            top_priority = primary.prioritized_recommendations[0].recommended_action
        if primary.key_risks:
            top_risk = primary.key_risks[0].title
        if primary.key_opportunities:
            top_opportunity = primary.key_opportunities[0].title
    elif reasonings is not None:
        headline = reasonings.summary.headline
        top_priority = reasonings.summary.top_priority_action
        top_risk = reasonings.summary.top_risk
        top_opportunity = reasonings.summary.top_opportunity
        confidence = reasonings.summary.average_executive_confidence

    if decisions is not None and not top_priority:
        top_priority = decisions.summary.quick_wins[0] if decisions.summary.quick_wins else ""
        if not top_risk:
            top_risk = decisions.summary.top_risks[0] if decisions.summary.top_risks else ""
        if not top_opportunity:
            top_opportunity = (
                decisions.summary.top_opportunities[0] if decisions.summary.top_opportunities else ""
            )

    if root_causes is not None:
        top_root_cause = root_causes.summary.top_cause

    return StoryboardSummary(
        headline=headline,
        slide_count=len(slides),
        section_count=len(sections),
        domain=domain,
        validation_status=validation_status,
        top_priority_action=top_priority,
        top_risk=top_risk,
        top_opportunity=top_opportunity,
        top_root_cause=top_root_cause,
        executive_confidence=confidence,
    )


def build_executive_storyboard_from_reasoning(
    reasonings: ExecutiveReasoningCollection | None = None,
    decisions: DecisionCollection | None = None,
    root_causes: RootCauseCollection | None = None,
    validations: list[ValidationReport] | None = None,
    *,
    dataset_id: str | None = None,
    domain: str | None = None,
) -> ExecutiveStoryboard:
    """Organize validated executive intelligence into ordered storyboard slides.

    Presentation orchestration only. Never fabricates or regenerates upstream outputs.
    """
    reasonings_c = _copy_reasoning_collection(reasonings)
    decisions_c = _copy_decision_collection(decisions)
    root_causes_c = _copy_root_cause_collection(root_causes)
    validations_c = _copy_validations(validations)
    primary = _primary_reasoning(reasonings_c)
    trace = _aggregate_traceability(reasonings_c, decisions_c, root_causes_c, validations_c)

    slides: list[StoryboardSlide] = []
    for order, slide_type in enumerate(STORYBOARD_SLIDE_ORDER, start=1):
        slides.append(
            _build_slide(
                slide_type,
                order,
                primary=primary,
                reasonings=reasonings_c,
                decisions=decisions_c,
                root_causes=root_causes_c,
                validations=validations_c,
                trace=trace,
            )
        )

    slides_by_type = {slide.slide_type: slide for slide in slides}
    sections: list[StoryboardSection] = []
    for section_order, (section_id, section_title, slide_types) in enumerate(_SECTION_PLAN, start=1):
        section_slides = [slides_by_type[slide_type] for slide_type in slide_types if slide_type in slides_by_type]
        section_trace = StoryboardMetadata(
            future_extensions=empty_storyboard_future_extensions(),
            linked_insight_ids=_unique([item_id for slide in section_slides for item_id in slide.linked_insight_ids]),
            linked_decision_ids=_unique([item_id for slide in section_slides for item_id in slide.linked_decision_ids]),
            linked_root_cause_ids=_unique(
                [item_id for slide in section_slides for item_id in slide.linked_root_cause_ids]
            ),
            linked_validation_report_ids=_unique(
                [item_id for slide in section_slides for item_id in slide.linked_validation_report_ids]
            ),
            linked_reasoning_ids=_unique(
                [item_id for slide in section_slides for item_id in slide.linked_reasoning_ids]
            ),
        )
        sections.append(
            StoryboardSection(
                section_id=section_id,
                title=section_title,
                order=section_order,
                slides=section_slides,
                metadata=section_trace,
            )
        )

    resolved_dataset = dataset_id
    resolved_domain = domain
    if reasonings_c is not None:
        resolved_dataset = resolved_dataset or reasonings_c.dataset_id
        resolved_domain = resolved_domain or reasonings_c.domain
    if decisions_c is not None:
        resolved_dataset = resolved_dataset or decisions_c.dataset_id
        resolved_domain = resolved_domain or decisions_c.domain
    if root_causes_c is not None:
        resolved_dataset = resolved_dataset or root_causes_c.dataset_id
        resolved_domain = resolved_domain or root_causes_c.domain
    if primary is not None:
        resolved_dataset = resolved_dataset or primary.dataset_id
        resolved_domain = resolved_domain or primary.domain

    title = "Executive Storyboard"
    if primary is not None and primary.headline:
        title = primary.headline
    elif reasonings_c is not None and reasonings_c.summary.headline:
        title = reasonings_c.summary.headline

    summary = _build_summary(
        primary=primary,
        reasonings=reasonings_c,
        decisions=decisions_c,
        root_causes=root_causes_c,
        slides=slides,
        sections=sections,
        domain=resolved_domain,
    )

    storyboard_id = f"storyboard_{resolved_dataset or (primary.reasoning_id if primary else 'empty')}"
    return ExecutiveStoryboard(
        storyboard_id=storyboard_id,
        dataset_id=resolved_dataset,
        domain=resolved_domain,
        title=title,
        sections=sections,
        slides=slides,
        summary=summary,
        generated_at=utc_now_iso(),
        metadata=StoryboardMetadata(
            legacy={"schema": STORYBOARD_SCHEMA_VERSION},
            debug={
                "slide_count": len(slides),
                "section_count": len(sections),
                "has_reasonings": reasonings_c is not None,
                "has_decisions": decisions_c is not None,
                "has_root_causes": root_causes_c is not None,
                "validation_count": len(validations_c),
            },
            custom={},
            future_extensions=empty_storyboard_future_extensions(),
            linked_insight_ids=trace.linked_insight_ids,
            linked_decision_ids=trace.linked_decision_ids,
            linked_root_cause_ids=trace.linked_root_cause_ids,
            linked_validation_report_ids=trace.linked_validation_report_ids,
            linked_reasoning_ids=trace.linked_reasoning_ids,
        ),
    )


def build_storyboard_collection(
    storyboards: list[ExecutiveStoryboard] | None = None,
    *,
    reasonings: ExecutiveReasoningCollection | None = None,
    decisions: DecisionCollection | None = None,
    root_causes: RootCauseCollection | None = None,
    validations: list[ValidationReport] | None = None,
    dataset_id: str | None = None,
) -> StoryboardCollection:
    """Build a storyboard collection from existing storyboards or upstream collections."""
    items = [item.model_copy(deep=True) for item in (storyboards or [])]
    if not items:
        items.append(
            build_executive_storyboard_from_reasoning(
                reasonings=reasonings,
                decisions=decisions,
                root_causes=root_causes,
                validations=validations,
                dataset_id=dataset_id,
            )
        )

    resolved_dataset = dataset_id or next((item.dataset_id for item in items if item.dataset_id), None)
    metadata = StoryboardMetadata(
        legacy={"schema": STORYBOARD_SCHEMA_VERSION},
        debug={"storyboard_count": len(items)},
        future_extensions=empty_storyboard_future_extensions(),
        linked_insight_ids=_unique([item_id for board in items for item_id in board.metadata.linked_insight_ids]),
        linked_decision_ids=_unique([item_id for board in items for item_id in board.metadata.linked_decision_ids]),
        linked_root_cause_ids=_unique(
            [item_id for board in items for item_id in board.metadata.linked_root_cause_ids]
        ),
        linked_validation_report_ids=_unique(
            [item_id for board in items for item_id in board.metadata.linked_validation_report_ids]
        ),
        linked_reasoning_ids=_unique([item_id for board in items for item_id in board.metadata.linked_reasoning_ids]),
    )
    return StoryboardCollection(
        dataset_id=resolved_dataset,
        storyboards=items,
        generated_at=utc_now_iso(),
        metadata=metadata,
    )
