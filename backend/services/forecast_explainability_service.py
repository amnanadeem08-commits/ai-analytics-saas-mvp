from __future__ import annotations

from typing import Any

from backend.models.ai_insight_models import utc_now_iso
from backend.models.forecast_explainability_models import (
    DEFAULT_EXPLANATION_SECTION_SPECS,
    FORECAST_EXPLAINABILITY_SCHEMA_VERSION,
    REQUIRED_SECTION_TYPES,
    ExplanationMetadata,
    ExplanationSection,
    ExplanationStatistics,
    ExplanationStatus,
    ExplanationSummary,
    ExplanationTraceability,
    ForecastExplanation,
    SectionType,
    empty_forecast_explainability_future_extensions,
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


def _parse_status(raw: Any) -> ExplanationStatus:
    if isinstance(raw, ExplanationStatus):
        return raw
    if raw is None or raw == "":
        return ExplanationStatus.planned
    return ExplanationStatus(str(raw).strip().lower())


def _parse_section_type(raw: Any) -> SectionType:
    if isinstance(raw, SectionType):
        return raw
    return SectionType(str(raw).strip().lower())


def _section_is_complete(section: ExplanationSection) -> bool:
    return bool(str(section.content or "").strip()) or bool(section.references)


def _build_default_sections() -> list[ExplanationSection]:
    sections: list[ExplanationSection] = []
    for order, (section_id, section_name, section_type) in enumerate(
        DEFAULT_EXPLANATION_SECTION_SPECS, start=1
    ):
        sections.append(
            ExplanationSection(
                section_id=section_id,
                section_name=section_name,
                section_type=section_type,
                display_order=order,
                content="",
                references=[],
                metadata={"template": True},
            )
        )
    return sections


def _hydrate_section_content(
    sections: list[ExplanationSection],
    *,
    summary: str,
    forecast_horizon: str,
    confidence_level: str,
    key_drivers: list[str],
    assumptions: list[str],
    limitations: list[str],
    supporting_evidence: list[str],
    related_predictions: list[str],
    related_decisions: list[str],
    related_root_causes: list[str],
    prediction_id: str | None,
    dataset_id: str | None,
    scenario_id: str | None,
    adapter_id: str | None,
) -> list[ExplanationSection]:
    """Populate section content from provided metadata fields only. No narrative generation."""
    result: list[ExplanationSection] = []
    for section in sections:
        item = section.model_copy(deep=True)
        if item.section_id == "sec_overview" and summary:
            item.content = summary
        elif item.section_id == "sec_forecast_horizon" and forecast_horizon:
            item.content = forecast_horizon
        elif item.section_id == "sec_confidence" and confidence_level:
            item.content = confidence_level
        elif item.section_id == "sec_key_drivers" and key_drivers:
            item.content = "; ".join(key_drivers)
            item.references = list(key_drivers)
        elif item.section_id == "sec_supporting_evidence" and supporting_evidence:
            item.content = "; ".join(supporting_evidence)
            item.references = list(supporting_evidence)
        elif item.section_id == "sec_assumptions" and assumptions:
            item.content = "; ".join(assumptions)
            item.references = list(assumptions)
        elif item.section_id == "sec_limitations" and limitations:
            item.content = "; ".join(limitations)
            item.references = list(limitations)
        elif item.section_id == "sec_traceability":
            links = [
                f"prediction_id={prediction_id or ''}",
                f"dataset_id={dataset_id or ''}",
                f"scenario_id={scenario_id or ''}",
                f"adapter_id={adapter_id or ''}",
            ]
            item.content = "; ".join(links)
            item.references = _unique(
                [prediction_id or "", dataset_id or "", scenario_id or "", adapter_id or ""]
                + related_predictions
                + related_decisions
                + related_root_causes
            )
        elif item.section_id == "sec_references":
            refs = _unique(
                related_predictions + related_decisions + related_root_causes
            )
            item.references = refs
            if refs:
                item.content = "; ".join(refs)
        result.append(item)
    return result


def build_default_explanation(
    *,
    prediction_id: str | None = None,
    dataset_id: str | None = None,
    scenario_id: str | None = None,
    adapter_id: str | None = None,
) -> ForecastExplanation:
    """Build a template explanation with default empty sections. Metadata only."""
    return build_explanation(
        prediction_id=prediction_id,
        dataset_id=dataset_id,
        scenario_id=scenario_id,
        adapter_id=adapter_id,
        explanation_status=ExplanationStatus.planned,
        summary="",
        forecast_horizon="",
        confidence_level="",
        key_drivers=[],
        assumptions=[],
        limitations=[],
        supporting_evidence=[],
        related_predictions=[],
        related_decisions=[],
        related_root_causes=[],
        include_default_sections=True,
    )


def build_explanation(
    *,
    prediction_id: str | None = None,
    dataset_id: str | None = None,
    scenario_id: str | None = None,
    adapter_id: str | None = None,
    explanation_status: ExplanationStatus | str = ExplanationStatus.planned,
    summary: str = "",
    forecast_horizon: str = "",
    confidence_level: str = "",
    key_drivers: list[str] | None = None,
    assumptions: list[str] | None = None,
    limitations: list[str] | None = None,
    supporting_evidence: list[str] | None = None,
    related_predictions: list[str] | None = None,
    related_decisions: list[str] | None = None,
    related_root_causes: list[str] | None = None,
    sections: list[ExplanationSection] | None = None,
    include_default_sections: bool = True,
    created_at: str | None = None,
    updated_at: str | None = None,
    metadata: dict[str, Any] | ExplanationMetadata | None = None,
) -> ForecastExplanation:
    """Construct a ForecastExplanation from caller-supplied metadata. Never forecasts or attributes."""
    now = utc_now_iso()
    drivers = list(key_drivers or [])
    assumptions_list = list(assumptions or [])
    limitations_list = list(limitations or [])
    evidence = list(supporting_evidence or [])
    pred_refs = list(related_predictions or [])
    decision_refs = list(related_decisions or [])
    rca_refs = list(related_root_causes or [])
    status = _parse_status(explanation_status)

    if sections is not None:
        built_sections = [s.model_copy(deep=True) for s in sections]
    elif include_default_sections:
        built_sections = _build_default_sections()
        built_sections = _hydrate_section_content(
            built_sections,
            summary=summary,
            forecast_horizon=forecast_horizon,
            confidence_level=confidence_level,
            key_drivers=drivers,
            assumptions=assumptions_list,
            limitations=limitations_list,
            supporting_evidence=evidence,
            related_predictions=pred_refs,
            related_decisions=decision_refs,
            related_root_causes=rca_refs,
            prediction_id=prediction_id,
            dataset_id=dataset_id,
            scenario_id=scenario_id,
            adapter_id=adapter_id,
        )
    else:
        built_sections = []

    # Derive status from structural completeness when caller leaves planned and supplies content.
    if status == ExplanationStatus.planned and (
        summary or drivers or assumptions_list or limitations_list or evidence
    ):
        completed = sum(1 for s in built_sections if _section_is_complete(s))
        if completed == 0:
            status = ExplanationStatus.insufficient
        elif completed < len(built_sections):
            status = ExplanationStatus.partial
        elif built_sections:
            status = ExplanationStatus.available

    trace = ExplanationTraceability(
        prediction_id=prediction_id,
        dataset_id=dataset_id,
        scenario_id=scenario_id,
        adapter_id=adapter_id,
        related_predictions=list(pred_refs),
        related_decisions=list(decision_refs),
        related_root_causes=list(rca_refs),
        section_ids=[s.section_id for s in built_sections],
    )

    if isinstance(metadata, ExplanationMetadata):
        meta = metadata.model_copy(deep=True)
        if not meta.future_extensions:
            meta.future_extensions = empty_forecast_explainability_future_extensions()
    else:
        meta_dict = dict(metadata or {})
        future = meta_dict.get("future_extensions")
        if not isinstance(future, dict) or not future:
            future = empty_forecast_explainability_future_extensions()
        meta = ExplanationMetadata(
            legacy=dict(meta_dict.get("legacy", {})),
            debug=dict(meta_dict.get("debug", {})),
            custom=dict(meta_dict.get("custom", {})),
            future_extensions=future,
        )
    meta.debug = {
        **meta.debug,
        "section_count": len(built_sections),
        "schema": FORECAST_EXPLAINABILITY_SCHEMA_VERSION,
    }
    meta.legacy = {**meta.legacy, "schema": FORECAST_EXPLAINABILITY_SCHEMA_VERSION}

    stamp = (created_at or now).replace(":", "").replace("-", "")
    return ForecastExplanation(
        explanation_id=f"forecast_explanation_{stamp}",
        prediction_id=prediction_id,
        dataset_id=dataset_id,
        scenario_id=scenario_id,
        adapter_id=adapter_id,
        explanation_status=status,
        summary=summary,
        forecast_horizon=forecast_horizon,
        confidence_level=confidence_level,
        key_drivers=drivers,
        assumptions=assumptions_list,
        limitations=limitations_list,
        supporting_evidence=evidence,
        related_predictions=pred_refs,
        related_decisions=decision_refs,
        related_root_causes=rca_refs,
        sections=built_sections,
        traceability=trace,
        created_at=created_at or now,
        updated_at=updated_at or now,
        metadata=meta,
        schema_version=FORECAST_EXPLAINABILITY_SCHEMA_VERSION,
    )


def find_section(
    explanation: ForecastExplanation,
    section_id: str,
) -> ExplanationSection | None:
    for item in explanation.sections:
        if item.section_id == section_id:
            return item.model_copy(deep=True)
    return None


def list_sections(
    explanation: ForecastExplanation,
    *,
    section_type: SectionType | str | None = None,
) -> list[ExplanationSection]:
    type_value = (
        section_type.value if isinstance(section_type, SectionType) else section_type
    )
    results: list[ExplanationSection] = []
    for item in sorted(explanation.sections, key=lambda s: s.display_order):
        if type_value is not None and item.section_type.value != type_value:
            continue
        results.append(item.model_copy(deep=True))
    return results


def explanation_statistics(explanation: ForecastExplanation) -> ExplanationStatistics:
    completed = empty = 0
    reference_count = 0
    for section in explanation.sections:
        reference_count += len(section.references)
        if _section_is_complete(section):
            completed += 1
        else:
            empty += 1
    return ExplanationStatistics(
        total_sections=len(explanation.sections),
        completed_sections=completed,
        empty_sections=empty,
        reference_count=reference_count,
        driver_count=len(explanation.key_drivers),
        assumption_count=len(explanation.assumptions),
        limitation_count=len(explanation.limitations),
    )


def explanation_summary(explanation: ForecastExplanation) -> ExplanationSummary:
    stats = explanation_statistics(explanation)
    if stats.total_sections == 0:
        completeness = "empty"
    elif stats.completed_sections == 0:
        completeness = "insufficient"
    elif stats.completed_sections < stats.total_sections:
        completeness = "partial"
    else:
        completeness = "complete"
    return ExplanationSummary(
        explanation_status=explanation.explanation_status.value,
        forecast_horizon=explanation.forecast_horizon,
        confidence_level=explanation.confidence_level,
        section_count=stats.total_sections,
        reference_count=stats.reference_count,
        driver_count=stats.driver_count,
        overall_completeness=completeness,
    )


def traceability_map(explanation: ForecastExplanation) -> dict[str, Any]:
    """Return a read-only map of explanation trace links. No graph execution."""
    return {
        "explanation_id": explanation.explanation_id,
        "prediction_id": explanation.prediction_id,
        "dataset_id": explanation.dataset_id,
        "scenario_id": explanation.scenario_id,
        "adapter_id": explanation.adapter_id,
        "related_predictions": list(explanation.related_predictions),
        "related_decisions": list(explanation.related_decisions),
        "related_root_causes": list(explanation.related_root_causes),
        "section_ids": [s.section_id for s in explanation.sections],
        "section_order": [
            {"section_id": s.section_id, "display_order": s.display_order}
            for s in sorted(explanation.sections, key=lambda x: x.display_order)
        ],
        "traceability": explanation.traceability.model_dump(),
    }


def validate_explanation(explanation: ForecastExplanation) -> dict[str, object]:
    """Structural integrity only — never attributes features or generates narratives."""
    issues: list[str] = []
    seen_ids: set[str] = set()
    seen_orders: set[int] = set()
    known_section_ids = {s.section_id for s in explanation.sections}

    if not explanation.sections and not explanation.summary:
        issues.append("Empty explanation")

    try:
        if explanation.explanation_status not in ExplanationStatus:
            issues.append(f"Invalid status: {explanation.explanation_status}")
    except Exception:
        issues.append(f"Invalid status: {explanation.explanation_status}")

    present_types: set[str] = set()
    for section in explanation.sections:
        if not section.section_id:
            issues.append("Section missing section_id")
            continue
        if section.section_id in seen_ids:
            issues.append(f"Duplicate section_id: {section.section_id}")
        seen_ids.add(section.section_id)

        if section.display_order in seen_orders:
            issues.append(f"Duplicate display_order: {section.display_order}")
        seen_orders.add(section.display_order)

        try:
            if section.section_type not in SectionType:
                issues.append(f"Invalid section type: {section.section_id}")
            else:
                present_types.add(section.section_type.value)
        except Exception:
            issues.append(f"Invalid section type: {section.section_id}")

        for ref in section.references:
            # References may point to external IDs or peer sections; only flag empty refs.
            if ref is None or str(ref).strip() == "":
                issues.append(f"Broken reference in section: {section.section_id}")

    missing_required = [
        req for req in REQUIRED_SECTION_TYPES if req not in present_types
    ]
    if explanation.sections and missing_required:
        issues.append(f"Missing required sections: {', '.join(missing_required)}")

    # Traceability section_ids that don't resolve are broken references.
    for sid in explanation.traceability.section_ids:
        if sid and sid not in known_section_ids:
            issues.append(f"Broken reference: traceability.section_ids -> {sid}")

    required_extensions = set(empty_forecast_explainability_future_extensions().keys())
    missing_extensions = sorted(
        required_extensions - set(explanation.metadata.future_extensions.keys())
    )
    if missing_extensions:
        issues.append(f"Missing future_extensions: {', '.join(missing_extensions)}")

    return {
        "valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "explanation_id": explanation.explanation_id,
        "section_count": len(explanation.sections),
        "missing_required_sections": missing_required if explanation.sections else list(REQUIRED_SECTION_TYPES),
    }
