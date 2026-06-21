from __future__ import annotations

from typing import Any

from backend.core.config import settings
from backend.rag.embeddings import DEFAULT_EMBEDDING_MODEL, get_embedding_model
from backend.rag.schemas import RagChunk

COLLECTION_NAME = "analytics_chunks"
VECTOR_STORE_PATH = settings.DATA_DIR / "vector_store" / "chroma"


def _json_scalar(value: Any) -> str | int | float | bool | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _chroma_metadata(chunk: RagChunk) -> dict[str, Any]:
    metadata = {key: _json_scalar(value) for key, value in chunk.metadata.items()}
    metadata.update({"dataset_id": chunk.dataset_id, "chunk_type": chunk.chunk_type})
    return metadata


class ChromaVectorStore:
    def __init__(self):
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError("chromadb is required for RAG indexing. Install dependencies from requirements.txt.") from exc
        VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(VECTOR_STORE_PATH))
        self.collection = self.client.get_or_create_collection(name=COLLECTION_NAME)

    def upsert_chunks(self, chunks: list[RagChunk], model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        if not chunks:
            return
        embeddings = get_embedding_model(model_name).embed_documents([chunk.text for chunk in chunks])
        self.collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            embeddings=embeddings,
            metadatas=[_chroma_metadata(chunk) for chunk in chunks],
        )

    def delete_dataset(self, dataset_id: str) -> None:
        self.collection.delete(where={"dataset_id": dataset_id})

    def query_dataset(
        self,
        dataset_id: str,
        query: str,
        k: int,
        chunk_types: list[str] | None = None,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
    ) -> list[dict[str, Any]]:
        where: dict[str, Any] = {"dataset_id": dataset_id}
        if chunk_types:
            where = {"$and": [{"dataset_id": dataset_id}, {"chunk_type": {"$in": chunk_types}}]}
        embedding = get_embedding_model(model_name).embed_query(query)
        result = self.collection.query(
            query_embeddings=[embedding],
            n_results=k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        rows: list[dict[str, Any]] = []
        for chunk_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
            distance_value = float(distance) if distance is not None else None
            rows.append(
                {
                    "chunk_id": chunk_id,
                    "dataset_id": metadata.get("dataset_id", dataset_id),
                    "chunk_type": metadata.get("chunk_type", "unknown"),
                    "text": document or "",
                    "metadata": dict(metadata or {}),
                    "distance": distance_value,
                    "score": 1.0 / (1.0 + distance_value) if distance_value is not None else 0.0,
                }
            )
        return rows
