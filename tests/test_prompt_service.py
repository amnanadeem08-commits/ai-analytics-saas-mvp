from __future__ import annotations

from backend.models.prompt_models import PromptTemplate, PromptType
from backend.services.prompt_service import (
    clear_prompts,
    ensure_builtin_prompts,
    get_prompt,
    list_prompts,
    register_prompt,
    render_prompt,
    validate_prompt,
)


def setup_function():
    clear_prompts(keep_builtins=False)
    ensure_builtin_prompts(reset=True)


def test_builtin_prompt_types_registered():
    prompts = list_prompts()
    types = {p.prompt_type for p in prompts}
    assert PromptType.analyst_prompt in types
    assert PromptType.planner_prompt in types
    assert PromptType.insight_prompt in types
    assert PromptType.reporting_prompt in types
    assert PromptType.validation_prompt in types


def test_register_and_get_prompt():
    tmpl = register_prompt(
        PromptTemplate(
            prompt_id="custom_analyst",
            prompt_type=PromptType.analyst_prompt,
            name="Custom",
            template="Query: {{user_query}}\nContext: {{context}}",
            required_variables=["user_query"],
        )
    )
    assert tmpl.prompt_id == "custom_analyst"
    fetched = get_prompt("custom_analyst")
    assert fetched is not None
    assert fetched.name == "Custom"


def test_render_prompt_variables():
    rendered = render_prompt(
        "analyst_default",
        {
            "user_query": "Analyze revenue decline",
            "context": {"dataset_id": "sales"},
            "retrieved_knowledge": "North region declined",
            "workflow_results": {"status": "completed"},
        },
    )
    assert "Analyze revenue decline" in rendered.rendered_text
    assert "North region declined" in rendered.rendered_text
    assert "user_query" in rendered.variables_used
    assert rendered.missing_variables == []


def test_validate_prompt_rejects_unsupported_variables():
    result = validate_prompt(
        {
            "prompt_id": "bad",
            "prompt_type": "analyst_prompt",
            "name": "Bad",
            "template": "Secret: {{api_key}} Query: {{user_query}}",
            "required_variables": ["user_query"],
        }
    )
    assert result["valid"] is False
    assert any("Unsupported variable" in i for i in result["issues"])


def test_validate_prompt_accepts_supported():
    result = validate_prompt(get_prompt("planner_default"))
    assert result["valid"] is True
