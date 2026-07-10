from __future__ import annotations

from backend.services.llm_service import (
    FUTURE_LLM_PROVIDERS,
    MockLLMProvider,
    evaluate_result,
    generate,
    generate_plan,
    get_llm_provider,
    reset_llm_provider,
    select_action,
    set_llm_provider,
    structured_generate,
    validate_llm_response,
)


def test_mock_llm_generate_and_structured():
    reset_llm_provider()
    provider = get_llm_provider()
    assert isinstance(provider, MockLLMProvider)

    text = generate("Explain revenue decline", system="Be concise", max_tokens=64)
    assert text["provider"] == "mock_llm"
    assert text["mode"] == "generate"
    assert "revenue" in text["text"].lower() or "Explain" in text["text"]
    assert validate_llm_response(text)["valid"] is True

    structured = structured_generate(
        "Select tools for analysis",
        schema={
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "selected_tools": {"type": "array"},
                "findings": {"type": "array"},
                "confidence": {"type": "number"},
            },
        },
        system="planner",
    )
    assert structured["mode"] == "structured_generate"
    assert isinstance(structured["data"], dict)
    assert "summary" in structured["data"]
    assert validate_llm_response(structured)["valid"] is True


def test_mock_llm_planner_methods():
    reset_llm_provider()
    plan = generate_plan(
        "Analyze customer revenue decline",
        available_tools=[
            "data_profiling",
            "insight_generation",
            "validation",
            "governance_validation",
        ],
    )
    assert plan["mode"] == "generate_plan"
    assert isinstance(plan["steps"], list)
    assert plan["steps"]
    assert validate_llm_response(plan)["valid"] is True

    action = select_action("Find important KPIs", ["kpi_detection", "data_profiling"])
    assert action["mode"] == "select_action"
    assert action["action"] == "kpi_detection"
    assert validate_llm_response(action)["valid"] is True

    evaluation = evaluate_result("task", {"ok": True, "value": 1})
    assert evaluation["mode"] == "evaluate_result"
    assert evaluation["passed"] is True
    assert validate_llm_response(evaluation)["valid"] is True


def test_provider_swap_and_validation_failures():
    custom = MockLLMProvider(provider_id="mock_alt")
    set_llm_provider(custom)
    out = generate("hello")
    assert out["provider"] == "mock_alt"

    invalid = validate_llm_response({"mode": "generate"})
    assert invalid["valid"] is False
    assert any("Missing" in i for i in invalid["issues"])

    reset_llm_provider()
    assert get_llm_provider().provider_id == "mock_llm"
    assert "openai" in FUTURE_LLM_PROVIDERS
    assert "anthropic" in FUTURE_LLM_PROVIDERS
