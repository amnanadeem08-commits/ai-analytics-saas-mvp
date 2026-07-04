from __future__ import annotations

from typing import Any

from backend.models.domain_context_models import DomainContext


def _domain_name(domain_context: DomainContext | dict[str, Any]) -> str:
    if isinstance(domain_context, DomainContext):
        return domain_context.detected_domain
    return (domain_context.get("detection", {}) or {}).get("domain", "Generic Analytics")

def build_suggested_questions(
    *,
    business_metrics: dict[str, Any],
    domain_context: DomainContext | dict[str, Any] | None = None,
    domain_intelligence: dict[str, Any] | None = None,
    profile: dict[str, Any],
) -> list[str]:
    metric = business_metrics.get("primary_metric")
    segment = business_metrics.get("primary_segment")
    source = domain_context if domain_context is not None else (domain_intelligence or {})
    domain = _domain_name(source)
    questions: list[str] = []

    if metric and segment:
        questions.extend(
            [
                f"Which {segment} has the strongest {metric} performance?",
                f"What explains the difference in {metric} across {segment}?",
                f"Which {segment} should leadership prioritize next?",
            ]
        )
    elif metric:
        questions.extend(
            [
                f"What is the current baseline for {metric}?",
                f"Which fields are most related to {metric}?",
            ]
        )

    if domain in {"Customer Churn", "Telecom"}:
        questions.append("Which segment has the highest churn risk?")
    elif domain == "Healthcare":
        questions.append("Which population segment has the highest risk indicators?")
    elif domain in {"Sales", "E-commerce"}:
        questions.append("Which segment is driving the strongest commercial performance?")

    if profile.get("outlier_summary"):
        questions.append(f"Which records are outliers in {profile['outlier_summary'][0]['column']}?")
    if profile.get("correlation_summary"):
        corr = profile["correlation_summary"][0]
        questions.append(f"How are {corr['column_a']} and {corr['column_b']} related?")
    if profile.get("trend_summary"):
        questions.append(f"What changed over time for {profile['trend_summary'][0]['metric']}?")
    if profile.get("total_missing_values", 0):
        questions.append("Which missing values should be fixed first?")

    questions.append("What risks should leadership watch before making a decision?")
    return list(dict.fromkeys(questions))[:8]
