from __future__ import annotations

from typing import Any

from backend.models.evaluation_models import EvaluationMetric, EvaluationReport
from backend.services.scoring_service import average_metric_scores, calculate_weighted_score

# Deterministic thresholds for strength / weakness classification.
STRENGTH_THRESHOLD = 0.80
WEAKNESS_THRESHOLD = 0.60


def build_summary(
    *,
    overall_score: float,
    grade: str,
    category_scores: dict[str, float],
    workflow_id: str = "",
    session_id: str = "",
) -> str:
    parts = [
        f"Evaluation grade {grade} with overall score {overall_score:.2f}.",
    ]
    if workflow_id:
        parts.append(f"Workflow: {workflow_id}.")
    if session_id:
        parts.append(f"Session: {session_id}.")
    if category_scores:
        ranked = sorted(category_scores.items(), key=lambda kv: (-kv[1], kv[0]))
        best = ranked[0]
        worst = ranked[-1]
        parts.append(f"Strongest category: {best[0]} ({best[1]:.2f}).")
        parts.append(f"Weakest category: {worst[0]} ({worst[1]:.2f}).")
    return " ".join(parts)


def list_strengths(metrics: list[EvaluationMetric] | list[dict[str, Any]]) -> list[str]:
    strengths: list[str] = []
    for metric in metrics or []:
        if isinstance(metric, dict):
            name = str(metric.get("name") or "")
            score = float(metric.get("score") or 0.0)
            explanation = str(metric.get("explanation") or "")
            category = str(metric.get("category") or "")
        else:
            name = metric.name
            score = float(metric.score)
            explanation = metric.explanation
            category = (
                metric.category.value
                if hasattr(metric.category, "value")
                else str(metric.category)
            )
        if score >= STRENGTH_THRESHOLD:
            strengths.append(
                f"{category}.{name} scored {score:.2f}"
                + (f": {explanation}" if explanation else "")
            )
    return strengths


def list_weaknesses(metrics: list[EvaluationMetric] | list[dict[str, Any]]) -> list[str]:
    weaknesses: list[str] = []
    for metric in metrics or []:
        if isinstance(metric, dict):
            name = str(metric.get("name") or "")
            score = float(metric.get("score") or 0.0)
            explanation = str(metric.get("explanation") or "")
            category = str(metric.get("category") or "")
        else:
            name = metric.name
            score = float(metric.score)
            explanation = metric.explanation
            category = (
                metric.category.value
                if hasattr(metric.category, "value")
                else str(metric.category)
            )
        if score < WEAKNESS_THRESHOLD:
            weaknesses.append(
                f"{category}.{name} scored {score:.2f}"
                + (f": {explanation}" if explanation else "")
            )
    return weaknesses


# Deterministic recommendation templates keyed by (category, metric_name).
_RECOMMENDATION_RULES: dict[tuple[str, str], str] = {
    ("workflow", "completion"): "Investigate failed or blocked workflow stages before re-running analysis.",
    ("workflow", "failure_rate"): "Reduce stage failures by validating required context keys before execution.",
    ("workflow", "retries"): "Review retry-heavy stages and stabilize upstream inputs.",
    ("agents", "completion"): "Ensure agent tasks complete successfully before accepting final answers.",
    ("agents", "success_rate"): "Review agent error messages and tool availability for failed runs.",
    ("agents", "planning_quality"): "Improve planning inputs (task clarity, available tools) for higher plan quality.",
    ("tools", "correct_selection"): "Align tool selection with task intent using the planning engine.",
    ("tools", "execution_success"): "Fix failing tool executions and verify tool registry availability.",
    ("tools", "fallback_usage"): "Reduce fallback tool usage by ensuring preferred tools are available.",
    ("memory", "retrieval_usefulness"): "Store clearer task summaries so memory retrieval is more useful.",
    ("memory", "context_usage"): "Ensure memory context is merged into planning and agent stages.",
    ("rag", "retrieval_relevance"): "Ingest more relevant knowledge documents for the query domain.",
    ("rag", "source_diversity"): "Add knowledge from multiple sources to improve retrieval diversity.",
    ("rag", "context_quality"): "Improve RAG chunk quality and filtering for higher context usefulness.",
    ("llm", "structured_output_validity"): "Enforce structured generation schemas for analyst responses.",
    ("llm", "schema_compliance"): "Repair or reject LLM outputs that miss required schema fields.",
    ("llm", "hallucination_indicators"): "Ground LLM answers in workflow, RAG, and memory evidence.",
    ("final_response", "completeness"): "Require answer, insights, and recommendations in the final response.",
    ("final_response", "consistency"): "Align final response content with workflow and RAG evidence.",
    ("final_response", "recommendation_quality"): "Ensure recommendations are concrete and non-empty.",
}


def generate_recommendations(
    metrics: list[EvaluationMetric] | list[dict[str, Any]],
) -> list[str]:
    """Deterministic recommendations from observed weak metrics only — no speculation."""
    recs: list[str] = []
    seen: set[str] = set()
    for metric in metrics or []:
        if isinstance(metric, dict):
            name = str(metric.get("name") or "")
            score = float(metric.get("score") or 0.0)
            category = str(metric.get("category") or "")
        else:
            name = metric.name
            score = float(metric.score)
            category = (
                metric.category.value
                if hasattr(metric.category, "value")
                else str(metric.category)
            )
        if score >= WEAKNESS_THRESHOLD:
            continue
        key = (category, name)
        text = _RECOMMENDATION_RULES.get(key)
        if text and text not in seen:
            seen.add(text)
            recs.append(text)
    if not recs and metrics:
        recs.append("No critical metric weaknesses observed; maintain current execution quality.")
    return recs


def build_evaluation_report(
    metrics: list[EvaluationMetric],
    *,
    category_scores: dict[str, float] | None = None,
    weights: dict[str, float] | None = None,
    workflow_id: str = "",
    session_id: str = "",
) -> EvaluationReport:
    cats = category_scores or {}
    if not cats:
        categories = sorted(
            {
                (
                    m.category.value
                    if hasattr(m.category, "value")
                    else str(m.category)
                )
                for m in metrics
            }
        )
        cats = {c: average_metric_scores(metrics, category=c) for c in categories}

    breakdown = calculate_weighted_score(cats, weights=weights)
    return EvaluationReport(
        summary=build_summary(
            overall_score=breakdown.overall_score,
            grade=breakdown.grade,
            category_scores=cats,
            workflow_id=workflow_id,
            session_id=session_id,
        ),
        strengths=list_strengths(metrics),
        weaknesses=list_weaknesses(metrics),
        recommendations=generate_recommendations(metrics),
        metrics=list(metrics),
        grade=breakdown.grade,
        overall_score=breakdown.overall_score,
        metadata={
            "score_breakdown": breakdown.model_dump(),
            "category_scores": cats,
            "read_only": True,
        },
    )
