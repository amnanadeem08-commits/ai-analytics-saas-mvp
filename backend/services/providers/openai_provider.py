from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

from backend.models.ai_insight_models import utc_now_iso
from backend.models.llm_models import LLMProviderConfig
from backend.services.llm_service import LLMProvider, MockLLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible adapter. No mandatory network calls; fails safely if unavailable."""

    def __init__(self, config: LLMProviderConfig | None = None) -> None:
        self.config = config or LLMProviderConfig(
            provider_name="openai",
            model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            api_key_env="OPENAI_API_KEY",
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            enabled=True,
        )
        self.provider_id = "openai"
        self._fallback = MockLLMProvider(provider_id="mock_openai_fallback")

    def _api_key(self) -> str:
        env_name = self.config.api_key_env or "OPENAI_API_KEY"
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
                metadata={**(metadata or {}), "fallback_reason": "openai_unavailable"},
            )
            out["provider"] = "openai"
            out["fallback"] = True
            return out
        try:
            payload = {
                "model": self.config.model_name,
                "temperature": temperature if temperature is not None else self.config.temperature,
                "max_tokens": max_tokens or self.config.max_tokens,
                "messages": (
                    ([{"role": "system", "content": system}] if system else [])
                    + [{"role": "user", "content": prompt}]
                ),
            }
            data = self._post("/chat/completions", payload)
            content = (
                (((data.get("choices") or [{}])[0]).get("message") or {}).get("content")
                or ""
            )
            return {
                "provider": "openai",
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
            out["provider"] = "openai"
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
        data: dict[str, Any]
        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                data = {"value": data}
        except Exception:
            data = self._fallback.structured_generate(
                prompt, schema=schema, system=system, metadata=metadata
            ).get("data", {"summary": text})
        return {
            "provider": "openai",
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
                "Authorization": f"Bearer {self._api_key()}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=20) as resp:  # noqa: S310 — controlled URL from config
                return json.loads(resp.read().decode("utf-8"))
        except error.URLError as exc:
            raise RuntimeError(f"OpenAI request failed: {exc}") from exc
