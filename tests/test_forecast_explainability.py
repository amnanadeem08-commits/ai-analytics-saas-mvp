from __future__ import annotations

from backend.models.forecast_explainability_models import (
    DEFAULT_EXPLANATION_SECTION_SPECS,
    FORECAST_EXPLAINABILITY_FUTURE_EXTENSION_KEYS,
    ExplanationSection,
    ExplanationStatus,
    SectionType,
)
from backend.services.forecast_explainability_service import (
    build_default_explanation,
    build_explanation,
    explanation_statistics,
    explanation_summary,
    find_section,
    list_sections,
    traceability_map,
    validate_explanation,
)


def test_explanation_creation_and_default():
    explanation = build_explanation(
        prediction_id="pred_1",
        dataset_id="ds_1",
        scenario_id="baseline",
        adapter_id="adapter_1",
        summary="Template overview for future engines.",
        forecast_horizon="30d",
        confidence_level="medium",
        key_drivers=["driver_a", "driver_b"],
        assumptions=["Assumption one."],
        limitations=["No model attribution."],
        supporting_evidence=["evidence_1"],
        related_predictions=["pred_0"],
        related_decisions=["dec_1"],
        related_root_causes=["rca_1"],
    )
    assert explanation.prediction_id == "pred_1"
    assert explanation.scenario_id == "baseline"
    assert len(explanation.sections) == len(DEFAULT_EXPLANATION_SECTION_SPECS)
    assert validate_explanation(explanation)["valid"] is True

    default = build_default_explanation(prediction_id="pred_2", dataset_id="ds_2")
    assert default.explanation_status == ExplanationStatus.planned
    assert len(default.sections) == 9
    names = [s.section_name for s in list_sections(default)]
    assert names == [
        "Overview",
        "Forecast Horizon",
        "Confidence",
        "Key Drivers",
        "Supporting Evidence",
        "Assumptions",
        "Limitations",
        "Traceability",
        "References",
    ]


def test_section_lookup_ordering_and_traceability():
    explanation = build_explanation(
        prediction_id="pred_1",
        dataset_id="ds_1",
        scenario_id="expected",
        adapter_id="adapter_x",
        summary="Overview text",
        forecast_horizon="7d",
        confidence_level="high",
        key_drivers=["k1"],
        assumptions=["a1"],
        limitations=["l1"],
        supporting_evidence=["e1"],
        related_predictions=["p0"],
        related_decisions=["d0"],
        related_root_causes=["r0"],
    )
    found = find_section(explanation, "sec_key_drivers")
    assert found is not None
    assert found.section_type == SectionType.drivers
    assert found.display_order == 4

    ordered = list_sections(explanation)
    orders = [s.display_order for s in ordered]
    assert orders == sorted(orders)

    drivers = list_sections(explanation, section_type=SectionType.drivers)
    assert len(drivers) == 1
    assert drivers[0].section_id == "sec_key_drivers"

    tmap = traceability_map(explanation)
    assert tmap["prediction_id"] == "pred_1"
    assert tmap["dataset_id"] == "ds_1"
    assert tmap["scenario_id"] == "expected"
    assert tmap["adapter_id"] == "adapter_x"
    assert "p0" in tmap["related_predictions"]
    assert "d0" in tmap["related_decisions"]
    assert "r0" in tmap["related_root_causes"]
    assert len(tmap["section_order"]) == 9


def test_statistics_and_summary():
    explanation = build_explanation(
        summary="Overview",
        forecast_horizon="14d",
        confidence_level="low",
        key_drivers=["d1", "d2"],
        assumptions=["a1"],
        limitations=["l1", "l2"],
        supporting_evidence=["e1"],
    )
    stats = explanation_statistics(explanation)
    assert stats.total_sections == 9
    assert stats.driver_count == 2
    assert stats.assumption_count == 1
    assert stats.limitation_count == 2
    assert stats.completed_sections >= 1
    assert stats.reference_count >= 1

    summary = explanation_summary(explanation)
    assert summary.forecast_horizon == "14d"
    assert summary.confidence_level == "low"
    assert summary.section_count == 9
    assert summary.driver_count == 2
    assert summary.overall_completeness in {"partial", "complete"}


def test_validation():
    good = build_explanation(
        summary="Ok",
        forecast_horizon="1d",
        confidence_level="medium",
        key_drivers=["k"],
        assumptions=["a"],
        limitations=["l"],
        supporting_evidence=["e"],
    )
    assert validate_explanation(good)["valid"] is True

    empty = build_explanation(include_default_sections=False)
    result = validate_explanation(empty)
    assert result["valid"] is False
    assert any("Empty explanation" in i for i in result["issues"])

    dup = good.model_copy(deep=True)
    dup.sections = list(dup.sections) + [dup.sections[0].model_copy(deep=True)]
    issues = validate_explanation(dup)["issues"]
    assert any("Duplicate section_id" in i for i in issues)

    order_dup = good.model_copy(deep=True)
    order_dup.sections[1].display_order = order_dup.sections[0].display_order
    assert any(
        "Duplicate display_order" in i
        for i in validate_explanation(order_dup)["issues"]
    )

    missing = build_explanation(
        sections=[
            ExplanationSection(
                section_id="only_overview",
                section_name="Overview",
                section_type=SectionType.overview,
                display_order=1,
                content="x",
            )
        ],
        include_default_sections=False,
        summary="x",
    )
    missing_issues = validate_explanation(missing)["issues"]
    assert any("Missing required sections" in i for i in missing_issues)

    broken = good.model_copy(deep=True)
    broken.traceability.section_ids = list(broken.traceability.section_ids) + ["missing_sec"]
    assert any(
        "Broken reference" in i for i in validate_explanation(broken)["issues"]
    )


def test_future_extension_buckets():
    explanation = build_default_explanation()
    for key in FORECAST_EXPLAINABILITY_FUTURE_EXTENSION_KEYS:
        assert key in explanation.metadata.future_extensions
        assert explanation.metadata.future_extensions[key] == {}
    assert "shap" in explanation.metadata.future_extensions
    assert "lime" in explanation.metadata.future_extensions
    assert "llm_explanations" in explanation.metadata.future_extensions


def test_immutability():
    explanation = build_explanation(
        summary="Immutable base",
        forecast_horizon="30d",
        confidence_level="medium",
        key_drivers=["k1"],
        assumptions=["a1"],
        limitations=["l1"],
        supporting_evidence=["e1"],
        related_predictions=["p1"],
    )
    snapshot = explanation.model_dump()
    found = find_section(explanation, "sec_overview")
    assert found is not None
    found.content = "mutated"
    listed = list_sections(explanation)
    listed[0].content = "mutated_list"
    explanation_statistics(explanation)
    explanation_summary(explanation)
    validate_explanation(explanation)
    tmap = traceability_map(explanation)
    tmap["prediction_id"] = "mutated"
    assert explanation.model_dump() == snapshot
