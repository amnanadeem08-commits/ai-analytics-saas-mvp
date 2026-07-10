from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.models.ai_insight_models import utc_now_iso


class LLMProvider(ABC):
    """Provider-agnostic LLM interface. No vendor lock-in."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.0,
        max_tokens: int = 512,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a free-text generation payload."""

    @abstractmethod
    def structured_generate(
        self,
        prompt: str,
        *,
        schema: dict[str, Any] | None = None,
        system: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a structured generation payload matching an optional schema."""

    @abstractmethod
    def validate_response(self, response: dict[str, Any]) -> dict[str, object]:
        """Validate a provider response for structural integrity."""

    def validate_output(self, response: dict[str, Any]) -> dict[str, object]:
        """Alias for validate_response — Sprint 7.6 interface name."""
        return self.validate_response(response)

    def generate_plan(
        self,
        task: str,
        *,
        available_tools: list[str] | None = None,
        agent_name: str = "",
        agent_role: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Optional planner hook — default uses structured_generate."""
        raise NotImplementedError

    def select_action(
        self,
        task: str,
        candidates: list[str],
        *,
        agent_role: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Optional action selection hook — default uses structured_generate."""
        raise NotImplementedError

    def evaluate_result(
        self,
        task: str,
        result: dict[str, Any],
        *,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Optional result evaluation hook — default uses structured_generate."""
        raise NotImplementedError


def _task_intent(task: str) -> str:
    text = " ".join(str(task or "").lower().split())
    if any(k in text for k in ("kpi", "metric", "key performance")):
        return "kpi_analysis"
    if any(k in text for k in ("forecast", "explain forecast", "explanation")):
        return "forecast_explanation"
    if any(k in text for k in ("validate", "validation", "quality")):
        return "validation"
    if any(k in text for k in ("govern", "compliance", "audit")):
        return "governance"
    if any(k in text for k in ("insight", "business", "finding")):
        return "insight_generation"
    if any(k in text for k in ("chart", "visual", "plot")):
        return "visualization"
    if any(k in text for k in ("profile", "dataset", "analyze", "revenue", "customer")):
        return "data_analysis"
    return "general_analysis"


def _deterministic_plan_steps(
    task: str,
    *,
    available_tools: list[str],
    agent_name: str,
    agent_role: str,
) -> list[dict[str, Any]]:
    """Deterministic multi-step plan templates for MockLLMProvider."""
    intent = _task_intent(task)
    tools = set(available_tools)
    steps: list[dict[str, Any]] = []

    def add(tool: str, description: str, agent: str, expected: str) -> None:
        if tool in tools or not tools:
            steps.append(
                {
                    "description": description,
                    "agent_name": agent or agent_name or "planner",
                    "tool_name": tool if (not tools or tool in tools) else (sorted(tools)[0] if tools else tool),
                    "expected_output": expected,
                }
            )

    # Full analytical pipeline for broad analysis tasks.
    if intent in {"data_analysis", "general_analysis", "kpi_analysis"}:
        add("data_profiling", "Profile dataset context", "Data Analyst Agent", "profile")
        if intent == "kpi_analysis" or "kpi" in task.lower():
            add("kpi_detection", "Detect important KPIs", "Data Analyst Agent", "kpi_summary")
        add("insight_generation", "Generate business insights", "Insight Agent", "analyst_response")
        add("validation", "Validate generated outputs", "Validation Agent", "validation_report")
        add("governance_validation", "Prepare reporting/governance output", "Reporting Agent", "governance")
    elif intent == "forecast_explanation":
        add("forecast_explanation", "Explain forecast results", agent_name or "Reporting Agent", "explanation")
        add("governance_validation", "Validate governance metadata", "Reporting Agent", "governance")
    elif intent == "validation":
        add("validation", "Validate insight quality", agent_name or "Validation Agent", "validation_report")
    elif intent == "governance":
        add("governance_validation", "Validate governance", agent_name or "Reporting Agent", "governance")
    elif intent == "insight_generation":
        add("insight_generation", "Generate insights", agent_name or "Insight Agent", "analyst_response")
        add("validation", "Validate insights", "Validation Agent", "validation_report")
    elif intent == "visualization":
        add("visualization_recommendation", "Recommend visualizations", agent_name or "Data Analyst Agent", "charts")
    else:
        add("data_profiling", "Analyze available context", agent_name or "Data Analyst Agent", "profile")

    # Constrain to available tools when provided.
    if tools:
        filtered = [s for s in steps if s["tool_name"] in tools]
        if filtered:
            steps = filtered
        else:
            # Fall back to first available tool.
            first = sorted(tools)[0]
            steps = [
                {
                    "description": f"Execute {first} for task",
                    "agent_name": agent_name or "planner",
                    "tool_name": first,
                    "expected_output": "tool_result",
                }
            ]

    # Role-scoped single-agent plans stay within role tools when agent_role set tightly.
    if agent_role == "validation" and "validation" in (tools or {"validation"}):
        steps = [
            {
                "description": "Validate outputs",
                "agent_name": agent_name or "Validation Agent",
                "tool_name": "validation",
                "expected_output": "validation_report",
            }
        ]
    elif agent_role == "insight" and "insight_generation" in (tools or {"insight_generation"}):
        steps = [
            {
                "description": "Generate insights",
                "agent_name": agent_name or "Insight Agent",
                "tool_name": "insight_generation",
                "expected_output": "analyst_response",
            }
        ]

    return steps


class MockLLMProvider(LLMProvider):
    """Deterministic local provider for tests and offline development."""

    def __init__(self, *, provider_id: str = "mock_llm") -> None:
        self.provider_id = provider_id
        self.call_count = 0

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.0,
        max_tokens: int = 512,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.call_count += 1
        trimmed = " ".join(str(prompt).split())
        preview = trimmed[:180]
        text = (
            f"[mock:{self.provider_id}] "
            f"{(system[:80] + ' | ') if system else ''}"
            f"{preview}"
        )
        if len(text) > max_tokens * 4:
            text = text[: max_tokens * 4]
        return {
            "provider": self.provider_id,
            "mode": "generate",
            "text": text,
            "prompt_chars": len(prompt),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "generated_at": utc_now_iso(),
            "metadata": dict(metadata or {}),
        }

    def structured_generate(
        self,
        prompt: str,
        *,
        schema: dict[str, Any] | None = None,
        system: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.call_count += 1
        schema = schema or {"type": "object", "properties": {"summary": {"type": "string"}}}
        properties = schema.get("properties") if isinstance(schema, dict) else {}
        if not isinstance(properties, dict):
            properties = {}
        data: dict[str, Any] = {}
        prompt_preview = " ".join(str(prompt).split())[:120]
        for key in properties:
            if key in {"summary", "headline", "text", "message", "understanding", "answer"}:
                data[key] = f"Mock structured response for: {prompt_preview}"
            elif key in {"findings", "items", "tools", "steps", "insights", "recommendations"}:
                if key == "insights":
                    data[key] = [
                        f"Insight: {prompt_preview[:60]}",
                        "Insight: supporting evidence reviewed",
                    ]
                elif key == "recommendations":
                    data[key] = [
                        "Investigate primary drivers",
                        "Validate findings with stakeholders",
                    ]
                else:
                    data[key] = [f"finding_{i}" for i in range(1, 3)]
            elif key in {"confidence", "score"}:
                data[key] = 0.75
            elif key in {"selected_tools", "tool_ids", "suggested_tools", "suggested_agents"}:
                data[key] = []
            elif key in {"intent"}:
                data[key] = _task_intent(prompt)
            elif key in {"action", "tool_id"}:
                data[key] = ""
            elif key in {"passed", "ok"}:
                data[key] = True
            else:
                data[key] = f"mock_{key}"
        if not data:
            data = {"summary": f"Mock structured response for: {' '.join(str(prompt).split())[:120]}"}
        return {
            "provider": self.provider_id,
            "mode": "structured_generate",
            "data": data,
            "schema": schema,
            "system": system,
            "generated_at": utc_now_iso(),
            "metadata": dict(metadata or {}),
        }

    def validate_response(self, response: dict[str, Any]) -> dict[str, object]:
        issues: list[str] = []
        if not isinstance(response, dict):
            return {"valid": False, "issues": ["Response is not a dict"], "issue_count": 1}
        if "provider" not in response:
            issues.append("Missing provider")
        mode = response.get("mode")
        if mode == "generate" and not response.get("text"):
            issues.append("Missing text")
        if mode in {"structured_generate", "generate_plan", "select_action", "evaluate_result"}:
            if mode == "structured_generate" and not isinstance(response.get("data"), dict):
                issues.append("Missing structured data")
            if mode == "generate_plan" and not isinstance(response.get("steps"), list):
                issues.append("Missing plan steps")
            if mode == "select_action" and "action" not in response:
                issues.append("Missing action")
            if mode == "evaluate_result" and "passed" not in response:
                issues.append("Missing evaluation passed flag")
        if mode not in {
            "generate",
            "structured_generate",
            "generate_plan",
            "select_action",
            "evaluate_result",
            None,
        }:
            issues.append(f"Unknown mode: {mode}")
        return {"valid": not issues, "issues": issues, "issue_count": len(issues)}

    def generate_plan(
        self,
        task: str,
        *,
        available_tools: list[str] | None = None,
        agent_name: str = "",
        agent_role: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.call_count += 1
        tools = list(available_tools or [])
        steps = _deterministic_plan_steps(
            task,
            available_tools=tools,
            agent_name=agent_name,
            agent_role=agent_role,
        )
        intent = _task_intent(task)
        return {
            "provider": self.provider_id,
            "mode": "generate_plan",
            "task": task,
            "intent": intent,
            "understanding": f"Task understood as {intent.replace('_', ' ')}.",
            "steps": steps,
            "agent_name": agent_name,
            "agent_role": agent_role,
            "generated_at": utc_now_iso(),
            "metadata": dict(metadata or {}),
        }

    def select_action(
        self,
        task: str,
        candidates: list[str],
        *,
        agent_role: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.call_count += 1
        intent = _task_intent(task)
        preference = {
            "kpi_analysis": "kpi_detection",
            "forecast_explanation": "forecast_explanation",
            "validation": "validation",
            "governance": "governance_validation",
            "insight_generation": "insight_generation",
            "visualization": "visualization_recommendation",
            "data_analysis": "data_profiling",
            "general_analysis": "data_profiling",
        }.get(intent)
        action = ""
        if preference and preference in candidates:
            action = preference
        elif candidates:
            action = candidates[0]
        return {
            "provider": self.provider_id,
            "mode": "select_action",
            "action": action,
            "tool_id": action,
            "candidates": list(candidates),
            "intent": intent,
            "agent_role": agent_role,
            "generated_at": utc_now_iso(),
            "metadata": dict(metadata or {}),
        }

    def evaluate_result(
        self,
        task: str,
        result: dict[str, Any],
        *,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.call_count += 1
        has_error = bool(result.get("error_message") or result.get("error"))
        empty = not result or result.get("empty") is True
        passed = not has_error and not empty
        return {
            "provider": self.provider_id,
            "mode": "evaluate_result",
            "passed": passed,
            "score": 0.9 if passed else 0.2,
            "summary": "Result acceptable" if passed else "Result needs attention",
            "task": task,
            "generated_at": utc_now_iso(),
            "metadata": dict(metadata or {}),
        }


# Reserved / optional providers — adapters live under backend.services.providers.
FUTURE_LLM_PROVIDERS: tuple[str, ...] = ("openai", "anthropic", "local")

_DEFAULT_PROVIDER: LLMProvider | None = None
_PROVIDER_CONFIG: dict[str, Any] | None = None


def get_llm_provider() -> LLMProvider:
    global _DEFAULT_PROVIDER
    if _DEFAULT_PROVIDER is None:
        _DEFAULT_PROVIDER = MockLLMProvider()
    return _DEFAULT_PROVIDER


def set_llm_provider(provider: LLMProvider) -> LLMProvider:
    global _DEFAULT_PROVIDER
    _DEFAULT_PROVIDER = provider
    return provider


def reset_llm_provider() -> LLMProvider:
    """Restore the default mock provider."""
    global _PROVIDER_CONFIG
    _PROVIDER_CONFIG = None
    return set_llm_provider(MockLLMProvider())


def build_provider(
    provider_name: str = "mock",
    *,
    config: Any | None = None,
) -> LLMProvider:
    """Factory for provider adapters. Unknown/disabled providers fall back to mock."""
    from backend.models.llm_models import LLMProviderConfig

    name = str(provider_name or "mock").strip().lower()
    cfg = config
    if cfg is None:
        cfg = LLMProviderConfig(provider_name=name)
    elif isinstance(cfg, dict):
        cfg = LLMProviderConfig(**cfg)

    if name in {"mock", "mock_llm"}:
        return MockLLMProvider()
    if name == "openai":
        from backend.services.providers.openai_provider import OpenAIProvider

        return OpenAIProvider(cfg)
    if name == "anthropic":
        from backend.services.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(cfg)
    if name == "local":
        from backend.services.providers.local_provider import LocalProvider

        return LocalProvider(cfg)
    return MockLLMProvider(provider_id=f"mock_{name}_fallback")


def configure_llm_provider(
    provider_name: str = "mock",
    *,
    config: Any | None = None,
) -> LLMProvider:
    """Switch the active process-wide LLM provider."""
    global _PROVIDER_CONFIG
    provider = build_provider(provider_name, config=config)
    _PROVIDER_CONFIG = {
        "provider_name": provider_name,
        "config": config.model_dump() if hasattr(config, "model_dump") else config,
    }
    return set_llm_provider(provider)


def generate(prompt: str, **kwargs: Any) -> dict[str, Any]:
    return get_llm_provider().generate(prompt, **kwargs)


def structured_generate(prompt: str, **kwargs: Any) -> dict[str, Any]:
    return get_llm_provider().structured_generate(prompt, **kwargs)


def validate_llm_response(response: dict[str, Any]) -> dict[str, object]:
    return get_llm_provider().validate_response(response)


def validate_output(response: dict[str, Any]) -> dict[str, object]:
    return get_llm_provider().validate_output(response)


def generate_plan(task: str, **kwargs: Any) -> dict[str, Any]:
    return get_llm_provider().generate_plan(task, **kwargs)


def select_action(task: str, candidates: list[str], **kwargs: Any) -> dict[str, Any]:
    return get_llm_provider().select_action(task, candidates, **kwargs)


def evaluate_result(task: str, result: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return get_llm_provider().evaluate_result(task, result, **kwargs)


def complete_llm_request(llm_request: Any) -> Any:
    """Execute an LLMRequest and return an LLMResponse with validation status."""
    from backend.models.llm_models import LLMRequest, LLMResponse
    from backend.services.output_validation_service import parse_structured_response

    if isinstance(llm_request, dict):
        llm_request = LLMRequest(**llm_request)
    provider = get_llm_provider()
    schema = llm_request.output_schema or None
    context_blob = ""
    if llm_request.context:
        import json as _json

        ctx = llm_request.context
        if isinstance(ctx, dict):
            context_blob = f"\n\nContext:\n{_json.dumps(ctx, default=str)}"
        else:
            context_blob = f"\n\nContext:\n{ctx}"
    prompt = f"{llm_request.prompt}{context_blob}"
    temperature = (
        llm_request.temperature
        if llm_request.temperature is not None
        else 0.0
    )
    max_tokens = llm_request.max_tokens if llm_request.max_tokens is not None else 512

    if schema:
        raw = provider.structured_generate(
            prompt,
            schema=schema,
            system=llm_request.system,
            metadata=llm_request.metadata,
        )
        structured = raw.get("data") if isinstance(raw.get("data"), dict) else {}
        content = str(structured.get("summary") or structured.get("answer") or raw.get("text") or "")
        parsed = parse_structured_response(structured or content, schema=schema)
        structured = parsed.get("data") if isinstance(parsed.get("data"), dict) else structured
        validation_status = "valid" if parsed.get("valid") else "invalid"
    else:
        raw = provider.generate(
            prompt,
            system=llm_request.system,
            temperature=temperature,
            max_tokens=max_tokens,
            metadata=llm_request.metadata,
        )
        content = str(raw.get("text") or "")
        structured = {}
        validation_status = "valid" if content else "invalid"

    provider_name = str(raw.get("provider") or getattr(provider, "provider_id", "unknown"))
    return LLMResponse(
        content=content,
        structured_output=structured,
        provider=provider_name,
        model_name=str(raw.get("model") or ""),
        usage_metadata=dict(raw.get("usage") or {}),
        raw=raw if isinstance(raw, dict) else {},
        validation_status=validation_status,
        metadata={
            "fallback": bool(raw.get("fallback")),
            "schema_version": "1.0.0",
            **dict(llm_request.metadata or {}),
        },
    )
