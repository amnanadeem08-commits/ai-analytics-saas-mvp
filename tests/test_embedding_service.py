from __future__ import annotations

from backend.services.embedding_service import (
    FUTURE_EMBEDDING_PROVIDERS,
    MockEmbeddingProvider,
    create_embedding,
    get_embedding_provider,
    reset_embedding_provider,
    set_embedding_provider,
    similarity_score,
)


def setup_function():
    reset_embedding_provider()


def test_mock_embedding_deterministic_and_similarity():
    a1 = create_embedding("customer revenue decline in north")
    a2 = create_embedding("customer revenue decline in north")
    assert a1 == a2
    assert len(a1) == 32

    similar = similarity_score(
        create_embedding("revenue kpi growth"),
        create_embedding("revenue metric growth kpi"),
    )
    dissimilar = similarity_score(
        create_embedding("revenue kpi growth"),
        create_embedding("completely unrelated astronomy nebula"),
    )
    assert similar > dissimilar
    assert 0.0 <= similar <= 1.0


def test_provider_swap():
    custom = MockEmbeddingProvider(provider_id="mock_alt", dimensions=16)
    set_embedding_provider(custom)
    vector = create_embedding("kpi")
    assert len(vector) == 16
    assert get_embedding_provider().provider_id == "mock_alt"
    assert "openai" in FUTURE_EMBEDDING_PROVIDERS
    reset_embedding_provider()
    assert get_embedding_provider().provider_id == "mock_embedding"
