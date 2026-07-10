from __future__ import annotations

from backend.models.llm_models import LLMProviderConfig, LLMRequest, LLMResponse
from backend.services.llm_service import (
    FUTURE_LLM_PROVIDERS,
    LLMProvider,
    MockLLMProvider,
    build_provider,
    complete_llm_request,
    configure_llm_provider,
    generate,
    get_llm_provider,
    reset_llm_provider,
    structured_generate,
    validate_output,
)
from backend.services.providers.anthropic_provider import AnthropicProvider
from backend.services.providers.local_provider import LocalProvider
from backend.services.providers.openai_provider import OpenAIProvider


def setup_function():
    reset_llm_provider()


def test_provider_interface_compatibility():
    for provider in (
        MockLLMProvider(),
        OpenAIProvider(LLMProviderConfig(provider_name="openai", enabled=False)),
        AnthropicProvider(LLMProviderConfig(provider_name="anthropic", enabled=False)),
        LocalProvider(LLMProviderConfig(provider_name="local", enabled=False, base_url="")),
    ):
        assert isinstance(provider, LLMProvider)
        out = provider.generate("hello")
        assert "text" in out
        assert provider.validate_output(out)["valid"] is True
        structured = provider.structured_generate(
            "summarize",
            schema={"type": "object", "properties": {"summary": {"type": "string"}}},
        )
        assert isinstance(structured.get("data"), dict)


def test_mock_provider_generates_output():
    provider = MockLLMProvider()
    text = provider.generate("Analyze revenue decline")
    assert text["provider"] == "mock_llm"
    assert "revenue" in text["text"].lower() or "Analyze" in text["text"]
    assert provider.validate_output(text)["valid"] is True


def test_build_provider_factory_and_safe_fallback():
    assert isinstance(build_provider("mock"), MockLLMProvider)
    openai = build_provider("openai", config=LLMProviderConfig(provider_name="openai", enabled=True))
    assert isinstance(openai, OpenAIProvider)
    # No API key → safe fallback path
    out = openai.generate("test without key")
    assert out.get("fallback") is True or out.get("provider") == "openai"

    unknown = build_provider("unknown_vendor")
    assert isinstance(unknown, MockLLMProvider)


def test_configure_provider_from_factory():
    configure_llm_provider("mock")
    assert isinstance(get_llm_provider(), MockLLMProvider)
    out = generate("ping")
    assert out["mode"] == "generate"


def test_complete_llm_request_structured():
    reset_llm_provider()
    response = complete_llm_request(
        LLMRequest(
            prompt="Analyze revenue",
            context={"dataset_id": "sales"},
            output_schema={
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                    "insights": {"type": "array"},
                    "recommendations": {"type": "array"},
                },
                "required": ["answer"],
            },
        )
    )
    assert isinstance(response, LLMResponse)
    assert response.content or response.structured_output
    assert response.provider
    assert response.validation_status in {"valid", "invalid", "repaired"}


def test_future_providers_listed():
    assert "openai" in FUTURE_LLM_PROVIDERS
    assert "anthropic" in FUTURE_LLM_PROVIDERS
    assert "local" in FUTURE_LLM_PROVIDERS


def test_validate_output_alias():
    raw = structured_generate("x", schema={"type": "object", "properties": {"summary": {"type": "string"}}})
    assert validate_output(raw)["valid"] is True
