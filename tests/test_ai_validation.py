from __future__ import annotations

import pandas as pd

from backend.models.ai_insight_models import (
    AI_INSIGHT_SCHEMA_VERSION,
    DataQualityScore,
    InsightMetadata,
    InsightPriority,
    InsightProvenance,
    RecommendedAction,
    RiskLevel,
    SupportingEvidenceItem,
    UniversalAIInsight,
    UniversalAIInsightCollection,
    ValidationStatus,
    utc_now_iso,
)
from backend.models.validation_models import VALIDATION_ENGINE_VERSION
from backend.services.ai_insight_mapper_service import from_rule_based_insight
from backend.services.ai_validation_service import (
    validate_business_logic,
    validate_collection,
    validate_confidence,
    validate_data_quality,
    validate_evidence,
    validate_governance,
    validate_insight,
    validate_schema,
)


def _valid_insight(**overrides) -> UniversalAIInsight:
    base = UniversalAIInsight(
        id="insight_valid",
        schema_version=AI_INSIGHT_SCHEMA_VERSION,
        title="Revenue trend is stable",
        summary="Revenue remained stable across segments.",
        insight="Revenue remained stable across segments.",
        reason="Segment totals show limited variance.",
        supporting_evidence=[
            SupportingEvidenceItem(
                label="Segment variance",
                value="Low",
                evidence_type="analysis",
                source="rule_based_engine",
                confidence_score=0.82,
            )
        ],
        affected_metrics=["revenue"],
        business_impact="Limited downside risk in the near term.",
        expected_outcome="Leadership can monitor rather than intervene immediately.",
        risk_level=RiskLevel.low,
        priority=InsightPriority.medium,
        recommended_actions=[
            RecommendedAction(
                action="Monitor weekly revenue by segment.",
                rationale="Variance remains low.",
                expected_impact="Early detection of change.",
                expected_outcome="Faster response if trend shifts.",
            )
        ],
        data_confidence=0.82,
        reasoning_confidence=0.78,
        overall_confidence=0.8,
        confidence_reason="Backed by validated segment evidence.",
        assumptions=["Revenue field is complete for the reviewed period."],
        limitations=["Does not include forward-looking forecast claims."],
        related_kpis=["total_revenue"],
        domain="Sales",
        generated_by=InsightProvenance(engine="rule_based_engine", provider="platform", engine_version="1.0.0"),
        generated_at=utc_now_iso(),
        validation_status=ValidationStatus.pending,
        data_quality_score=DataQualityScore(score=88.0, grade="B", completeness_pct=96.0, dimensions={"freshness": "good"}),
        metadata=InsightMetadata(),
    )
    return base.model_copy(update=overrides)


def test_valid_insight_passes_validation():
    original = _valid_insight()
    validated, report = validate_insight(original)

    assert original.validation_status == ValidationStatus.pending
    assert validated.validation_status == ValidationStatus.validated
    assert validated is not original
    assert report.overall_status == ValidationStatus.validated
    assert report.score >= 70
    assert report.validator_version == VALIDATION_ENGINE_VERSION
    assert validated.metadata.future_extensions["validation_engine"]["overall_status"] == "validated"


def test_invalid_insight_is_rejected_for_schema_failure():
    original = _valid_insight(id="", schema_version="0.0.1")
    validated, report = validate_insight(original)

    assert report.overall_status == ValidationStatus.rejected
    assert validated.validation_status == ValidationStatus.rejected
    assert "required_id" in report.failed_checks
    assert "schema_version" in report.failed_checks


def test_missing_evidence_fails_high_risk_insight():
    original = _valid_insight(
        supporting_evidence=[],
        risk_level=RiskLevel.high,
        priority=InsightPriority.high,
    )
    _, report = validate_insight(original)

    assert "evidence_missing" in report.failed_checks


def test_missing_recommendation_text_fails_business_logic_validator():
    insight = _valid_insight(
        recommended_actions=[RecommendedAction(action="   ", rationale="Missing action text")]
    )
    result = validate_business_logic(insight)

    assert "recommendation_action_0" in result.failed_checks


def test_invalid_confidence_is_detected():
    insight = _valid_insight(data_confidence=0.8, reasoning_confidence=0.7, overall_confidence=0.2)
    result = validate_confidence(insight)

    assert "overall_confidence_consistent" in result.failed_checks


def test_confidence_adjustment_applied_on_validated_copy():
    original = _valid_insight(data_confidence=0.8, reasoning_confidence=0.6, overall_confidence=0.2)
    validated, report = validate_insight(original)

    assert "overall_confidence_consistent" in report.failed_checks
    assert validated.overall_confidence == 0.7
    assert original.overall_confidence == 0.2


def test_missing_confidence_reason_caps_high_confidence():
    original = _valid_insight(confidence_reason="", overall_confidence=0.9)
    validated, report = validate_insight(original)

    assert "confidence_reason_present" in report.failed_checks
    assert validated.overall_confidence <= 0.5
    assert original.overall_confidence == 0.9


def test_low_data_quality_warns_for_high_priority_insight():
    insight = _valid_insight(
        priority=InsightPriority.high,
        data_quality_score=DataQualityScore(score=45.0, grade="D", completeness_pct=55.0),
    )
    result = validate_data_quality(insight)

    assert "data_quality_low" in [finding.check_id for finding in result.findings if finding.status.value == "warning"]


def test_governance_validator_requires_assumptions_for_high_risk():
    insight = _valid_insight(assumptions=[], limitations=[], risk_level=RiskLevel.critical)
    result = validate_governance(insight)

    assert "assumptions_documented" in result.failed_checks
    assert "limitations_documented" in result.failed_checks


def test_evidence_validator_flags_unknown_refs():
    insight = _valid_insight(
        recommended_actions=[
            RecommendedAction(
                action="Review segment playbook.",
                evidence_refs=["missing_evidence_ref"],
            )
        ]
    )
    result = validate_evidence(insight)

    assert any(check.startswith("evidence_ref_") for check in result.failed_checks)


def test_schema_validator_checks_required_fields():
    insight = _valid_insight(title="", summary="", insight="")
    result = validate_schema(insight)

    assert "required_title" in result.failed_checks
    assert "required_summary" in result.failed_checks
    assert "required_insight" in result.failed_checks


def test_validate_collection_returns_new_collection_and_aggregate_report():
    insights = [
        _valid_insight(id="one"),
        from_rule_based_insight(
            {
                "type": "overview",
                "title": "Dataset overview",
                "message": "Rows analyzed.",
                "severity": "info",
                "metadata": {},
            }
        ),
    ]
    collection = UniversalAIInsightCollection(dataset_id="demo", domain="Sales", insights=insights)
    validated_collection, report = validate_collection(collection)

    assert validated_collection is not collection
    assert len(validated_collection.insights) == 2
    assert report.validator_version == VALIDATION_ENGINE_VERSION
    assert "validation_engine" in validated_collection.metadata.future_extensions


def test_validate_collection_empty_insights():
    collection = UniversalAIInsightCollection(dataset_id="demo", insights=[])
    validated_collection, report = validate_collection(collection)

    assert validated_collection.insights == []
    assert report.overall_status == ValidationStatus.insufficient
    assert "Collection contains no insights." in report.warnings


def test_original_insight_not_mutated():
    original = _valid_insight()
    original_status = original.validation_status
    original_metadata = original.metadata.model_dump()

    validate_insight(original)

    assert original.validation_status == original_status
    assert original.metadata.model_dump() == original_metadata


def test_mapper_produced_insight_can_be_validated():
    df = pd.DataFrame({"revenue": [10, 20, 30], "segment": ["A", "B", "A"]})
    from backend.ai.rule_based_engine import generate_rule_based_insights

    mapped = from_rule_based_insight(generate_rule_based_insights(df)[0], domain="Sales")
    validated, report = validate_insight(mapped)

    assert validated.validation_status in {
        ValidationStatus.validated,
        ValidationStatus.insufficient,
        ValidationStatus.rejected,
    }
    assert report.passed_checks or report.failed_checks or report.warnings
