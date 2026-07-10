from __future__ import annotations

import re
from typing import Any

from backend.models.prompt_models import PromptTemplate, PromptType, RenderedPrompt

_PROMPT_REGISTRY: dict[str, PromptTemplate] = {}

_VARIABLE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")

SUPPORTED_VARIABLES: frozenset[str] = frozenset(
    {
        "user_query",
        "context",
        "retrieved_knowledge",
        "workflow_results",
    }
)

_BUILTIN_PROMPTS: tuple[dict[str, Any], ...] = (
    {
        "prompt_id": "analyst_default",
        "prompt_type": PromptType.analyst_prompt,
        "name": "AI Analyst Default",
        "description": "Primary analyst understanding and answer prompt",
        "required_variables": ["user_query"],
        "template": (
            "You are an AI Analyst.\n"
            "User query: {{user_query}}\n"
            "Context: {{context}}\n"
            "Retrieved knowledge: {{retrieved_knowledge}}\n"
            "Workflow results: {{workflow_results}}\n"
            "Provide a clear analytical answer with insights and recommendations."
        ),
    },
    {
        "prompt_id": "planner_default",
        "prompt_type": PromptType.planner_prompt,
        "name": "Planner Default",
        "description": "Plan analytical steps for a user query",
        "required_variables": ["user_query"],
        "template": (
            "Create an analysis plan for: {{user_query}}\n"
            "Context: {{context}}\n"
            "Retrieved knowledge: {{retrieved_knowledge}}\n"
            "Return ordered steps with tools and expected outputs."
        ),
    },
    {
        "prompt_id": "insight_default",
        "prompt_type": PromptType.insight_prompt,
        "name": "Insight Default",
        "description": "Generate business insights from analysis context",
        "required_variables": ["user_query", "workflow_results"],
        "template": (
            "Generate business insights for: {{user_query}}\n"
            "Context: {{context}}\n"
            "Retrieved knowledge: {{retrieved_knowledge}}\n"
            "Workflow results: {{workflow_results}}"
        ),
    },
    {
        "prompt_id": "reporting_default",
        "prompt_type": PromptType.reporting_prompt,
        "name": "Reporting Default",
        "description": "Compose a structured reporting response",
        "required_variables": ["user_query", "workflow_results"],
        "template": (
            "Compose a report answering: {{user_query}}\n"
            "Context: {{context}}\n"
            "Retrieved knowledge: {{retrieved_knowledge}}\n"
            "Workflow results: {{workflow_results}}"
        ),
    },
    {
        "prompt_id": "validation_default",
        "prompt_type": PromptType.validation_prompt,
        "name": "Validation Default",
        "description": "Validate analytical outputs for completeness",
        "required_variables": ["workflow_results"],
        "template": (
            "Validate the following analysis outputs.\n"
            "User query: {{user_query}}\n"
            "Context: {{context}}\n"
            "Retrieved knowledge: {{retrieved_knowledge}}\n"
            "Workflow results: {{workflow_results}}\n"
            "Check for missing fields, incorrect types, and unsupported claims."
        ),
    },
)


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return "\n".join(_format_value(v) for v in value)
    if isinstance(value, dict):
        import json

        return json.dumps(value, default=str)
    return str(value)


def clear_prompts(*, keep_builtins: bool = False) -> None:
    global _PROMPT_REGISTRY
    _PROMPT_REGISTRY = {}
    if keep_builtins:
        ensure_builtin_prompts(reset=True)


def ensure_builtin_prompts(*, reset: bool = False) -> list[PromptTemplate]:
    if reset:
        clear_prompts(keep_builtins=False)
    registered: list[PromptTemplate] = []
    for spec in _BUILTIN_PROMPTS:
        existing = _PROMPT_REGISTRY.get(spec["prompt_id"])
        if existing is not None and not reset:
            registered.append(existing.model_copy(deep=True))
            continue
        tmpl = PromptTemplate(**spec)
        _PROMPT_REGISTRY[tmpl.prompt_id] = tmpl
        registered.append(tmpl.model_copy(deep=True))
    return registered


def register_prompt(template: PromptTemplate | dict[str, Any]) -> PromptTemplate:
    if isinstance(template, dict):
        template = PromptTemplate(**template)
    validation = validate_prompt(template)
    if not validation.get("valid"):
        raise ValueError(f"Invalid prompt template: {validation.get('issues')}")
    stored = template.model_copy(deep=True)
    _PROMPT_REGISTRY[stored.prompt_id] = stored
    return stored.model_copy(deep=True)


def get_prompt(prompt_id: str) -> PromptTemplate | None:
    ensure_builtin_prompts()
    item = _PROMPT_REGISTRY.get(prompt_id)
    return item.model_copy(deep=True) if item is not None else None


def list_prompts(*, prompt_type: PromptType | str | None = None) -> list[PromptTemplate]:
    ensure_builtin_prompts()
    items = list(_PROMPT_REGISTRY.values())
    if prompt_type is not None:
        ptype = prompt_type if isinstance(prompt_type, PromptType) else PromptType(str(prompt_type))
        items = [p for p in items if p.prompt_type == ptype]
    return [p.model_copy(deep=True) for p in items]


def validate_prompt(template: PromptTemplate | dict[str, Any] | str) -> dict[str, Any]:
    issues: list[str] = []
    if isinstance(template, str):
        text = template
        required: list[str] = []
        prompt_id = ""
        prompt_type = None
    elif isinstance(template, dict):
        try:
            tmpl = PromptTemplate(**template)
        except Exception as exc:  # noqa: BLE001
            return {"valid": False, "issues": [f"Invalid template model: {exc}"], "issue_count": 1}
        text = tmpl.template
        required = list(tmpl.required_variables)
        prompt_id = tmpl.prompt_id
        prompt_type = tmpl.prompt_type
    else:
        text = template.template
        required = list(template.required_variables)
        prompt_id = template.prompt_id
        prompt_type = template.prompt_type

    if not str(text or "").strip():
        issues.append("Template text is empty")
    if prompt_id is not None and prompt_id == "":
        issues.append("prompt_id is required")
    if prompt_type is not None and not isinstance(prompt_type, PromptType):
        try:
            PromptType(str(prompt_type))
        except Exception:
            issues.append(f"Unknown prompt_type: {prompt_type}")

    found = set(_VARIABLE_PATTERN.findall(text or ""))
    for var in found:
        if var not in SUPPORTED_VARIABLES:
            issues.append(f"Unsupported variable: {var}")
    for req in required:
        if req not in SUPPORTED_VARIABLES:
            issues.append(f"Unsupported required variable: {req}")
        if req not in found and f"{{{{{req}}}}}" not in (text or ""):
            # Required vars should appear in the template.
            if req not in found:
                issues.append(f"Required variable missing from template: {req}")

    return {"valid": not issues, "issues": issues, "issue_count": len(issues), "variables": sorted(found)}


def render_prompt(
    prompt_id: str,
    variables: dict[str, Any] | None = None,
    *,
    template: PromptTemplate | None = None,
) -> RenderedPrompt:
    ensure_builtin_prompts()
    tmpl = template or get_prompt(prompt_id)
    if tmpl is None:
        raise KeyError(f"Prompt not found: {prompt_id}")

    vars_in = dict(variables or {})
    # Normalize common aliases
    if "query" in vars_in and "user_query" not in vars_in:
        vars_in["user_query"] = vars_in["query"]
    if "rag" in vars_in and "retrieved_knowledge" not in vars_in:
        vars_in["retrieved_knowledge"] = vars_in["rag"]
    if "memory" in vars_in and "context" not in vars_in:
        vars_in["context"] = vars_in["memory"]

    found = _VARIABLE_PATTERN.findall(tmpl.template)
    missing = [v for v in tmpl.required_variables if v not in vars_in or vars_in.get(v) in (None, "")]
    rendered = tmpl.template

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in vars_in:
            return match.group(0)
        return _format_value(vars_in[key])

    rendered = _VARIABLE_PATTERN.sub(_replace, rendered)
    return RenderedPrompt(
        prompt_id=tmpl.prompt_id,
        prompt_type=tmpl.prompt_type.value if isinstance(tmpl.prompt_type, PromptType) else str(tmpl.prompt_type),
        rendered_text=rendered,
        variables_used=sorted(set(found).intersection(vars_in)),
        missing_variables=missing,
        metadata={"schema_version": "1.0.0"},
    )


def get_prompt_by_type(prompt_type: PromptType | str) -> PromptTemplate | None:
    items = list_prompts(prompt_type=prompt_type)
    return items[0] if items else None
