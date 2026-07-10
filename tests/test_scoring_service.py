from __future__ import annotations

from backend.models.evaluation_models import EvaluationGrade
from backend.services.scoring_service import (
    DEFAULT_CATEGORY_WEIGHTS,
    average_metric_scores,
    calculate_weighted_score,
    clamp_score,
    grade_score,
    normalize_scores,
)


def test_normalize_and_clamp():
    assert clamp_score(1.5) == 1.0
    assert clamp_score(-1) == 0.0
    assert normalize_scores({"a": 1.2, "b": -0.1}) == {"a": 1.0, "b": 0.0}


def test_grade_assignment():
    assert grade_score(0.95) == EvaluationGrade.A.value
    assert grade_score(0.85) == EvaluationGrade.B.value
    assert grade_score(0.75) == EvaluationGrade.C.value
    assert grade_score(0.65) == EvaluationGrade.D.value
    assert grade_score(0.2) == EvaluationGrade.F.value


def test_weighted_scoring():
    scores = {
        "workflow": 1.0,
        "agents": 1.0,
        "tools": 1.0,
        "memory": 1.0,
        "rag": 1.0,
        "llm": 1.0,
        "final_response": 1.0,
    }
    breakdown = calculate_weighted_score(scores)
    assert breakdown.overall_score == 1.0
    assert breakdown.grade == "A"
    assert set(breakdown.weights_used).issubset(set(DEFAULT_CATEGORY_WEIGHTS) | set(scores))


def test_configurable_weights_change_outcome():
    scores = {
        "workflow": 1.0,
        "final_response": 0.0,
    }
    equal = calculate_weighted_score(scores, weights={"workflow": 1.0, "final_response": 1.0})
    skewed = calculate_weighted_score(scores, weights={"workflow": 0.1, "final_response": 10.0})
    assert skewed.overall_score < equal.overall_score
    assert equal.grade != skewed.grade or skewed.overall_score <= equal.overall_score


def test_average_metric_scores():
    metrics = [
        type("M", (), {"category": "rag", "score": 0.8})(),
        type("M", (), {"category": "rag", "score": 0.6})(),
        type("M", (), {"category": "llm", "score": 1.0})(),
    ]
    assert average_metric_scores(metrics, category="rag") == 0.7
    assert average_metric_scores(metrics, category="llm") == 1.0
