from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

from backend.models.ai_insight_models import utc_now_iso
from backend.models.llm_models import LLMProviderConfig
from backend.services.llm_service import LLMProvider, MockLLMProvider


class AnthropicProvider(LLMProvider):
    """Anthropic adapter. Optional; fails safely to mock when unavailable."""

    def __init__(self, config: LLMProviderConfig | None = None) -> None:
        self.config = config or LLMProviderConfig(
            provider_name="anthropic",
            model_name=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
            api_key_env="ANTHROPIC_API_KEY",
            base_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"),
            enabled=True,
        )
        self.provider_id = "anthropic"
        self._fallback = MockLLMProvider(provider_id="mock_anthropic_fallback")

    def _api_key(self) -> str:
        env_name = self.config.api_key_env or "ANTHROPIC_API_KEY"
        return os.getenv(env_name, "").strip()

    def _available(self) -> bool:
        return bool(self.config.enabled and self._api_key())

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.0,
        max_tokens: int = 512,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self._available():
            out = self._fallback.generate(
                prompt,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
                metadata={**(metadata or {}), "fallback_reason": "anthropic_unavailable"},
            )
            out["provider"] = "anthropic"
            out["fallback"] = True
            return out
        try:
            payload = {
                "model": self.config.model_name,
                "max_tokens": max_tokens or self.config.max_tokens,
                "temperature": temperature if temperature is not None else self.config.temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                payload["system"] = system
            data = self._post("/messages", payload)
            blocks = data.get("content") or []
            text_parts = [
                str(block.get("text") or "")
                for block in blocks
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            content = "\n".join(part for part in text_parts if part)
            return {
                "provider": "anthropic",
                "mode": "generate",
                "text": content,
                "model": self.config.model_name,
                "usage": data.get("usage") or {},
                "generated_at": utc_now_iso(),
                "metadata": dict(metadata or {}),
                "raw": data,
            }
        except Exception as exc:  # noqa: BLE001
            out = self._fallback.generate(
                prompt,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
                metadata={**(metadata or {}), "fallback_reason": str(exc)},
            )
            out["provider"] = "anthropic"
            out["fallback"] = True
            out["error"] = str(exc)
            return out

    def structured_generate(
        self,
        prompt: str,
        *,
        schema: dict[str, Any] | None = None,
        system: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        schema = schema or {"type": "object", "properties": {"summary": {"type": "string"}}}
        guided = (
            f"{prompt}\n\nReturn ONLY valid JSON matching this schema:\n"
            f"{json.dumps(schema)}"
        )
        raw = self.generate(guided, system=system or "Return JSON only.", metadata=metadata)
        text = str(raw.get("text") or "")
        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                data = {"value": data}
        except Exception:
            data = self._fallback.structured_generate(
                prompt, schema=schema, system=system, metadata=metadata
            ).get("data", {"summary": text})
        return {
            "provider": "anthropic",
            "mode": "structured_generate",
            "data": data,
            "schema": schema,
            "generated_at": utc_now_iso(),
            "metadata": dict(metadata or {}),
            "fallback": bool(raw.get("fallback")),
            "raw": raw,
        }

    def validate_response(self, response: dict[str, Any]) -> dict[str, object]:
        return self._fallback.validate_response(response)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = self.config.base_url.rstrip("/") + path
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url,
            data=body,
            headers={
                "x-api-key": self._api_key(),
                "anthropic-version": os.getenv("ANTHROPIC_VERSION", "2023-06-01"),
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=20) as resp:  # noqa: S310
                return json.loads(resp.read().decode("utf-8"))
        except error.URLError as exc:
            raise RuntimeError(f"Anthropic request failed: {exc}") from exc
