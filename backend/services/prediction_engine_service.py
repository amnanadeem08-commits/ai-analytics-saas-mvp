from __future__ import annotations

from typing import Any

from backend.models.ai_analyst_models import AIAnalystResponse, ConversationContext
from backend.models.ai_insight_models import UniversalAIInsight, UniversalAIInsightCollection, utc_now_iso
from backend.models.analyst_skill_models import AnalystSkillRegistry
from backend.models.decision_models import DecisionCollection, DecisionRecommendation, DecisionTimeHorizon
from backend.models.executive_reasoning_models import ExecutiveReasoning, ExecutiveReasoningCollection
from backend.models.intelligence_bundle_models import IntelligenceBundle
from backend.models.intelligence_registry_models import IntelligenceRegistry
from backend.models.prediction_models import (
    PREDICTION_SCHEMA_VERSION,
    ConfidenceInterval,
    Prediction,
    PredictionCollection,
    PredictionEvidence,
    PredictionExplanation,
    PredictionMetadata,
    PredictionRange,
    PredictionScenario,
    PredictionStatistics,
    PredictionStatus,
    PredictionSummary,
    PredictionTimeHorizon,
    PredictionType,
    ScenarioKind,
    empty_prediction_future_extensions,
)
from backend.models.root_cause_models import RootCause, RootCauseCollection
from backend.models.storyboard_models import ExecutiveStoryboard
from backend.models.validation_models import ValidationReport

_INSUFFICIENT_NOTE = "Insufficient existing intelligence to justify a prediction."


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


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _map_horizon(raw: object | None) -> PredictionTimeHorizon:
    if raw is None:
        return PredictionTimeHorizon.unknown
    value = getattr(raw, "value", raw)
    text = str(value)
    for item in PredictionTimeHorizon:
        if item.value == text or item.name == text.lower():
            return item
    mapping = {
        DecisionTimeHorizon.immediate.value: PredictionTimeHorizon.immediate,
        DecisionTimeHorizon.short_term.value: PredictionTimeHorizon.short_term,
        DecisionTimeHorizon.medium_term.value: PredictionTimeHorizon.medium_term,
        DecisionTimeHorizon.long_term.value: PredictionTimeHorizon.long_term,
    }
    return mapping.get(text, PredictionTimeHorizon.unknown)


def _infer_prediction_type(
    *,
    insight: UniversalAIInsight | None,
    decision: DecisionRecommendation | None,
    root_cause: RootCause | None,
) -> PredictionType:
    haystack_parts: list[str] = []
    if insight is not None:
        haystack_parts.extend(
            [
                insight.title,
                insight.summary,
                insight.domain or "",
                " ".join(insight.affected_metrics),
                " ".join(insight.related_kpis),
            ]
        )
    if decision is not None:
        haystack_parts.extend(
            [
                decision.title,
                decision.summary,
                decision.category.value,
                " ".join(decision.affected_metrics),
                " ".join(decision.related_kpis),
            ]
        )
    if root_cause is not None:
        haystack_parts.extend(
            [
                root_cause.title,
                root_cause.summary,
                root_cause.cause_category.value,
                " ".join(root_cause.affected_metrics),
                " ".join(root_cause.related_kpis),
            ]
        )
    text = " ".join(haystack_parts).lower()

    rules: tuple[tuple[tuple[str, ...], PredictionType], ...] = (
        (("revenue",), PredictionType.revenue),
        (("sales", "sell"), PredictionType.sales),
        (("demand", "forecast"), PredictionType.demand),
        (("inventory", "stock"), PredictionType.inventory),
        (("customer", "churn", "retention"), PredictionType.customer),
        (("risk", "mitigation", "fraud"), PredictionType.risk),
        (("cost", "margin", "profit", "financial", "finance"), PredictionType.financial),
        (("operational", "operations", "efficiency"), PredictionType.operational),
        (("kpi", "metric"), PredictionType.business_kpi),
    )
    for keywords, ptype in rules:
        if any(keyword in text for keyword in keywords):
            return ptype
    return PredictionType.custom


def _extract_metric(
    *,
    insight: UniversalAIInsight | None,
    decision: DecisionRecommendation | None,
    root_cause: RootCause | None,
) -> str:
    if decision is not None:
        if decision.related_kpis:
            return decision.related_kpis[0]
        if decision.affected_metrics:
            return decision.affected_metrics[0]
        if decision.expected_outcome_target and decision.expected_outcome_target.target_metric:
            return decision.expected_outcome_target.target_metric
    if insight is not None:
        if insight.related_kpis:
            return insight.related_kpis[0]
        if insight.affected_metrics:
            return insight.affected_metrics[0]
    if root_cause is not None:
        if root_cause.related_kpis:
            return root_cause.related_kpis[0]
        if root_cause.affected_metrics:
            return root_cause.affected_metrics[0]
    return ""


def _extract_predicted_value(
    *,
    insight: UniversalAIInsight | None,
    decision: DecisionRecommendation | None,
) -> Any:
    """Use only values already present on intelligence objects — never invent numbers."""
    if decision is not None:
        target = decision.expected_outcome_target
        if target is not None and target.target_value is not None:
            return target.target_value
        for evidence in decision.supporting_evidence:
            if evidence.value is not None:
                return evidence.value
    if insight is not None:
        for evidence in insight.supporting_evidence:
            if evidence.value is not None:
                return evidence.value
    return None


def _min_confidence(*values: float | None) -> float | None:
    present = [v for v in values if v is not None and v > 0]
    if not present:
        return None
    return round(min(present), 4)


def _build_scenarios(
    prediction_id: str,
    *,
    predicted_value: Any,
    confidence: float | None,
    assumptions: list[str],
) -> list[PredictionScenario]:
    """Scenario metadata only — no Monte Carlo / ML sampling."""
    base_conf = confidence
    optimistic_conf = round(min(1.0, (confidence or 0.0) + 0.05), 4) if confidence is not None else None
    pessimistic_conf = round(max(0.0, (confidence or 0.0) - 0.05), 4) if confidence is not None else None

    return [
        PredictionScenario(
            scenario_id=f"{prediction_id}_baseline",
            kind=ScenarioKind.baseline,
            label="Baseline",
            description="Baseline scenario from existing intelligence confidence.",
            predicted_value=predicted_value,
            prediction_confidence=base_conf,
            assumptions=list(assumptions),
            linked_prediction_id=prediction_id,
        ),
        PredictionScenario(
            scenario_id=f"{prediction_id}_expected",
            kind=ScenarioKind.expected,
            label="Expected",
            description="Expected scenario aligned to current validated intelligence.",
            predicted_value=predicted_value,
            prediction_confidence=base_conf,
            assumptions=list(assumptions),
            linked_prediction_id=prediction_id,
        ),
        PredictionScenario(
            scenario_id=f"{prediction_id}_optimistic",
            kind=ScenarioKind.optimistic,
            label="Optimistic",
            description="Optimistic metadata bound using existing confidence ceiling (+0.05 capped).",
            predicted_value=predicted_value,
            prediction_confidence=optimistic_conf,
            assumptions=list(assumptions) + ["Optimistic bound uses existing confidence only."],
            linked_prediction_id=prediction_id,
        ),
        PredictionScenario(
            scenario_id=f"{prediction_id}_pessimistic",
            kind=ScenarioKind.pessimistic,
            label="Pessimistic",
            description="Pessimistic metadata bound using existing confidence floor (-0.05 floored).",
            predicted_value=predicted_value,
            prediction_confidence=pessimistic_conf,
            assumptions=list(assumptions) + ["Pessimistic bound uses existing confidence only."],
            linked_prediction_id=prediction_id,
        ),
    ]


def build_prediction(
    *,
    insight: UniversalAIInsight | None = None,
    decision: DecisionRecommendation | None = None,
    root_cause: RootCause | None = None,
    validation: ValidationReport | None = None,
    reasoning: ExecutiveReasoning | None = None,
    storyboard: ExecutiveStoryboard | None = None,
    bundle: IntelligenceBundle | None = None,
    registry: IntelligenceRegistry | None = None,
    analyst_response: AIAnalystResponse | None = None,
    analyst_context: ConversationContext | None = None,
    skill_registry: AnalystSkillRegistry | None = None,
    dataset_id: str | None = None,
    domain: str | None = None,
) -> Prediction:
    """Build one prediction from existing intelligence. Never regenerates upstream objects."""
    insight_c = insight.model_copy(deep=True) if insight is not None else None
    decision_c = decision.model_copy(deep=True) if decision is not None else None
    root_cause_c = root_cause.model_copy(deep=True) if root_cause is not None else None
    validation_c = validation.model_copy(deep=True) if validation is not None else None
    reasoning_c = reasoning.model_copy(deep=True) if reasoning is not None else None
    storyboard_c = storyboard.model_copy(deep=True) if storyboard is not None else None
    bundle_c = bundle.model_copy(deep=True) if bundle is not None else None
    registry_c = registry.model_copy(deep=True) if registry is not None else None
    analyst_c = analyst_response.model_copy(deep=True) if analyst_response is not None else None
    context_c = analyst_context.model_copy(deep=True) if analyst_context is not None else None
    skills_c = skill_registry.model_copy(deep=True) if skill_registry is not None else None

    now = utc_now_iso()
    supporting_decisions = [decision_c.decision_id] if decision_c is not None else []
    supporting_root_causes = [root_cause_c.root_cause_id] if root_cause_c is not None else []
    supporting_insights = [insight_c.id] if insight_c is not None else []
    validation_refs = [_validation_id(validation_c)] if validation_c is not None else []
    reasoning_refs = [reasoning_c.reasoning_id] if reasoning_c is not None else []
    registry_refs: list[str] = []
    analyst_refs: list[str] = []

    if registry_c is not None:
        registry_refs = [a.reference_id or a.object_id for a in registry_c.assets]
    if analyst_c is not None:
        analyst_refs.append(analyst_c.response_id)
    if context_c is not None:
        analyst_refs.append(context_c.context_id)

    evidence: list[PredictionEvidence] = []
    if insight_c is not None:
        evidence.append(
            PredictionEvidence(
                evidence_id=f"insight:{insight_c.id}",
                object_type="insight",
                object_id=insight_c.id,
                label=insight_c.title,
                field="overall_confidence",
                value=insight_c.overall_confidence,
                confidence=insight_c.overall_confidence,
            )
        )
        for item in insight_c.supporting_evidence[:5]:
            evidence.append(
                PredictionEvidence(
                    evidence_id=f"insight_evidence:{insight_c.id}:{item.label}",
                    object_type="insight_evidence",
                    object_id=insight_c.id,
                    label=item.label,
                    field="supporting_evidence",
                    value=item.value,
                    confidence=item.confidence_score,
                )
            )
    if decision_c is not None:
        evidence.append(
            PredictionEvidence(
                evidence_id=f"decision:{decision_c.decision_id}",
                object_type="decision",
                object_id=decision_c.decision_id,
                label=decision_c.title,
                field="confidence",
                value=decision_c.confidence,
                confidence=decision_c.confidence,
            )
        )
    if root_cause_c is not None:
        evidence.append(
            PredictionEvidence(
                evidence_id=f"root_cause:{root_cause_c.root_cause_id}",
                object_type="root_cause",
                object_id=root_cause_c.root_cause_id,
                label=root_cause_c.title,
                field="confidence",
                value=root_cause_c.confidence,
                confidence=root_cause_c.confidence,
            )
        )
    if validation_c is not None:
        evidence.append(
            PredictionEvidence(
                evidence_id=f"validation:{_validation_id(validation_c)}",
                object_type="validation",
                object_id=_validation_id(validation_c),
                label="validation_score",
                field="score",
                value=validation_c.score,
                confidence=None,
            )
        )

    has_core_support = bool(supporting_insights or supporting_decisions or supporting_root_causes)
    predicted_metric = _extract_metric(insight=insight_c, decision=decision_c, root_cause=root_cause_c)
    predicted_value = _extract_predicted_value(insight=insight_c, decision=decision_c)

    confidences: list[float | None] = []
    if insight_c is not None:
        confidences.append(insight_c.overall_confidence)
    if decision_c is not None:
        confidences.append(decision_c.confidence)
    if root_cause_c is not None:
        confidences.append(root_cause_c.confidence)
    if reasoning_c is not None:
        confidences.append(reasoning_c.executive_confidence)
    prediction_confidence = _min_confidence(*confidences)

    assumptions: list[str] = []
    limitations: list[str] = []
    if insight_c is not None:
        assumptions.extend(insight_c.assumptions)
        limitations.extend(insight_c.limitations)
    if decision_c is not None:
        assumptions.extend(decision_c.assumptions)
        limitations.extend(decision_c.limitations)
    if root_cause_c is not None:
        assumptions.extend(root_cause_c.assumptions)
        limitations.extend(root_cause_c.limitations)
    assumptions = _unique(assumptions)
    limitations = _unique(limitations)

    # Justification gate: need supporting intelligence + confidence from existing objects.
    insufficient_reasons: list[str] = []
    if not has_core_support:
        insufficient_reasons.append("No supporting insight, decision, or root cause.")
    if prediction_confidence is None:
        insufficient_reasons.append("No existing confidence values available.")
    if validation_c is not None and validation_c.overall_status.value == "rejected":
        insufficient_reasons.append("Validation status is rejected.")
    if not evidence:
        insufficient_reasons.append("No evidence references available.")

    status = PredictionStatus.ready if not insufficient_reasons else PredictionStatus.insufficient

    title_parts: list[str] = []
    if decision_c is not None and decision_c.title:
        title_parts.append(decision_c.title)
    elif insight_c is not None and insight_c.title:
        title_parts.append(insight_c.title)
    elif root_cause_c is not None and root_cause_c.title:
        title_parts.append(root_cause_c.title)
    title = f"Prediction: {title_parts[0]}" if title_parts else "Prediction: unavailable"

    summary_parts: list[str] = []
    if decision_c is not None and decision_c.expected_outcome:
        summary_parts.append(decision_c.expected_outcome)
    elif insight_c is not None and insight_c.expected_outcome:
        summary_parts.append(insight_c.expected_outcome)
    elif reasoning_c is not None and reasoning_c.executive_summary:
        summary_parts.append(reasoning_c.executive_summary)
    summary = summary_parts[0] if summary_parts else _INSUFFICIENT_NOTE

    ptype = _infer_prediction_type(insight=insight_c, decision=decision_c, root_cause=root_cause_c)
    horizon = _map_horizon(decision_c.time_horizon if decision_c is not None else None)

    resolved_dataset = dataset_id
    resolved_domain = domain
    for source in (insight_c, decision_c, root_cause_c, reasoning_c, storyboard_c, bundle_c):
        if source is None:
            continue
        if resolved_dataset is None:
            resolved_dataset = getattr(source, "dataset_id", None) or getattr(source, "source_dataset", None)
        if resolved_domain is None:
            resolved_domain = getattr(source, "domain", None)

    seed = (
        (decision_c.decision_id if decision_c else None)
        or (insight_c.id if insight_c else None)
        or (root_cause_c.root_cause_id if root_cause_c else None)
        or "empty"
    )
    prediction_id = f"pred_{seed}"

    explanation = PredictionExplanation(
        explanation_id=f"expl_{prediction_id}",
        headline=title,
        rationale=summary if status == PredictionStatus.ready else _INSUFFICIENT_NOTE,
        drivers=_unique(
            ([decision_c.recommended_action] if decision_c and decision_c.recommended_action else [])
            + ([root_cause_c.summary] if root_cause_c and root_cause_c.summary else [])
        ),
        risks=_unique(
            ([decision_c.business_impact] if decision_c and decision_c.business_impact else [])
            + ([root_cause_c.business_impact] if root_cause_c and root_cause_c.business_impact else [])
        ),
        unavailable_note="; ".join(insufficient_reasons),
    )

    conf_interval = ConfidenceInterval(
        lower_confidence=round(max(0.0, prediction_confidence - 0.05), 4)
        if prediction_confidence is not None
        else None,
        upper_confidence=round(min(1.0, prediction_confidence + 0.05), 4)
        if prediction_confidence is not None
        else None,
        method="existing_intelligence_bounds",
        note="Bounds derived from min existing confidence ±0.05; not a statistical CI.",
    )

    pred_range = PredictionRange(
        lower=predicted_value,
        upper=predicted_value,
        unit="",
        source="existing_evidence" if predicted_value is not None else "unavailable",
    )

    scenarios = _build_scenarios(
        prediction_id,
        predicted_value=predicted_value,
        confidence=prediction_confidence,
        assumptions=assumptions,
    )

    skill_ids = [s.skill_id for s in skills_c.skills] if skills_c is not None else []

    return Prediction(
        prediction_id=prediction_id,
        prediction_type=ptype,
        title=title,
        summary=summary,
        predicted_metric=predicted_metric,
        predicted_value=predicted_value,
        prediction_range=pred_range,
        confidence_interval=conf_interval,
        time_horizon=horizon,
        prediction_confidence=prediction_confidence,
        prediction_status=status,
        assumptions=assumptions,
        limitations=limitations,
        supporting_decisions=supporting_decisions,
        supporting_root_causes=supporting_root_causes,
        supporting_insights=supporting_insights,
        validation_reference=validation_refs,
        reasoning_reference=reasoning_refs,
        registry_reference=_unique(registry_refs),
        analyst_reference=_unique(analyst_refs),
        bundle_reference=bundle_c.bundle_id if bundle_c is not None else None,
        storyboard_reference=storyboard_c.storyboard_id if storyboard_c is not None else None,
        scenarios=scenarios,
        explanation=explanation,
        evidence=evidence,
        dataset_id=resolved_dataset,
        domain=resolved_domain or (insight_c.domain if insight_c else None),
        generated_at=now,
        metadata=PredictionMetadata(
            legacy={"schema": PREDICTION_SCHEMA_VERSION},
            debug={
                "status": status.value,
                "has_insight": insight_c is not None,
                "has_decision": decision_c is not None,
                "has_root_cause": root_cause_c is not None,
                "has_validation": validation_c is not None,
                "has_bundle": bundle_c is not None,
                "has_registry": registry_c is not None,
                "has_analyst": analyst_c is not None,
                "skill_count": len(skill_ids),
                "insufficient_reasons": insufficient_reasons,
            },
            custom={},
            future_extensions=empty_prediction_future_extensions(),
        ),
    )


def rank_predictions(predictions: list[Prediction]) -> list[Prediction]:
    """Rank by existing confidence then ready status. Does not invent scores."""

    def sort_key(item: Prediction) -> tuple:
        status_rank = 0 if item.prediction_status == PredictionStatus.ready else 1
        conf = item.prediction_confidence if item.prediction_confidence is not None else -1.0
        return (status_rank, -conf, item.prediction_id)

    ranked = [item.model_copy(deep=True) for item in sorted(predictions, key=sort_key)]
    for index, item in enumerate(ranked, start=1):
        item.prediction_rank = index
    return ranked


def group_predictions(predictions: list[Prediction]) -> dict[str, list[Prediction]]:
    """Group deep copies by prediction_type value."""
    groups: dict[str, list[Prediction]] = {}
    for item in predictions:
        key = item.prediction_type.value
        groups.setdefault(key, []).append(item.model_copy(deep=True))
    return groups


def summarize_predictions(predictions: list[Prediction]) -> PredictionSummary:
    type_breakdown: dict[str, int] = {}
    datasets: list[str] = []
    domains: list[str] = []
    confidences: list[float] = []
    ready = insufficient = rejected = draft = 0
    top_id: str | None = None
    headline = ""

    ranked = rank_predictions(predictions)
    if ranked:
        top_id = ranked[0].prediction_id
        headline = ranked[0].title

    for item in predictions:
        type_breakdown[item.prediction_type.value] = type_breakdown.get(item.prediction_type.value, 0) + 1
        if item.dataset_id:
            datasets.append(item.dataset_id)
        if item.domain:
            domains.append(item.domain)
        if item.prediction_confidence is not None:
            confidences.append(item.prediction_confidence)
        if item.prediction_status == PredictionStatus.ready:
            ready += 1
        elif item.prediction_status == PredictionStatus.insufficient:
            insufficient += 1
        elif item.prediction_status == PredictionStatus.rejected:
            rejected += 1
        elif item.prediction_status == PredictionStatus.draft:
            draft += 1

    return PredictionSummary(
        total_predictions=len(predictions),
        ready_count=ready,
        insufficient_count=insufficient,
        rejected_count=rejected,
        draft_count=draft,
        type_breakdown=type_breakdown,
        top_prediction_id=top_id,
        headline=headline,
        average_confidence=_avg(confidences),
        datasets=sorted(set(datasets)),
        domains=sorted(set(domains)),
    )


def prediction_statistics(predictions: list[Prediction]) -> PredictionStatistics:
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_horizon: dict[str, int] = {}
    scenario_counts: dict[str, int] = {}
    confidences: list[float] = []
    with_evidence = 0
    without_evidence = 0

    for item in predictions:
        by_type[item.prediction_type.value] = by_type.get(item.prediction_type.value, 0) + 1
        by_status[item.prediction_status.value] = by_status.get(item.prediction_status.value, 0) + 1
        by_horizon[item.time_horizon.value] = by_horizon.get(item.time_horizon.value, 0) + 1
        if item.prediction_confidence is not None:
            confidences.append(item.prediction_confidence)
        if item.evidence:
            with_evidence += 1
        else:
            without_evidence += 1
        for scenario in item.scenarios:
            scenario_counts[scenario.kind.value] = scenario_counts.get(scenario.kind.value, 0) + 1

    return PredictionStatistics(
        counts={"total": len(predictions)},
        by_type=by_type,
        by_status=by_status,
        by_horizon=by_horizon,
        confidence_average=_avg(confidences),
        scenario_counts=scenario_counts,
        with_evidence=with_evidence,
        without_evidence=without_evidence,
    )


def find_prediction(
    collection: PredictionCollection,
    prediction_id: str,
) -> Prediction | None:
    for item in collection.predictions:
        if item.prediction_id == prediction_id:
            return item.model_copy(deep=True)
    return None


def validate_predictions(collection: PredictionCollection) -> dict[str, object]:
    """Structural integrity only — never modifies predictions."""
    issues: list[str] = []
    seen: set[str] = set()

    for item in collection.predictions:
        if not item.prediction_id:
            issues.append("Prediction missing prediction_id")
            continue
        if item.prediction_id in seen:
            issues.append(f"Duplicate prediction_id: {item.prediction_id}")
        seen.add(item.prediction_id)

        if item.prediction_status == PredictionStatus.ready:
            if not (
                item.supporting_insights
                or item.supporting_decisions
                or item.supporting_root_causes
            ):
                issues.append(f"Ready prediction lacks support refs: {item.prediction_id}")
            if item.prediction_confidence is None:
                issues.append(f"Ready prediction missing confidence: {item.prediction_id}")
            if not item.evidence:
                issues.append(f"Ready prediction missing evidence: {item.prediction_id}")

        if item.prediction_status == PredictionStatus.insufficient:
            if item.explanation and not item.explanation.unavailable_note:
                issues.append(f"Insufficient prediction missing unavailable_note: {item.prediction_id}")

        required_kinds = {ScenarioKind.baseline, ScenarioKind.optimistic, ScenarioKind.pessimistic, ScenarioKind.expected}
        present_kinds = {s.kind for s in item.scenarios}
        if item.scenarios and not required_kinds.issubset(present_kinds):
            issues.append(f"Incomplete scenarios: {item.prediction_id}")

        required_extensions = set(empty_prediction_future_extensions().keys())
        missing_extensions = sorted(required_extensions - set(item.metadata.future_extensions.keys()))
        if missing_extensions:
            issues.append(f"Missing future_extensions on {item.prediction_id}: {', '.join(missing_extensions)}")

    required_extensions = set(empty_prediction_future_extensions().keys())
    missing_collection = sorted(required_extensions - set(collection.metadata.future_extensions.keys()))
    if missing_collection:
        issues.append(f"Missing collection future_extensions: {', '.join(missing_collection)}")

    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "collection_id": collection.collection_id,
        "prediction_count": len(collection.predictions),
    }


def build_prediction_collection(
    *,
    insights: UniversalAIInsightCollection | None = None,
    validations: list[ValidationReport] | None = None,
    decisions: DecisionCollection | None = None,
    root_causes: RootCauseCollection | None = None,
    reasonings: ExecutiveReasoningCollection | None = None,
    storyboard: ExecutiveStoryboard | None = None,
    bundle: IntelligenceBundle | None = None,
    registry: IntelligenceRegistry | None = None,
    analyst_response: AIAnalystResponse | None = None,
    analyst_context: ConversationContext | None = None,
    skill_registry: AnalystSkillRegistry | None = None,
    dataset_id: str | None = None,
    domain: str | None = None,
) -> PredictionCollection:
    """Build predictions from existing collections. One prediction per decision when present."""
    insights_c = insights.model_copy(deep=True) if insights is not None else None
    decisions_c = decisions.model_copy(deep=True) if decisions is not None else None
    root_causes_c = root_causes.model_copy(deep=True) if root_causes is not None else None
    reasonings_c = reasonings.model_copy(deep=True) if reasonings is not None else None
    storyboard_c = storyboard.model_copy(deep=True) if storyboard is not None else None
    bundle_c = bundle.model_copy(deep=True) if bundle is not None else None
    registry_c = registry.model_copy(deep=True) if registry is not None else None
    analyst_c = analyst_response.model_copy(deep=True) if analyst_response is not None else None
    context_c = analyst_context.model_copy(deep=True) if analyst_context is not None else None
    skills_c = skill_registry.model_copy(deep=True) if skill_registry is not None else None
    validations_c = [item.model_copy(deep=True) for item in (validations or [])]

    if bundle_c is not None:
        if insights_c is None and bundle_c.insights is not None:
            insights_c = bundle_c.insights.model_copy(deep=True)
        if decisions_c is None and bundle_c.decisions is not None:
            decisions_c = bundle_c.decisions.model_copy(deep=True)
        if root_causes_c is None and bundle_c.root_causes is not None:
            root_causes_c = bundle_c.root_causes.model_copy(deep=True)
        if reasonings_c is None and bundle_c.reasonings is not None:
            reasonings_c = bundle_c.reasonings.model_copy(deep=True)
        if storyboard_c is None and bundle_c.storyboard is not None:
            storyboard_c = bundle_c.storyboard.model_copy(deep=True)
        if not validations_c and bundle_c.validations:
            validations_c = [item.model_copy(deep=True) for item in bundle_c.validations]

    resolved_dataset = dataset_id
    resolved_domain = domain
    for source in (insights_c, decisions_c, root_causes_c, reasonings_c, storyboard_c, bundle_c):
        if source is None:
            continue
        if resolved_dataset is None and getattr(source, "dataset_id", None):
            resolved_dataset = source.dataset_id
        if resolved_domain is None and getattr(source, "domain", None):
            resolved_domain = source.domain

    insight_by_id = {i.id: i for i in (insights_c.insights if insights_c else [])}
    root_by_decision = {
        rc.source_decision_id: rc
        for rc in (root_causes_c.root_causes if root_causes_c else [])
        if rc.source_decision_id
    }
    root_by_insight = {
        rc.source_insight_id: rc
        for rc in (root_causes_c.root_causes if root_causes_c else [])
        if rc.source_insight_id
    }
    primary_reasoning = reasonings_c.reasonings[0] if reasonings_c and reasonings_c.reasonings else None
    primary_validation = validations_c[0] if validations_c else None

    predictions: list[Prediction] = []

    if decisions_c is not None and decisions_c.decisions:
        for decision in decisions_c.decisions:
            insight = insight_by_id.get(decision.source_insight_id)
            root = root_by_decision.get(decision.decision_id) or (
                root_by_insight.get(decision.source_insight_id) if decision.source_insight_id else None
            )
            predictions.append(
                build_prediction(
                    insight=insight,
                    decision=decision,
                    root_cause=root,
                    validation=primary_validation,
                    reasoning=primary_reasoning,
                    storyboard=storyboard_c,
                    bundle=bundle_c,
                    registry=registry_c,
                    analyst_response=analyst_c,
                    analyst_context=context_c,
                    skill_registry=skills_c,
                    dataset_id=resolved_dataset,
                    domain=resolved_domain,
                )
            )
    elif insights_c is not None and insights_c.insights:
        for insight in insights_c.insights:
            root = root_by_insight.get(insight.id)
            predictions.append(
                build_prediction(
                    insight=insight,
                    root_cause=root,
                    validation=primary_validation,
                    reasoning=primary_reasoning,
                    storyboard=storyboard_c,
                    bundle=bundle_c,
                    registry=registry_c,
                    analyst_response=analyst_c,
                    analyst_context=context_c,
                    skill_registry=skills_c,
                    dataset_id=resolved_dataset,
                    domain=resolved_domain,
                )
            )
    else:
        # Explicit empty / insufficient collection when no core intelligence provided.
        predictions.append(
            build_prediction(
                validation=primary_validation,
                reasoning=primary_reasoning,
                storyboard=storyboard_c,
                bundle=bundle_c,
                registry=registry_c,
                analyst_response=analyst_c,
                analyst_context=context_c,
                skill_registry=skills_c,
                dataset_id=resolved_dataset,
                domain=resolved_domain,
            )
        )

    ranked = rank_predictions(predictions)
    now = utc_now_iso()
    return PredictionCollection(
        collection_id=f"pred_coll_{resolved_dataset or 'empty'}_{now.replace(':', '').replace('-', '')}",
        dataset_id=resolved_dataset,
        domain=resolved_domain,
        predictions=ranked,
        summary=summarize_predictions(ranked),
        statistics=prediction_statistics(ranked),
        generated_at=now,
        metadata=PredictionMetadata(
            legacy={"schema": PREDICTION_SCHEMA_VERSION},
            debug={"prediction_count": len(ranked)},
            custom={},
            future_extensions=empty_prediction_future_extensions(),
        ),
    )
