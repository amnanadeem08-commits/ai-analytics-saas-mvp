from __future__ import annotations

from backend.models.evaluation_models import EvaluationCategory, EvaluationMetric
from backend.services.evaluation_report_service import (
    build_evaluation_report,
    build_summary,
    generate_recommendations,
    list_strengths,
    list_weaknesses,
)


def _metrics() -> list[EvaluationMetric]:
    return [
        EvaluationMetric(
            name="completion",
            category=EvaluationCategory.workflow,
            score=0.95,
            explanation="All stages completed",
        ),
        EvaluationMetric(
            name="retrieval_relevance",
            category=EvaluationCategory.rag,
            score=0.4,
            explanation="Few relevant chunks",
        ),
        EvaluationMetric(
            name="completeness",
            category=EvaluationCategory.final_response,
            score=0.3,
            explanation="Missing recommendations",
        ),
    ]


def test_build_summary_and_lists():
    metrics = _metrics()
    strengths = list_strengths(metrics)
    weaknesses = list_weaknesses(metrics)
    assert any("completion" in s for s in strengths)
    assert any("retrieval_relevance" in w for w in weaknesses)
    assert any("completeness" in w for w in weaknesses)

    summary = build_summary(
        overall_score=0.72,
        grade="C",
        category_scores={"workflow": 0.95, "rag": 0.4, "final_response": 0.3},
        workflow_id="wf_1",
        session_id="asess_1",
    )
    assert "grade C" in summary
    assert "wf_1" in summary


def test_deterministic_recommendations():
    metrics = _metrics()
    recs_a = generate_recommendations(metrics)
    recs_b = generate_recommendations(metrics)
    assert recs_a == recs_b
    assert any("knowledge" in r.lower() or "rag" in r.lower() or "Ingest" in r for r in recs_a)
    assert any("answer" in r.lower() or "recommendations" in r.lower() or "Require" in r for r in recs_a)


def test_build_evaluation_report_structure():
    report = build_evaluation_report(_metrics(), workflow_id="wf_x", session_id="s_x")
    assert report.summary
    assert report.grade in {"A", "B", "C", "D", "F"}
    assert 0.0 <= report.overall_score <= 1.0
    assert report.strengths
    assert report.weaknesses
    assert report.recommendations
    assert len(report.metrics) == 3
    assert report.metadata.get("read_only") is True
    assert "score_breakdown" in report.metadata
