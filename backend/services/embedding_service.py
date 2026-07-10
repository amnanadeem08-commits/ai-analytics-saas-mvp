from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from typing import Any

from backend.models.ai_insight_models import utc_now_iso

FUTURE_EMBEDDING_PROVIDERS: tuple[str, ...] = (
    "openai",
    "huggingface",
    "local",
)

# Fixed vocabulary seeds for deterministic mock embeddings.
_SEED_TOKENS: tuple[str, ...] = (
    "revenue",
    "kpi",
    "customer",
    "decline",
    "forecast",
    "validation",
    "governance",
    "insight",
    "sales",
    "north",
    "margin",
    "growth",
    "risk",
    "quality",
    "dataset",
    "analysis",
    "guideline",
    "business",
    "rule",
    "metric",
    "profile",
    "demand",
    "pipeline",
    "agent",
    "memory",
    "knowledge",
    "chunk",
    "document",
    "explain",
    "compliance",
)


class EmbeddingProvider(ABC):
    """Provider-agnostic embedding interface. No vendor lock-in."""

    @abstractmethod
    def create_embedding(self, text: str, *, metadata: dict[str, Any] | None = None) -> list[float]:
        """Return a dense vector for text."""

    @abstractmethod
    def similarity_score(self, left: list[float], right: list[float]) -> float:
        """Return similarity in [0, 1] (cosine mapped to unit interval)."""


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(text or "").lower())


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic local embeddings for tests and offline development."""

    def __init__(self, *, provider_id: str = "mock_embedding", dimensions: int = 32) -> None:
        self.provider_id = provider_id
        self.dimensions = max(8, int(dimensions))
        self.call_count = 0

    def create_embedding(self, text: str, *, metadata: dict[str, Any] | None = None) -> list[float]:
        self.call_count += 1
        tokens = _tokenize(text)
        vector = [0.0] * self.dimensions
        if not tokens:
            vector[0] = 1.0
            return vector

        for token in tokens:
            # Stable hash into dimensions.
            h = 0
            for ch in token:
                h = (h * 131 + ord(ch)) % 1_000_003
            idx = h % self.dimensions
            vector[idx] += 1.0
            # Boost known business vocabulary for stronger semantic clustering.
            if token in _SEED_TOKENS:
                vector[(idx + 1) % self.dimensions] += 0.75
                vector[(idx + 3) % self.dimensions] += 0.35

        # L2 normalize for stable cosine similarity.
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [round(v / norm, 8) for v in vector]

    def similarity_score(self, left: list[float], right: list[float]) -> float:
        if not left or not right:
            return 0.0
        n = min(len(left), len(right))
        if n == 0:
            return 0.0
        dot = sum(left[i] * right[i] for i in range(n))
        # Cosine already near [-1, 1] for normalized vectors; map to [0, 1].
        score = (dot + 1.0) / 2.0
        return round(max(0.0, min(1.0, score)), 8)


_DEFAULT_PROVIDER: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    global _DEFAULT_PROVIDER
    if _DEFAULT_PROVIDER is None:
        _DEFAULT_PROVIDER = MockEmbeddingProvider()
    return _DEFAULT_PROVIDER


def set_embedding_provider(provider: EmbeddingProvider) -> EmbeddingProvider:
    global _DEFAULT_PROVIDER
    _DEFAULT_PROVIDER = provider
    return provider


def reset_embedding_provider() -> EmbeddingProvider:
    return set_embedding_provider(MockEmbeddingProvider())


def create_embedding(text: str, **kwargs: Any) -> list[float]:
    return get_embedding_provider().create_embedding(text, **kwargs)


def similarity_score(left: list[float], right: list[float]) -> float:
    return get_embedding_provider().similarity_score(left, right)
