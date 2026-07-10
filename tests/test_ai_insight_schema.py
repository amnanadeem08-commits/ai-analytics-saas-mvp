from __future__ import annotations

import pandas as pd

from backend.ai.rule_based_engine import generate_rule_based_insights
from backend.models.ai_insight_models import AI_INSIGHT_SCHEMA_VERSION, InsightMetadata, InsightProvenance
from backend.models.insight_models import Insight
from backend.services.ai_business_insight_service import build_ai_business_insights_from_data_insights
from backend.services.ai_insight_mapper_service import (
    build_insight_collection,
    collect_insights,
    from_ai_business_card,
    from_analyst_response,
    from_executive_summary,
    from_rule_based_insight,
    to_legacy_insight,
)
from backend.services.analyst.analyst_service import answer_analyst_question
from backend.services.data_insights_service import build_data_insights
from backend.services.executive_insight_service import build_executive_summary


def test_universal_ai_insight_schema_defaults():
    insight = from_rule_based_insight(
        {
            "type": "overview",
            "title": "Dataset overview",
            "message": "10 rows analyzed.",
            "severity": "info",
            "metadata": {},
        }
    )
    assert insight.schema_version == AI_INSIGHT_SCHEMA_VERSION
    assert insight.generated_by.engine == "rule_based_engine"
    assert insight.generated_by.provider == "platform"
    assert insight.generated_by.engine_version == "1.0.0"
    assert insight.metadata.legacy["type"] == "overview"
    assert insight.metadata.debug == {"original_metadata_keys": []}
    assert insight.metadata.custom == {}
    assert insight.metadata.future_extensions == {}


def test_rule_based_mapper_maps_confidence_fields():
    insight = from_rule_based_insight(
        {
            "type": "quality",
            "title": "Quality",
            "message": "Quality is acceptable.",
            "severity": "warning",
            "metadata": {"confidence_score": 0.9, "recommended_action": "Review records"},
        }
    )
    assert insight.data_confidence == 0.9
    assert insight.overall_confidence > 0
    assert insight.recommended_actions[0].action == "Review records"


def test_executive_summary_mapper_includes_expected_outcome_and_data_quality():
    payload = build_executive_summary(
        pd.DataFrame({"revenue": [10, 20, 30], "segment": ["A", "B", "A"]})
    )
    insight = from_executive_summary(payload, domain="Sales")
    assert insight.domain == "Sales"
    assert insight.insight
    assert insight.expected_outcome
    assert insight.data_quality_score is not None or payload["metrics_snapshot"].get("data_quality_score") is None


def test_ai_business_card_mapper_preserves_validation_status():
    data_insights = build_data_insights(pd.DataFrame())
    payload = build_ai_business_insights_from_data_insights(data_insights)
    cards = payload["cards"]
    insight = from_ai_business_card(cards[0], domain="Generic Business Dataset")
    assert insight.validation_status.value == "insufficient"
    assert insight.metadata.legacy["source"] == "ai_business_insight_service"


def test_analyst_mapper_supports_decision_response():
    df = pd.DataFrame({"revenue": [10, 20, 30, 40], "segment": ["A", "B", "A", "B"]})
    response = answer_analyst_question(df, "What risks should management prioritize?")
    insight = from_analyst_response(response, question="What risks should management prioritize?", domain="Sales")
    assert insight.generated_by.engine == "analyst_service"
    assert insight.summary == response["answer"]


def test_collect_and_build_collection():
    df = pd.DataFrame({"value": [1, 2, 3, 4], "segment": ["A", "B", "A", "B"]})
    insights = collect_insights(generate_rule_based_insights(df), from_rule_based_insight, domain="Sales")
    collection = build_insight_collection(insights, dataset_id="demo", domain="Sales")
    assert collection.dataset_id == "demo"
    assert collection.domain == "Sales"
    assert len(collection.insights) >= 1
    assert collection.schema_version == AI_INSIGHT_SCHEMA_VERSION


def test_recommended_action_supports_effort_and_urgency():
    insight = from_executive_summary(
        {
            "insight": "Revenue is stable.",
            "reason": "No major movement detected.",
            "action": "Monitor weekly.",
            "evidence": ["Revenue reviewed across segments."],
            "metrics_snapshot": {},
            "confidence": "medium",
            "recommendations": [
                {
                    "recommendation": "Review top segment playbook",
                    "expected_impact": "Improves growth focus",
                    "estimated_effort": "low",
                    "urgency": "high",
                }
            ],
        }
    )
    action = insight.recommended_actions[0]
    assert action.estimated_effort.value == "low"
    assert action.urgency.value == "high"
    assert action.expected_outcome == "Improves growth focus"


def test_to_legacy_insight_reverse_adapter():
    universal = from_rule_based_insight(
        {
            "type": "overview",
            "title": "Dataset overview",
            "message": "Rows analyzed.",
            "severity": "info",
            "metadata": {"recommended_action": "Review"},
        }
    )
    legacy: Insight = to_legacy_insight(universal)
    assert legacy.title == "Dataset overview"
    assert legacy.message == "Rows analyzed."
    assert legacy.severity == "info"
    assert legacy.metadata["overall_confidence"] == universal.overall_confidence
    assert legacy.metadata["metadata"]["legacy"]["type"] == "overview"


def test_structured_metadata_buckets_are_independent():
    metadata = InsightMetadata(
        legacy={"type": "risk"},
        debug={"trace": "mapper"},
        custom={"tenant": "demo"},
        future_extensions={"validation_engine": {"enabled": False}},
    )
    assert metadata.legacy["type"] == "risk"
    assert metadata.debug["trace"] == "mapper"
    assert metadata.custom["tenant"] == "demo"
    assert metadata.future_extensions["validation_engine"]["enabled"] is False


def test_generated_by_provider_and_engine_version():
    insight = from_ai_business_card(
        {
            "type": "Opportunity",
            "title": "Opportunity",
            "business_meaning": "Validated signal",
            "supporting_evidence": "KPI discovered",
            "executive_recommendation": "Review segment",
            "confidence_score": 0.8,
            "evidence_status": "validated",
        },
        domain="Sales",
    )
    assert insight.generated_by.provider == "platform"
    assert insight.generated_by.engine_version == "1.0.0"
    assert isinstance(insight.generated_by, InsightProvenance)
