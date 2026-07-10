from __future__ import annotations

from typing import Iterable

from backend.models.ai_insight_models import (
    AI_INSIGHT_SCHEMA_VERSION,
    InsightMetadata,
    InsightPriority,
    RiskLevel,
    UniversalAIInsight,
    UniversalAIInsightCollection,
    ValidationStatus,
    compute_overall_confidence,
    utc_now_iso,
)
from backend.models.validation_models import (
    VALIDATION_ENGINE_VERSION,
    CheckStatus,
    ValidationFinding,
    ValidationReport,
    ValidatorResult,
)


_VALIDATOR_WEIGHT = 100.0 / 6.0
_CONFIDENCE_TOLERANCE = 0.06
_HIGH_RISK_LEVELS = {RiskLevel.high, RiskLevel.critical}
_HIGH_PRIORITIES = {InsightPriority.high, InsightPriority.critical}


def _finding(
    validator: str,
    check_id: str,
    status: CheckStatus,
    message: str,
) -> ValidationFinding:
    return ValidationFinding(validator=validator, check_id=check_id, status=status, message=message)


def _record_pass(result: ValidatorResult, check_id: str, message: str) -> None:
    result.passed_checks.append(check_id)
    result.findings.append(_finding(result.validator, check_id, CheckStatus.passed, message))


def _record_fail(result: ValidatorResult, check_id: str, message: str, penalty: float = 20.0) -> None:
    result.failed_checks.append(check_id)
    result.findings.append(_finding(result.validator, check_id, CheckStatus.failed, message))
    result.score = max(0.0, result.score - penalty)


def _record_warning(result: ValidatorResult, check_id: str, message: str, penalty: float = 8.0) -> None:
    result.warnings.append(message)
    result.findings.append(_finding(result.validator, check_id, CheckStatus.warning, message))
    result.score = max(0.0, result.score - penalty)


def validate_evidence(insight: UniversalAIInsight) -> ValidatorResult:
    result = ValidatorResult(validator="evidence_validator", score=_VALIDATOR_WEIGHT * 6)

    if insight.supporting_evidence:
        _record_pass(result, "evidence_present", "Supporting evidence is present.")
        for index, item in enumerate(insight.supporting_evidence):
            if not item.label.strip():
                _record_fail(result, f"evidence_label_{index}", "Evidence item is missing a label.")
            if item.value in (None, "", []):
                _record_warning(result, f"evidence_value_{index}", f"Evidence '{item.label or index}' has no value.")
            if not item.source.strip():
                _record_warning(result, f"evidence_source_{index}", f"Evidence '{item.label or index}' has no source.")
    elif insight.risk_level in _HIGH_RISK_LEVELS or insight.priority in _HIGH_PRIORITIES:
        _record_fail(result, "evidence_missing", "High-risk or high-priority insight lacks supporting evidence.")
    else:
        _record_warning(result, "evidence_missing", "No supporting evidence provided.")

    known_refs = {item.label for item in insight.supporting_evidence if item.label}
    known_refs.update(insight.related_charts)
    known_refs.update(insight.related_kpis)
    known_refs.update(insight.affected_metrics)

    for action_index, action in enumerate(insight.recommended_actions):
        for ref in action.evidence_refs:
            if ref and ref not in known_refs:
                _record_fail(
                    result,
                    f"evidence_ref_{action_index}",
                    f"Recommended action references unknown evidence ref '{ref}'.",
                )

    return result


def validate_business_logic(insight: UniversalAIInsight) -> ValidatorResult:
    result = ValidatorResult(validator="business_logic_validator", score=_VALIDATOR_WEIGHT * 6)

    if insight.business_impact.strip():
        _record_pass(result, "business_impact_present", "Business impact is documented.")
    elif insight.priority in _HIGH_PRIORITIES:
        _record_fail(result, "business_impact_missing", "High-priority insight lacks business impact.")

    if insight.expected_outcome.strip():
        _record_pass(result, "expected_outcome_present", "Expected outcome is documented.")
    elif insight.recommended_actions:
        _record_warning(result, "expected_outcome_missing", "Recommendations exist without an expected outcome.")

    if not insight.recommended_actions:
        _record_warning(result, "recommendations_missing", "No recommended actions were provided.")
        return result

    for index, action in enumerate(insight.recommended_actions):
        if not action.action.strip():
            _record_fail(result, f"recommendation_action_{index}", "Recommended action text is empty.")
            continue
        _record_pass(result, f"recommendation_action_{index}", "Recommended action text is present.")
        if insight.insight.strip() or insight.reason.strip():
            _record_pass(result, f"recommendation_support_{index}", "Recommendation is supported by narrative context.")
        else:
            _record_fail(result, f"recommendation_support_{index}", "Recommendation lacks supporting insight narrative.")

    if insight.business_impact and insight.expected_outcome:
        _record_pass(result, "impact_outcome_alignment", "Business impact and expected outcome are both documented.")

    return result


def validate_confidence(insight: UniversalAIInsight) -> ValidatorResult:
    result = ValidatorResult(validator="confidence_validator", score=_VALIDATOR_WEIGHT * 6)

    for field_name in ("data_confidence", "reasoning_confidence", "overall_confidence"):
        value = getattr(insight, field_name)
        if 0.0 <= value <= 1.0:
            _record_pass(result, f"{field_name}_range", f"{field_name} is within the valid 0-1 range.")
        else:
            _record_fail(result, f"{field_name}_range", f"{field_name} must be between 0 and 1.")

    expected_overall = compute_overall_confidence(insight.data_confidence, insight.reasoning_confidence)
    if expected_overall == 0.0 and insight.overall_confidence == 0.0:
        _record_pass(result, "overall_confidence_consistent", "Overall confidence is consistently zero.")
    elif abs(insight.overall_confidence - expected_overall) <= _CONFIDENCE_TOLERANCE:
        _record_pass(result, "overall_confidence_consistent", "Overall confidence matches component confidences.")
    else:
        _record_fail(
            result,
            "overall_confidence_consistent",
            f"Overall confidence {insight.overall_confidence} is inconsistent with expected {expected_overall}.",
        )

    if insight.overall_confidence > 0.5 and not insight.confidence_reason.strip():
        _record_fail(result, "confidence_reason_present", "High confidence requires a confidence explanation.")
    elif insight.confidence_reason.strip():
        _record_pass(result, "confidence_reason_present", "Confidence explanation is present.")
    else:
        _record_warning(result, "confidence_reason_present", "Confidence explanation is empty.")

    return result


def validate_data_quality(insight: UniversalAIInsight) -> ValidatorResult:
    result = ValidatorResult(validator="data_quality_validator", score=_VALIDATOR_WEIGHT * 6)
    scorecard = insight.data_quality_score

    if scorecard is None:
        if insight.priority in _HIGH_PRIORITIES:
            _record_warning(result, "data_quality_present", "High-priority insight has no data quality score.")
        else:
            _record_warning(result, "data_quality_present", "Data quality score is not provided.")
        return result

    _record_pass(result, "data_quality_present", "Data quality score is present.")

    if scorecard.score is None:
        _record_warning(result, "data_quality_score_value", "Data quality score value is missing.")
    elif 0.0 <= float(scorecard.score) <= 100.0 or 0.0 <= float(scorecard.score) <= 1.0:
        _record_pass(result, "data_quality_score_value", "Data quality score value is within a valid range.")
        if float(scorecard.score) < 60.0 and insight.priority in _HIGH_PRIORITIES:
            _record_warning(result, "data_quality_low", "Data quality score is low for a high-priority insight.")
    else:
        _record_fail(result, "data_quality_score_value", "Data quality score value is out of range.")

    if scorecard.completeness_pct is None:
        _record_warning(result, "completeness_present", "Completeness percentage is missing.")
    elif 0.0 <= float(scorecard.completeness_pct) <= 100.0:
        _record_pass(result, "completeness_present", "Completeness percentage is valid.")
    else:
        _record_fail(result, "completeness_present", "Completeness percentage is out of range.")

    if scorecard.dimensions:
        _record_pass(result, "dimensions_populated", "Data quality dimensions are populated.")
    else:
        _record_warning(result, "dimensions_populated", "Data quality dimensions are empty.")

    return result


def validate_schema(insight: UniversalAIInsight) -> ValidatorResult:
    result = ValidatorResult(validator="schema_validator", score=_VALIDATOR_WEIGHT * 6)

    required_fields = {
        "id": insight.id,
        "title": insight.title,
        "summary": insight.summary,
        "insight": insight.insight,
        "generated_at": insight.generated_at,
        "generated_by.engine": insight.generated_by.engine,
    }
    for field_name, value in required_fields.items():
        if str(value or "").strip():
            _record_pass(result, f"required_{field_name}", f"Required field '{field_name}' is present.")
        else:
            _record_fail(result, f"required_{field_name}", f"Required field '{field_name}' is missing.")

    if insight.schema_version == AI_INSIGHT_SCHEMA_VERSION:
        _record_pass(result, "schema_version", "Schema version matches the canonical contract.")
    else:
        _record_fail(result, "schema_version", f"Unsupported schema version '{insight.schema_version}'.")

    if insight.id.strip():
        _record_pass(result, "identifier_format", "Insight identifier is present.")
    else:
        _record_fail(result, "identifier_format", "Insight identifier is empty.")

    for enum_name, enum_value in (
        ("risk_level", insight.risk_level.value),
        ("priority", insight.priority.value),
        ("validation_status", insight.validation_status.value),
    ):
        if enum_value:
            _record_pass(result, f"enum_{enum_name}", f"Enum field '{enum_name}' is populated.")
        else:
            _record_fail(result, f"enum_{enum_name}", f"Enum field '{enum_name}' is invalid.")

    return result


def validate_governance(insight: UniversalAIInsight) -> ValidatorResult:
    result = ValidatorResult(validator="governance_validator", score=_VALIDATOR_WEIGHT * 6)

    if insight.assumptions:
        _record_pass(result, "assumptions_documented", "Assumptions are documented.")
    elif insight.risk_level in _HIGH_RISK_LEVELS:
        _record_fail(result, "assumptions_documented", "High-risk insight lacks documented assumptions.")
    else:
        _record_warning(result, "assumptions_documented", "Assumptions are not documented.")

    if insight.limitations:
        _record_pass(result, "limitations_documented", "Limitations are documented.")
    elif insight.validation_status == ValidationStatus.insufficient or insight.risk_level in _HIGH_RISK_LEVELS:
        _record_fail(result, "limitations_documented", "Insight lacks documented limitations for its risk profile.")
    else:
        _record_warning(result, "limitations_documented", "Limitations are not documented.")

    return result


def _aggregate_results(results: Iterable[ValidatorResult]) -> ValidationReport:
    result_list = list(results)
    passed_checks: list[str] = []
    failed_checks: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []
    findings: list[ValidationFinding] = []

    total_score = 0.0
    for item in result_list:
        passed_checks.extend(item.passed_checks)
        failed_checks.extend(item.failed_checks)
        warnings.extend(item.warnings)
        recommendations.extend(item.recommendations)
        findings.extend(item.findings)
        total_score += item.score

    normalized_score = round(min(100.0, total_score / max(len(result_list), 1) * (6.0 / _VALIDATOR_WEIGHT) / 6.0), 2)
    # total_score is sum of per-validator scores each capped at 100/6*6 = 100 when perfect... 
    # Actually each validator starts at 100 and we subtract penalties. Let me recalculate.

    # Simpler: average validator scores
    normalized_score = round(sum(item.score for item in result_list) / max(len(result_list), 1), 2)

    if failed_checks:
        if any("schema" in check or "required_" in check for check in failed_checks):
            overall_status = ValidationStatus.rejected
        elif normalized_score < 50:
            overall_status = ValidationStatus.rejected
        else:
            overall_status = ValidationStatus.insufficient
    elif normalized_score < 70:
        overall_status = ValidationStatus.insufficient
    else:
        overall_status = ValidationStatus.validated

    return ValidationReport(
        overall_status=overall_status,
        score=normalized_score,
        passed_checks=passed_checks,
        failed_checks=failed_checks,
        warnings=warnings,
        recommendations=recommendations,
        findings=findings,
        validator_version=VALIDATION_ENGINE_VERSION,
        validated_at=utc_now_iso(),
    )


def _apply_confidence_adjustments(insight: UniversalAIInsight, report: ValidationReport) -> UniversalAIInsight:
    if "overall_confidence_consistent" in report.failed_checks:
        expected = compute_overall_confidence(insight.data_confidence, insight.reasoning_confidence)
        if expected > 0:
            insight.overall_confidence = expected
    if "confidence_reason_present" in report.failed_checks and insight.overall_confidence > 0.5:
        insight.overall_confidence = min(insight.overall_confidence, 0.5)
    return insight


def _apply_validation_metadata(insight: UniversalAIInsight, report: ValidationReport) -> UniversalAIInsight:
    metadata = insight.metadata.model_copy(deep=True)
    metadata.future_extensions = {
        **metadata.future_extensions,
        "validation_engine": report.model_dump(),
    }
    metadata.debug = {
        **metadata.debug,
        "validation_findings": [finding.model_dump() for finding in report.findings],
    }
    insight.metadata = metadata
    insight.validation_status = report.overall_status
    return insight


def validate_insight(insight: UniversalAIInsight) -> tuple[UniversalAIInsight, ValidationReport]:
    """Validate a single insight and return a new validated copy plus report."""
    validated = insight.model_copy(deep=True)
    report = _aggregate_results(
        [
            validate_evidence(validated),
            validate_business_logic(validated),
            validate_confidence(validated),
            validate_data_quality(validated),
            validate_schema(validated),
            validate_governance(validated),
        ]
    )
    validated = _apply_confidence_adjustments(validated, report)
    validated = _apply_validation_metadata(validated, report)
    return validated, report


def validate_collection(
    collection: UniversalAIInsightCollection,
) -> tuple[UniversalAIInsightCollection, ValidationReport]:
    """Validate each insight in a collection and return a new collection plus aggregate report."""
    validated_insights: list[UniversalAIInsight] = []
    reports: list[ValidationReport] = []

    for insight in collection.insights:
        validated_insight, report = validate_insight(insight)
        validated_insights.append(validated_insight)
        reports.append(report)

    if not reports:
        empty_report = ValidationReport(
            overall_status=ValidationStatus.insufficient,
            score=0.0,
            warnings=["Collection contains no insights."],
            validator_version=VALIDATION_ENGINE_VERSION,
            validated_at=utc_now_iso(),
        )
        return collection.model_copy(deep=True), empty_report

    aggregate = ValidationReport(
        overall_status=ValidationStatus.validated,
        score=round(sum(item.score for item in reports) / len(reports), 2),
        passed_checks=[check for item in reports for check in item.passed_checks],
        failed_checks=[check for item in reports for check in item.failed_checks],
        warnings=[warning for item in reports for warning in item.warnings],
        recommendations=[rec for item in reports for rec in item.recommendations],
        findings=[finding for item in reports for finding in item.findings],
        validator_version=VALIDATION_ENGINE_VERSION,
        validated_at=utc_now_iso(),
    )

    if any(item.overall_status == ValidationStatus.rejected for item in reports):
        aggregate.overall_status = ValidationStatus.rejected
    elif any(item.overall_status == ValidationStatus.insufficient for item in reports):
        aggregate.overall_status = ValidationStatus.insufficient

    validated_collection = collection.model_copy(deep=True)
    validated_collection.insights = validated_insights
    metadata = validated_collection.metadata.model_copy(deep=True)
    metadata.future_extensions = {
        **metadata.future_extensions,
        "validation_engine": aggregate.model_dump(),
    }
    validated_collection.metadata = metadata
    return validated_collection, aggregate
