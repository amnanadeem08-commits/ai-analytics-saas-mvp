from __future__ import annotations

from functools import lru_cache

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class LocalEmbeddingModel:
    """Small wrapper around SentenceTransformers with lazy optional dependency loading."""

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for RAG indexing. Install dependencies from requirements.txt."
            ) from exc
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return vectors.tolist()

    def embed_query(self, query: str) -> list[float]:
        return self.embed_documents([query])[0]


@lru_cache(maxsize=1)
def get_embedding_model(model_name: str = DEFAULT_EMBEDDING_MODEL) -> LocalEmbeddingModel:
    return LocalEmbeddingModel(model_name=model_name)
