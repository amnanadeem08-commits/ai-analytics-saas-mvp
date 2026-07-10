from __future__ import annotations

"""LLM provider adapters.

Providers are optional and environment-configured.
They never hardcode API keys and fail safely when unavailable.
"""

from backend.services.providers.anthropic_provider import AnthropicProvider
from backend.services.providers.local_provider import LocalProvider
from backend.services.providers.openai_provider import OpenAIProvider

__all__ = ["AnthropicProvider", "LocalProvider", "OpenAIProvider"]
