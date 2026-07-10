from __future__ import annotations

from backend.models.ai_insight_models import (
    UniversalAIInsightCollection,
    ValidationStatus,
    utc_now_iso,
)
from backend.models.decision_models import DecisionCollection
from backend.models.executive_reasoning_models import ExecutiveReasoningCollection
from backend.models.intelligence_bundle_models import (
    INTELLIGENCE_BUNDLE_SCHEMA_VERSION,
    BundleMetadata,
    BundleReferences,
    BundleStatistics,
    BundleSummary,
    IntelligenceBundle,
    empty_intelligence_bundle_future_extensions,
)
from backend.models.root_cause_models import RootCauseCollection
from backend.models.storyboard_models import ExecutiveStoryboard
from backend.models.validation_models import ValidationReport


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _avg(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def _increment(mapping: dict[str, int], key: str) -> None:
    mapping[key] = mapping.get(key, 0) + 1


def _validation_id(report: ValidationReport) -> str:
    return f"validation_{report.validator_version}_{report.validated_at}"


def bundle_references(
    insights: UniversalAIInsightCollection | None = None,
    validations: list[ValidationReport] | None = None,
    decisions: DecisionCollection | None = None,
    root_causes: RootCauseCollection | None = None,
    reasonings: ExecutiveReasoningCollection | None = None,
    storyboard: ExecutiveStoryboard | None = None,
) -> BundleReferences:
    """Collect traceability IDs from existing objects only."""
    insight_ids: list[str] = []
    decision_ids: list[str] = []
    root_cause_ids: list[str] = []
    storyboard_ids: list[str] = []
    validation_ids: list[str] = []
    reasoning_ids: list[str] = []

    if insights is not None:
        insight_ids.extend(item.id for item in insights.insights)
    if validations:
        validation_ids.extend(_validation_id(item) for item in validations)
    if decisions is not None:
        decision_ids.extend(item.decision_id for item in decisions.decisions)
    if root_causes is not None:
        root_cause_ids.extend(item.root_cause_id for item in root_causes.root_causes)
    if reasonings is not None:
        reasoning_ids.extend(item.reasoning_id for item in reasonings.reasonings)
        insight_ids.extend(reasonings.metadata.linked_insight_ids)
        decision_ids.extend(reasonings.metadata.linked_decision_ids)
        root_cause_ids.extend(reasonings.metadata.linked_root_cause_ids)
        validation_ids.extend(reasonings.metadata.linked_validation_report_ids)
    if storyboard is not None:
        storyboard_ids.append(storyboard.storyboard_id)
        insight_ids.extend(storyboard.metadata.linked_insight_ids)
        decision_ids.extend(storyboard.metadata.linked_decision_ids)
        root_cause_ids.extend(storyboard.metadata.linked_root_cause_ids)
        validation_ids.extend(storyboard.metadata.linked_validation_report_ids)
        reasoning_ids.extend(storyboard.metadata.linked_reasoning_ids)

    return BundleReferences(
        insight_ids=_unique(insight_ids),
        decision_ids=_unique(decision_ids),
        root_cause_ids=_unique(root_cause_ids),
        storyboard_ids=_unique(storyboard_ids),
        validation_ids=_unique(validation_ids),
        reasoning_ids=_unique(reasoning_ids),
    )


def bundle_statistics(
    insights: UniversalAIInsightCollection | None = None,
    validations: list[ValidationReport] | None = None,
    decisions: DecisionCollection | None = None,
    root_causes: RootCauseCollection | None = None,
    reasonings: ExecutiveReasoningCollection | None = None,
    storyboard: ExecutiveStoryboard | None = None,
) -> BundleStatistics:
    """Aggregate counts and averages from existing objects — no new analytics."""
    counts = {
        "insights": len(insights.insights) if insights is not None else 0,
        "validations": len(validations or []),
        "decisions": len(decisions.decisions) if decisions is not None else 0,
        "root_causes": len(root_causes.root_causes) if root_causes is not None else 0,
        "reasonings": len(reasonings.reasonings) if reasonings is not None else 0,
        "storyboards": 1 if storyboard is not None else 0,
    }

    confidence_values: dict[str, list[float]] = {
        "insights": [],
        "decisions": [],
        "root_causes": [],
        "reasonings": [],
    }
    risk_distribution: dict[str, int] = {}
    priority_distribution: dict[str, int] = {}
    category_distribution: dict[str, int] = {}
    validation_scores: list[float] = []

    if insights is not None:
        for item in insights.insights:
            if item.overall_confidence > 0:
                confidence_values["insights"].append(item.overall_confidence)
            _increment(risk_distribution, item.risk_level.value)
            _increment(priority_distribution, item.priority.value)

    if decisions is not None:
        for item in decisions.decisions:
            if item.confidence > 0:
                confidence_values["decisions"].append(item.confidence)
            _increment(risk_distribution, item.risk_level.value)
            _increment(priority_distribution, item.priority.value)
            _increment(category_distribution, item.category.value)

    if root_causes is not None:
        for item in root_causes.root_causes:
            if item.confidence > 0:
                confidence_values["root_causes"].append(item.confidence)
            _increment(risk_distribution, item.severity.value)
            _increment(category_distribution, item.cause_category.value)

    if reasonings is not None:
        for item in reasonings.reasonings:
            if item.executive_confidence > 0:
                confidence_values["reasonings"].append(item.executive_confidence)

    if validations:
        for item in validations:
            validation_scores.append(float(item.score))

    return BundleStatistics(
        counts=counts,
        confidence_averages={key: _avg(values) for key, values in confidence_values.items()},
        validation_averages={"score": _avg(validation_scores)},
        risk_distribution=risk_distribution,
        priority_distribution=priority_distribution,
        category_distribution=category_distribution,
    )


def bundle_summary(
    *,
    dataset_id: str | None,
    domain: str | None,
    insights: UniversalAIInsightCollection | None,
    validations: list[ValidationReport] | None,
    decisions: DecisionCollection | None,
    root_causes: RootCauseCollection | None,
    reasonings: ExecutiveReasoningCollection | None,
    storyboard: ExecutiveStoryboard | None,
    generated_at: str,
) -> BundleSummary:
    """Build a compact summary from existing collection fields only."""
    overall_health = ""
    if decisions is not None and decisions.summary.overall_business_health:
        overall_health = decisions.summary.overall_business_health
    elif storyboard is not None and storyboard.summary.validation_status:
        overall_health = storyboard.summary.validation_status.value

    overall_validation = ValidationStatus.pending
    if validations:
        # Prefer the first report's status; no new validation logic.
        overall_validation = validations[0].overall_status
    elif reasonings is not None and reasonings.reasonings:
        overall_validation = reasonings.reasonings[0].overall_validation_status
    elif storyboard is not None:
        overall_validation = storyboard.summary.validation_status

    return BundleSummary(
        dataset_id=dataset_id,
        domain=domain,
        overall_health=overall_health,
        overall_validation=overall_validation,
        total_insights=len(insights.insights) if insights is not None else 0,
        total_decisions=len(decisions.decisions) if decisions is not None else 0,
        total_root_causes=len(root_causes.root_causes) if root_causes is not None else 0,
        total_storyboards=1 if storyboard is not None else 0,
        total_reasonings=len(reasonings.reasonings) if reasonings is not None else 0,
        total_validations=len(validations or []),
        generated_at=generated_at,
    )


def validate_bundle(bundle: IntelligenceBundle) -> dict[str, object]:
    """Structural integrity checks only — no business validation."""
    issues: list[str] = []
    refs = bundle.references

    if bundle.insights is not None:
        for insight_id in (item.id for item in bundle.insights.insights):
            if insight_id not in refs.insight_ids:
                issues.append(f"Missing insight reference: {insight_id}")
    if bundle.decisions is not None:
        for decision_id in (item.decision_id for item in bundle.decisions.decisions):
            if decision_id not in refs.decision_ids:
                issues.append(f"Missing decision reference: {decision_id}")
    if bundle.root_causes is not None:
        for root_id in (item.root_cause_id for item in bundle.root_causes.root_causes):
            if root_id not in refs.root_cause_ids:
                issues.append(f"Missing root cause reference: {root_id}")
    if bundle.storyboard is not None and bundle.storyboard.storyboard_id not in refs.storyboard_ids:
        issues.append(f"Missing storyboard reference: {bundle.storyboard.storyboard_id}")
    if bundle.validations:
        for report in bundle.validations:
            report_id = _validation_id(report)
            if report_id not in refs.validation_ids:
                issues.append(f"Missing validation reference: {report_id}")

    required_extensions = set(empty_intelligence_bundle_future_extensions().keys())
    missing_extensions = sorted(required_extensions - set(bundle.metadata.future_extensions.keys()))
    if missing_extensions:
        issues.append(f"Missing future_extensions: {', '.join(missing_extensions)}")

    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "bundle_id": bundle.bundle_id,
    }


def build_intelligence_bundle(
    *,
    insights: UniversalAIInsightCollection | None = None,
    validations: list[ValidationReport] | None = None,
    decisions: DecisionCollection | None = None,
    root_causes: RootCauseCollection | None = None,
    reasonings: ExecutiveReasoningCollection | None = None,
    storyboard: ExecutiveStoryboard | None = None,
    dataset_id: str | None = None,
    domain: str | None = None,
) -> IntelligenceBundle:
    """Orchestrate existing intelligence collections into one canonical bundle.

    Aggregation only. Does not regenerate insights, decisions, RCA, reasoning, or storyboards.
    """
    insights_c = insights.model_copy(deep=True) if insights is not None else None
    decisions_c = decisions.model_copy(deep=True) if decisions is not None else None
    root_causes_c = root_causes.model_copy(deep=True) if root_causes is not None else None
    reasonings_c = reasonings.model_copy(deep=True) if reasonings is not None else None
    storyboard_c = storyboard.model_copy(deep=True) if storyboard is not None else None
    validations_c = [item.model_copy(deep=True) for item in (validations or [])]

    resolved_dataset = dataset_id
    resolved_domain = domain
    for source in (insights_c, decisions_c, root_causes_c, reasonings_c, storyboard_c):
        if source is None:
            continue
        if resolved_dataset is None and getattr(source, "dataset_id", None):
            resolved_dataset = source.dataset_id
        if resolved_domain is None and getattr(source, "domain", None):
            resolved_domain = source.domain

    generated_at = utc_now_iso()
    references = bundle_references(
        insights=insights_c,
        validations=validations_c,
        decisions=decisions_c,
        root_causes=root_causes_c,
        reasonings=reasonings_c,
        storyboard=storyboard_c,
    )
    statistics = bundle_statistics(
        insights=insights_c,
        validations=validations_c,
        decisions=decisions_c,
        root_causes=root_causes_c,
        reasonings=reasonings_c,
        storyboard=storyboard_c,
    )
    summary = bundle_summary(
        dataset_id=resolved_dataset,
        domain=resolved_domain,
        insights=insights_c,
        validations=validations_c,
        decisions=decisions_c,
        root_causes=root_causes_c,
        reasonings=reasonings_c,
        storyboard=storyboard_c,
        generated_at=generated_at,
    )

    bundle_id = f"bundle_{resolved_dataset or 'empty'}_{generated_at.replace(':', '').replace('-', '')}"
    return IntelligenceBundle(
        bundle_id=bundle_id,
        dataset_id=resolved_dataset,
        domain=resolved_domain,
        insights=insights_c,
        validations=validations_c,
        decisions=decisions_c,
        root_causes=root_causes_c,
        reasonings=reasonings_c,
        storyboard=storyboard_c,
        summary=summary,
        statistics=statistics,
        references=references,
        generated_at=generated_at,
        metadata=BundleMetadata(
            legacy={"schema": INTELLIGENCE_BUNDLE_SCHEMA_VERSION},
            debug={
                "has_insights": insights_c is not None,
                "has_decisions": decisions_c is not None,
                "has_root_causes": root_causes_c is not None,
                "has_reasonings": reasonings_c is not None,
                "has_storyboard": storyboard_c is not None,
                "validation_count": len(validations_c),
            },
            custom={},
            future_extensions=empty_intelligence_bundle_future_extensions(),
        ),
    )
