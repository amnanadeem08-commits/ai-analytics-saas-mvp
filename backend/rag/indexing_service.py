from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.core.config import settings
from backend.rag.chunking import build_rag_chunks
from backend.rag.embeddings import DEFAULT_EMBEDDING_MODEL
from backend.rag.vector_store import COLLECTION_NAME, VECTOR_STORE_PATH, ChromaVectorStore
from backend.services.dataset_service import get_dataset_metadata, load_dataset_dataframe

RAG_INDEXES_DIR = settings.DATA_DIR / "rag_indexes"


def dataset_index_dir(dataset_id: str) -> Path:
    return RAG_INDEXES_DIR / dataset_id


def index_meta_path(dataset_id: str) -> Path:
    return dataset_index_dir(dataset_id) / "index_meta.json"


def load_index_meta(dataset_id: str) -> dict[str, Any] | None:
    path = index_meta_path(dataset_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def get_index_status(dataset_id: str) -> dict[str, Any]:
    get_dataset_metadata(dataset_id)
    meta = load_index_meta(dataset_id)
    if not meta:
        return {"dataset_id": dataset_id, "indexed": False, "status": "not_indexed", "chunk_count": 0, "collection": COLLECTION_NAME}
    return {
        "dataset_id": dataset_id,
        "indexed": meta.get("status") == "indexed",
        "status": meta.get("status", "unknown"),
        "chunk_count": int(meta.get("chunk_count", 0)),
        "collection": meta.get("collection", COLLECTION_NAME),
        "embedding_model": meta.get("embedding_model"),
        "index_path": str(index_meta_path(dataset_id).as_posix()),
        "last_indexed_at": meta.get("last_indexed_at"),
        "metadata": meta,
    }


def index_dataset(dataset_id: str, rebuild: bool = False, max_row_samples: int = 20) -> dict[str, Any]:
    metadata = get_dataset_metadata(dataset_id)
    existing = load_index_meta(dataset_id)
    if existing and existing.get("status") == "indexed" and not rebuild:
        return {
            "dataset_id": dataset_id,
            "status": "indexed",
            "chunk_count": int(existing.get("chunk_count", 0)),
            "collection": existing.get("collection", COLLECTION_NAME),
            "embedding_model": existing.get("embedding_model", DEFAULT_EMBEDDING_MODEL),
            "index_path": str(index_meta_path(dataset_id).as_posix()),
            "message": "Dataset is already indexed. Pass rebuild=true to rebuild.",
        }

    df = load_dataset_dataframe(dataset_id)
    chunks = build_rag_chunks(dataset_id, df, max_row_samples=max_row_samples)
    store = ChromaVectorStore()
    if rebuild or existing:
        store.delete_dataset(dataset_id)
    store.upsert_chunks(chunks)

    dataset_index_dir(dataset_id).mkdir(parents=True, exist_ok=True)
    meta = {
        "dataset_id": dataset_id,
        "status": "indexed",
        "chunk_count": len(chunks),
        "collection": COLLECTION_NAME,
        "embedding_model": DEFAULT_EMBEDDING_MODEL,
        "vector_store_path": str(VECTOR_STORE_PATH.as_posix()),
        "index_path": str(index_meta_path(dataset_id).as_posix()),
        "last_indexed_at": datetime.now(timezone.utc).isoformat(),
        "source_dataset": {
            "original_filename": metadata.get("original_filename"),
            "row_count": metadata.get("row_count"),
            "column_count": metadata.get("column_count"),
            "file_hash": metadata.get("file_hash"),
        },
        "chunk_types": sorted({chunk.chunk_type for chunk in chunks}),
        "max_row_samples": max_row_samples,
    }
    index_meta_path(dataset_id).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {
        "dataset_id": dataset_id,
        "status": "indexed",
        "chunk_count": len(chunks),
        "collection": COLLECTION_NAME,
        "embedding_model": DEFAULT_EMBEDDING_MODEL,
        "index_path": str(index_meta_path(dataset_id).as_posix()),
        "message": "Dataset indexed for retrieval.",
    }


def delete_index(dataset_id: str) -> dict[str, Any]:
    get_dataset_metadata(dataset_id)
    meta_path = index_meta_path(dataset_id)
    deleted = False
    try:
        ChromaVectorStore().delete_dataset(dataset_id)
        deleted = True
    except RuntimeError:
        if not meta_path.exists():
            raise
    if meta_path.exists():
        meta_path.unlink()
        deleted = True
    index_dir = dataset_index_dir(dataset_id)
    if index_dir.exists() and not any(index_dir.iterdir()):
        index_dir.rmdir()
    return {"dataset_id": dataset_id, "deleted": deleted, "message": "RAG index deleted." if deleted else "No RAG index found."}
