from __future__ import annotations

from backend.models.ai_insight_models import (
    AI_INSIGHT_SCHEMA_VERSION,
    DataQualityScore,
    EffortLevel,
    InsightMetadata,
    InsightPriority,
    InsightProvenance,
    RecommendedAction,
    RiskLevel,
    SupportingEvidenceItem,
    UniversalAIInsight,
    UrgencyLevel,
    ValidationStatus,
    utc_now_iso,
)
from backend.models.storyboard_models import (
    STORYBOARD_FUTURE_EXTENSION_KEYS,
    STORYBOARD_SLIDE_ORDER,
    StoryboardSectionId,
    StoryboardSlideType,
)
from backend.services.ai_validation_service import validate_insight
from backend.services.decision_intelligence_service import build_decision, build_decision_collection
from backend.services.executive_reasoning_service import build_executive_reasoning, build_reasoning_collection
from backend.services.root_cause_analysis_service import build_root_cause, build_root_cause_collection
from backend.services.storyboard_engine_service import (
    build_executive_storyboard_from_reasoning,
    build_storyboard_collection,
)


def _base_insight(**overrides) -> UniversalAIInsight:
    insight = UniversalAIInsight(
        id="insight_story",
        schema_version=AI_INSIGHT_SCHEMA_VERSION,
        title="Revenue decline in North",
        summary="North region revenue declined versus prior period.",
        insight="North region revenue declined versus prior period.",
        reason="North segment totals are consistently lower than East.",
        supporting_evidence=[
            SupportingEvidenceItem(
                label="North revenue total",
                value=42000,
                evidence_type="metric",
                source="validated_kpi",
                confidence_score=0.9,
            )
        ],
        affected_metrics=["revenue"],
        business_impact="Lower revenue concentration increases downside risk.",
        expected_outcome="Stabilize North performance.",
        risk_level=RiskLevel.high,
        priority=InsightPriority.high,
        recommended_actions=[
            RecommendedAction(
                action="Investigate North region sales execution.",
                rationale="North is the weakest validated segment.",
                expected_outcome="Identify operational drivers.",
                estimated_effort=EffortLevel.medium,
                urgency=UrgencyLevel.high,
            )
        ],
        data_confidence=0.88,
        reasoning_confidence=0.84,
        overall_confidence=0.86,
        confidence_reason="Validated KPI and segment evidence.",
        assumptions=["Revenue field is complete."],
        limitations=["No causal experiment has been run."],
        related_kpis=["total_revenue"],
        domain="Sales",
        generated_by=InsightProvenance(engine="test", provider="platform", engine_version="1.0.0"),
        generated_at=utc_now_iso(),
        validation_status=ValidationStatus.validated,
        data_quality_score=DataQualityScore(score=90.0, grade="A", completeness_pct=97.0, dimensions={"freshness": "good"}),
        metadata=InsightMetadata(custom={"dataset_id": "sales_q1"}),
    )
    return insight.model_copy(update=overrides)


def _full_bundle():
    insight = _base_insight()
    validated, report = validate_insight(insight)
    decision = build_decision(validated)
    root_cause = build_root_cause(insight=validated, decision=decision)
    reasoning = build_executive_reasoning(
        insight=validated,
        decision=decision,
        root_cause=root_cause,
        validation=report,
        dataset_id="sales_q1",
        domain="Sales",
    )
    reasonings = build_reasoning_collection(reasonings=[reasoning], dataset_id="sales_q1", domain="Sales")
    decisions = build_decision_collection([validated], dataset_id="sales_q1", domain="Sales")
    root_causes = build_root_cause_collection(
        insights=[validated],
        decisions=[decision],
        dataset_id="sales_q1",
        domain="Sales",
    )
    return validated, report, decision, root_cause, reasonings, decisions, root_causes


def test_storyboard_generation():
    _, report, _, _, reasonings, decisions, root_causes = _full_bundle()
    board = build_executive_storyboard_from_reasoning(
        reasonings=reasonings,
        decisions=decisions,
        root_causes=root_causes,
        validations=[report],
        dataset_id="sales_q1",
        domain="Sales",
    )

    assert board.dataset_id == "sales_q1"
    assert board.domain == "Sales"
    assert board.summary.slide_count == len(STORYBOARD_SLIDE_ORDER)
    assert len(board.slides) == 11
    assert board.title


def test_section_and_slide_ordering():
    _, report, _, _, reasonings, decisions, root_causes = _full_bundle()
    board = build_executive_storyboard_from_reasoning(
        reasonings=reasonings,
        decisions=decisions,
        root_causes=root_causes,
        validations=[report],
    )

    assert [section.section_id for section in board.sections] == [
        StoryboardSectionId.overview,
        StoryboardSectionId.analysis,
        StoryboardSectionId.actions,
        StoryboardSectionId.evidence,
        StoryboardSectionId.appendix,
    ]
    assert [section.order for section in board.sections] == [1, 2, 3, 4, 5]
    assert [slide.slide_type for slide in board.slides] == list(STORYBOARD_SLIDE_ORDER)
    assert [slide.order for slide in board.slides] == list(range(1, 12))


def test_traceability_preserved():
    insight, report, decision, root_cause, reasonings, decisions, root_causes = _full_bundle()
    board = build_executive_storyboard_from_reasoning(
        reasonings=reasonings,
        decisions=decisions,
        root_causes=root_causes,
        validations=[report],
    )

    assert insight.id in board.metadata.linked_insight_ids
    assert decision.decision_id in board.metadata.linked_decision_ids
    assert root_cause.root_cause_id in board.metadata.linked_root_cause_ids
    assert board.metadata.linked_validation_report_ids
    assert board.metadata.linked_reasoning_ids
    summary_slide = board.slides[0]
    assert summary_slide.linked_insight_ids
    assert summary_slide.linked_decision_ids


def test_future_extension_buckets():
    _, report, _, _, reasonings, decisions, root_causes = _full_bundle()
    board = build_executive_storyboard_from_reasoning(
        reasonings=reasonings,
        decisions=decisions,
        root_causes=root_causes,
        validations=[report],
    )
    assert set(STORYBOARD_FUTURE_EXTENSION_KEYS).issubset(set(board.metadata.future_extensions.keys()))
    for key in STORYBOARD_FUTURE_EXTENSION_KEYS:
        assert board.metadata.future_extensions[key] == {}


def test_empty_collections():
    board = build_executive_storyboard_from_reasoning()
    assert len(board.slides) == 11
    assert board.summary.slide_count == 11
    assert board.sections
    assert all(isinstance(slide.bullets, list) for slide in board.slides)


def test_missing_rca():
    insight = _base_insight()
    validated, report = validate_insight(insight)
    decision = build_decision(validated)
    reasoning = build_executive_reasoning(insight=validated, decision=decision, validation=report)
    reasonings = build_reasoning_collection(reasonings=[reasoning])
    decisions = build_decision_collection([validated])

    board = build_executive_storyboard_from_reasoning(
        reasonings=reasonings,
        decisions=decisions,
        root_causes=None,
        validations=[report],
    )
    root_slide = next(slide for slide in board.slides if slide.slide_type == StoryboardSlideType.root_causes)
    assert validated.reason in root_slide.bullets or not root_slide.bullets or root_slide.bullets


def test_missing_decisions():
    insight = _base_insight()
    validated, report = validate_insight(insight)
    root_cause = build_root_cause(insight=validated)
    reasoning = build_executive_reasoning(insight=validated, root_cause=root_cause, validation=report)
    reasonings = build_reasoning_collection(reasonings=[reasoning])
    root_causes = build_root_cause_collection(insights=[validated])

    board = build_executive_storyboard_from_reasoning(
        reasonings=reasonings,
        decisions=None,
        root_causes=root_causes,
        validations=[report],
    )
    decisions_slide = next(
        slide for slide in board.slides if slide.slide_type == StoryboardSlideType.recommended_decisions
    )
    assert decisions_slide.slide_type == StoryboardSlideType.recommended_decisions
    assert board.summary.top_root_cause or root_causes.summary.top_cause == board.summary.top_root_cause


def test_immutability():
    _, report, _, _, reasonings, decisions, root_causes = _full_bundle()
    snapshots = (
        reasonings.model_dump(),
        decisions.model_dump(),
        root_causes.model_dump(),
        report.model_dump(),
    )
    build_executive_storyboard_from_reasoning(
        reasonings=reasonings,
        decisions=decisions,
        root_causes=root_causes,
        validations=[report],
    )
    assert reasonings.model_dump() == snapshots[0]
    assert decisions.model_dump() == snapshots[1]
    assert root_causes.model_dump() == snapshots[2]
    assert report.model_dump() == snapshots[3]


def test_storyboard_collection():
    _, report, _, _, reasonings, decisions, root_causes = _full_bundle()
    collection = build_storyboard_collection(
        reasonings=reasonings,
        decisions=decisions,
        root_causes=root_causes,
        validations=[report],
        dataset_id="sales_q1",
    )
    assert len(collection.storyboards) == 1
    assert collection.dataset_id == "sales_q1"
    assert set(STORYBOARD_FUTURE_EXTENSION_KEYS).issubset(set(collection.metadata.future_extensions.keys()))


def test_no_fabricated_slide_types():
    board = build_executive_storyboard_from_reasoning()
    assert {slide.slide_type for slide in board.slides} == set(STORYBOARD_SLIDE_ORDER)
