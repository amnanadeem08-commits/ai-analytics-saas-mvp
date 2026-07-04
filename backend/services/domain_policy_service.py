from __future__ import annotations

from typing import Any

from backend.services.domain_profile_service import domain_profile


DOMAIN_PROMPTS: dict[str, str] = {
    "Healthcare": "HEALTHCARE_ANALYST_PROMPT",
    "Generic Business Dataset": "GENERAL_ANALYST_PROMPT",
}


HEALTHCARE_REPLACEMENTS: list[tuple[str, str]] = [
    ("business", "health"),
    ("Business", "Health"),
    ("KPI", "health indicator"),
    ("KPIs", "health indicators"),
    ("kpi", "health indicator"),
    ("kpis", "health indicators"),
    ("executive", "clinical leadership"),
    ("Executive", "Clinical Leadership"),
    ("revenue", "outcome"),
    ("Revenue", "Outcome"),
    ("customer", "patient"),
    ("Customer", "Patient"),
    ("leadership attention", "care team attention"),
    ("targets or budgets", "care targets or resource plans"),
]


def _prompt_for_domain(domain: str) -> str:
    if domain in DOMAIN_PROMPTS:
        return DOMAIN_PROMPTS[domain]
    return f"{domain.upper().replace(' ', '_').replace('-', '_')}_ANALYST_PROMPT"


def _language_terms(domain: str, profile: dict[str, Any]) -> dict[str, str]:
    return {
        "lens": str(profile.get("context") or "business analytics").lower(),
        "leader": "clinical leadership team" if domain == "Healthcare" else "business leadership team",
        "metric": "health indicator" if domain == "Healthcare" else "KPI",
        "metrics": "health indicators" if domain == "Healthcare" else "KPIs",
        "driver": (profile.get("root_causes") or ["evidence-backed driver"])[0],
        "summary_action": f"prioritize {(profile.get('metrics') or ['primary KPI'])[0].lower()} and the strongest validated recommendations",
    }


def build_domain_policy(domain: str) -> dict[str, Any]:
    profile = domain_profile(domain)
    replacements = HEALTHCARE_REPLACEMENTS if profile["domain"] == "Healthcare" else []
    return {
        "domain": profile["domain"],
        "prompt": _prompt_for_domain(profile["domain"]),
        "terms": _language_terms(profile["domain"], profile),
        "replacements": [{"from": source, "to": target} for source, target in replacements],
    }


def apply_language_policy(value: Any, policy: dict[str, Any]) -> Any:
    replacements = policy.get("replacements") or []
    if not replacements:
        return value

    def apply_text(text: str) -> str:
        result = text
        for replacement in replacements:
            source = str(replacement.get("from", ""))
            target = str(replacement.get("to", ""))
            if source:
                result = result.replace(source, target)
        return result

    if isinstance(value, str):
        return apply_text(value)
    if isinstance(value, list):
        return [apply_language_policy(item, policy) for item in value]
    if isinstance(value, dict):
        return {key: apply_language_policy(item, policy) for key, item in value.items()}
    return value
