from __future__ import annotations

from typing import Any, Mapping

from backend.models.evaluation_models import EvaluationGrade, ScoreBreakdown

# Default category weights — configurable via calculate_weighted_score(weights=...).
DEFAULT_CATEGORY_WEIGHTS: dict[str, float] = {
    "workflow": 1.0,
    "agents": 1.2,
    "tools": 1.0,
    "memory": 0.8,
    "rag": 1.0,
    "llm": 1.2,
    "final_response": 1.5,
}

GRADE_THRESHOLDS: tuple[tuple[float, str], ...] = (
    (0.90, EvaluationGrade.A.value),
    (0.80, EvaluationGrade.B.value),
    (0.70, EvaluationGrade.C.value),
    (0.60, EvaluationGrade.D.value),
    (0.0, EvaluationGrade.F.value),
)


def clamp_score(score: float, *, low: float = 0.0, high: float = 1.0) -> float:
    try:
        value = float(score)
    except (TypeError, ValueError):
        return low
    return max(low, min(high, value))


def normalize_scores(
    scores: Mapping[str, float],
    *,
    low: float = 0.0,
    high: float = 1.0,
) -> dict[str, float]:
    """Clamp each score into [low, high]. Deterministic, no relative rescaling."""
    return {str(k): clamp_score(v, low=low, high=high) for k, v in dict(scores or {}).items()}


def grade_score(score: float) -> str:
    """Assign letter grade from overall score in [0, 1]."""
    value = clamp_score(score)
    for threshold, grade in GRADE_THRESHOLDS:
        if value >= threshold:
            return grade
    return EvaluationGrade.F.value


def calculate_weighted_score(
    scores: Mapping[str, float],
    *,
    weights: Mapping[str, float] | None = None,
) -> ScoreBreakdown:
    """
    Weighted mean of category scores.
    Missing weights default to 1.0. Zero/negative weights are ignored.
    """
    normalized = normalize_scores(scores)
    weight_map = dict(DEFAULT_CATEGORY_WEIGHTS)
    if weights:
        for key, value in weights.items():
            try:
                weight_map[str(key)] = float(value)
            except (TypeError, ValueError):
                continue

    contributions: dict[str, float] = {}
    used_weights: dict[str, float] = {}
    total_weight = 0.0
    weighted_sum = 0.0

    for category, score in sorted(normalized.items()):
        weight = float(weight_map.get(category, 1.0))
        if weight <= 0:
            continue
        contrib = score * weight
        contributions[category] = round(contrib, 6)
        used_weights[category] = weight
        weighted_sum += contrib
        total_weight += weight

    overall = clamp_score(weighted_sum / total_weight) if total_weight > 0 else 0.0
    return ScoreBreakdown(
        overall_score=round(overall, 4),
        grade=grade_score(overall),
        normalized_scores={k: round(v, 4) for k, v in normalized.items()},
        weighted_contribution=contributions,
        weights_used=used_weights,
    )


def average_metric_scores(metrics: list[Any], *, category: str | None = None) -> float:
    """Average metric.score values, optionally filtered by category."""
    values: list[float] = []
    for metric in metrics or []:
        cat = getattr(metric, "category", None)
        if cat is not None and hasattr(cat, "value"):
            cat = cat.value
        elif isinstance(metric, dict):
            cat = metric.get("category")
        if category is not None and str(cat) != str(category):
            continue
        score = getattr(metric, "score", None)
        if score is None and isinstance(metric, dict):
            score = metric.get("score")
        if score is None:
            continue
        values.append(clamp_score(score))
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)
