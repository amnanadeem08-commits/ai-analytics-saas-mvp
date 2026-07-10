from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.services.embedding_service import similarity_score

FUTURE_VECTOR_BACKENDS: tuple[str, ...] = (
    "faiss",
    "chroma",
    "pinecone",
    "pgvector",
)


class VectorStore(ABC):
    """Vector store abstraction — in-memory now; FAISS/Chroma/etc. later."""

    @abstractmethod
    def add_vectors(
        self,
        ids: list[str],
        vectors: list[list[float]],
        *,
        payloads: list[dict[str, Any]] | None = None,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    def search_vectors(
        self,
        query_vector: list[float],
        *,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Return [{id, score, payload}, ...] sorted by score desc."""
        raise NotImplementedError

    @abstractmethod
    def delete_vectors(self, ids: list[str]) -> int:
        raise NotImplementedError

    @abstractmethod
    def count(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        raise NotImplementedError


class InMemoryVectorStore(VectorStore):
    """Process-local vector index. No external DB dependency."""

    def __init__(self) -> None:
        self._vectors: dict[str, list[float]] = {}
        self._payloads: dict[str, dict[str, Any]] = {}

    def add_vectors(
        self,
        ids: list[str],
        vectors: list[list[float]],
        *,
        payloads: list[dict[str, Any]] | None = None,
    ) -> int:
        if len(ids) != len(vectors):
            raise ValueError("ids and vectors length mismatch")
        payload_list = payloads or [{} for _ in ids]
        if len(payload_list) != len(ids):
            raise ValueError("payloads length mismatch")
        for item_id, vector, payload in zip(ids, vectors, payload_list, strict=True):
            self._vectors[str(item_id)] = list(vector)
            self._payloads[str(item_id)] = dict(payload or {})
        return len(ids)

    def search_vectors(
        self,
        query_vector: list[float],
        *,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        filters = filters or {}
        scored: list[dict[str, Any]] = []
        for item_id, vector in self._vectors.items():
            payload = self._payloads.get(item_id, {})
            if filters and not _payload_matches(payload, filters):
                continue
            score = similarity_score(query_vector, vector)
            scored.append({"id": item_id, "score": score, "payload": dict(payload)})
        scored.sort(key=lambda row: (-row["score"], row["id"]))
        return scored[: max(1, int(top_k))]

    def delete_vectors(self, ids: list[str]) -> int:
        removed = 0
        for item_id in ids:
            if item_id in self._vectors:
                del self._vectors[item_id]
                self._payloads.pop(item_id, None)
                removed += 1
        return removed

    def count(self) -> int:
        return len(self._vectors)

    def clear(self) -> None:
        self._vectors.clear()
        self._payloads.clear()


def _payload_matches(payload: dict[str, Any], filters: dict[str, Any]) -> bool:
    for key, expected in filters.items():
        actual = payload.get(key)
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


_STORE: VectorStore = InMemoryVectorStore()


def get_vector_store() -> VectorStore:
    return _STORE


def set_vector_store(store: VectorStore) -> VectorStore:
    global _STORE
    _STORE = store
    return store


def reset_vector_store() -> VectorStore:
    return set_vector_store(InMemoryVectorStore())


def add_vectors(
    ids: list[str],
    vectors: list[list[float]],
    *,
    payloads: list[dict[str, Any]] | None = None,
) -> int:
    return get_vector_store().add_vectors(ids, vectors, payloads=payloads)


def search_vectors(
    query_vector: list[float],
    *,
    top_k: int = 5,
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return get_vector_store().search_vectors(query_vector, top_k=top_k, filters=filters)


def delete_vectors(ids: list[str]) -> int:
    return get_vector_store().delete_vectors(ids)
