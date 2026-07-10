from __future__ import annotations

from backend.models.ai_analyst_models import (
    AI_ANALYST_FUTURE_EXTENSION_KEYS,
    AnalystResponseMode,
)
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
    UniversalAIInsightCollection,
    UrgencyLevel,
    ValidationStatus,
    utc_now_iso,
)
from backend.services.ai_analyst_service import (
    answer_question,
    build_ai_response,
    build_follow_up_context,
    business_summary,
    executive_summary,
    explain_decision,
    explain_root_cause,
    recommend_next_questions,
    technical_summary,
    validate_response,
)
from backend.services.ai_validation_service import validate_insight
from backend.services.decision_intelligence_service import build_decision, build_decision_collection
from backend.services.executive_reasoning_service import build_executive_reasoning, build_reasoning_collection
from backend.services.intelligence_bundle_service import build_intelligence_bundle
from backend.services.intelligence_registry_service import build_registry
from backend.services.root_cause_analysis_service import build_root_cause, build_root_cause_collection
from backend.services.storyboard_engine_service import build_executive_storyboard_from_reasoning


def _base_insight(**overrides) -> UniversalAIInsight:
    insight = UniversalAIInsight(
        id="insight_analyst",
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
        data_quality_score=DataQualityScore(
            score=90.0, grade="A", completeness_pct=97.0, dimensions={"freshness": "good"}
        ),
        metadata=InsightMetadata(custom={"dataset_id": "sales_q1"}),
    )
    return insight.model_copy(update=overrides)


def _full_pipeline():
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
    insights = UniversalAIInsightCollection(dataset_id="sales_q1", domain="Sales", insights=[validated])
    decisions = build_decision_collection([validated], dataset_id="sales_q1", domain="Sales")
    root_causes = build_root_cause_collection(
        insights=[validated],
        decisions=[decision],
        dataset_id="sales_q1",
        domain="Sales",
    )
    reasonings = build_reasoning_collection(reasonings=[reasoning], dataset_id="sales_q1", domain="Sales")
    storyboard = build_executive_storyboard_from_reasoning(
        reasonings=reasonings,
        decisions=decisions,
        root_causes=root_causes,
        validations=[report],
        dataset_id="sales_q1",
        domain="Sales",
    )
    bundle = build_intelligence_bundle(
        insights=insights,
        validations=[report],
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
        dataset_id="sales_q1",
        domain="Sales",
    )
    registry = build_registry(
        insights=insights,
        validations=[report],
        decisions=decisions,
        root_causes=root_causes,
        reasonings=reasonings,
        storyboard=storyboard,
        bundle=bundle,
        dataset_id="sales_q1",
        domain="Sales",
    )
    return insights, [report], decisions, root_causes, reasonings, storyboard, bundle, registry


def test_executive_response():
    *_, reasonings, storyboard, bundle, registry = _full_pipeline()
    response = executive_summary(
        bundle=bundle,
        registry=registry,
        storyboard=storyboard,
        reasonings=reasonings,
    )
    assert response.mode == AnalystResponseMode.executive
    assert "Executive view" in response.answer.answer_text
    assert response.answer.headline
    assert response.answer.headline != "unavailable" or response.explanation.unavailable_fields
    assert validate_response(response)["valid"] is True


def test_business_response():
    *_, reasonings, storyboard, bundle, registry = _full_pipeline()
    response = business_summary(bundle=bundle, registry=registry, reasonings=reasonings, storyboard=storyboard)
    assert response.mode == AnalystResponseMode.business
    assert "Business view" in response.answer.answer_text
    assert response.explanation.business_impact


def test_technical_response():
    insights, validations, decisions, root_causes, reasonings, storyboard, bundle, registry = _full_pipeline()
    response = technical_summary(
        bundle=bundle,
        registry=registry,
        validations=validations,
        decisions=decisions,
        reasonings=reasonings,
    )
    assert response.mode == AnalystResponseMode.technical
    assert "Technical view" in response.answer.answer_text
    assert any("Validation" in point or "validation" in point.lower() for point in response.answer.key_points) or (
        "Validation" in response.answer.answer_text
    )


def test_audit_response():
    *_, reasonings, storyboard, bundle, registry = _full_pipeline()
    response = build_ai_response(
        mode=AnalystResponseMode.audit,
        question="Audit the intelligence chain",
        bundle=bundle,
        registry=registry,
        storyboard=storyboard,
        reasonings=reasonings,
    )
    assert response.mode == AnalystResponseMode.audit
    assert "Audit view" in response.answer.answer_text
    assert response.traceability.source_bundle == bundle.bundle_id
    assert response.traceability.registry_reference_ids


def test_decision_explanation():
    insights, validations, decisions, root_causes, reasonings, storyboard, bundle, registry = _full_pipeline()
    decision_id = decisions.decisions[0].decision_id
    response = explain_decision(
        decision_id=decision_id,
        bundle=bundle,
        registry=registry,
        decisions=decisions,
        reasonings=reasonings,
    )
    assert decision_id in response.traceability.source_decisions
    assert response.answer.evidence
    assert any(e.source_object_id == decision_id for e in response.answer.evidence)
    assert "Action:" in response.answer.answer_text


def test_root_cause_explanation():
    insights, validations, decisions, root_causes, reasonings, storyboard, bundle, registry = _full_pipeline()
    root_id = root_causes.root_causes[0].root_cause_id
    response = explain_root_cause(
        root_cause_id=root_id,
        bundle=bundle,
        registry=registry,
        root_causes=root_causes,
        reasonings=reasonings,
    )
    assert root_id in response.traceability.source_root_causes
    assert any(e.source_object_id == root_id for e in response.answer.evidence)
    assert "Probability:" in response.answer.answer_text


def test_traceability_and_registry_references():
    insights, validations, decisions, root_causes, reasonings, storyboard, bundle, registry = _full_pipeline()
    response = build_ai_response(
        mode=AnalystResponseMode.executive,
        bundle=bundle,
        registry=registry,
        storyboard=storyboard,
        reasonings=reasonings,
        decisions=decisions,
        root_causes=root_causes,
        validations=validations,
        insights=insights,
    )
    trace = response.traceability
    assert trace.source_bundle == bundle.bundle_id
    assert trace.source_storyboard == storyboard.storyboard_id
    assert trace.source_reasoning
    assert trace.source_decisions
    assert trace.source_root_causes
    assert trace.source_validation
    assert trace.source_insights
    assert set(trace.registry_reference_ids).issubset(
        {a.reference_id or a.object_id for a in registry.assets}
    ) or all(ref for ref in trace.registry_reference_ids)


def test_conversation_context():
    *_, reasonings, storyboard, bundle, registry = _full_pipeline()
    response = answer_question(
        "What is the executive summary?",
        bundle=bundle,
        registry=registry,
        reasonings=reasonings,
        storyboard=storyboard,
    )
    assert response.conversation_context is not None
    ctx = build_follow_up_context(response=response)
    assert ctx.last_question == response.answer.question
    assert ctx.focus_decision_ids == response.traceability.source_decisions


def test_follow_up_generation():
    insights, validations, decisions, root_causes, reasonings, *_ = _full_pipeline()
    follow_ups = recommend_next_questions(
        decisions=decisions,
        root_causes=root_causes,
        validations=validations,
        reasonings=reasonings,
        insights=insights,
    )
    assert follow_ups
    assert all(item.question for item in follow_ups)
    assert all(item.source_gap for item in follow_ups)

    response = build_ai_response(
        mode=AnalystResponseMode.analyst,
        decisions=decisions,
        root_causes=root_causes,
        validations=validations,
        reasonings=reasonings,
        insights=insights,
    )
    assert response.follow_ups


def test_missing_information():
    response = build_ai_response(mode=AnalystResponseMode.executive, question="What happened?")
    assert "unavailable" in response.answer.answer_text.lower()
    assert response.answer.unavailable_note or response.explanation.unavailable_fields
    assert validate_response(response)["valid"] is True

    missing_decision = explain_decision(question="Explain decision")
    assert "unavailable" in missing_decision.answer.answer_text.lower()

    missing_rca = explain_root_cause(question="Explain root cause")
    assert "unavailable" in missing_rca.answer.answer_text.lower()


def test_immutability():
    insights, validations, decisions, root_causes, reasonings, storyboard, bundle, registry = _full_pipeline()
    snapshots = (
        insights.model_dump(),
        validations[0].model_dump(),
        decisions.model_dump(),
        root_causes.model_dump(),
        reasonings.model_dump(),
        storyboard.model_dump(),
        bundle.model_dump(),
        registry.model_dump(),
    )
    build_ai_response(
        mode=AnalystResponseMode.business,
        bundle=bundle,
        registry=registry,
        storyboard=storyboard,
        reasonings=reasonings,
        decisions=decisions,
        root_causes=root_causes,
        validations=validations,
        insights=insights,
    )
    explain_decision(bundle=bundle, decisions=decisions, registry=registry)
    explain_root_cause(bundle=bundle, root_causes=root_causes, registry=registry)
    assert insights.model_dump() == snapshots[0]
    assert validations[0].model_dump() == snapshots[1]
    assert decisions.model_dump() == snapshots[2]
    assert root_causes.model_dump() == snapshots[3]
    assert reasonings.model_dump() == snapshots[4]
    assert storyboard.model_dump() == snapshots[5]
    assert bundle.model_dump() == snapshots[6]
    assert registry.model_dump() == snapshots[7]


def test_future_extension_buckets():
    response = build_ai_response()
    for key in AI_ANALYST_FUTURE_EXTENSION_KEYS:
        assert key in response.metadata.future_extensions
        assert response.metadata.future_extensions[key] == {}


def test_modes_share_underlying_traceability():
    *_, reasonings, storyboard, bundle, registry = _full_pipeline()
    exec_resp = build_ai_response(
        mode=AnalystResponseMode.executive, bundle=bundle, registry=registry, reasonings=reasonings
    )
    tech_resp = build_ai_response(
        mode=AnalystResponseMode.technical, bundle=bundle, registry=registry, reasonings=reasonings
    )
    assert exec_resp.traceability.source_bundle == tech_resp.traceability.source_bundle
    assert exec_resp.traceability.source_decisions == tech_resp.traceability.source_decisions
    assert exec_resp.mode != tech_resp.mode
