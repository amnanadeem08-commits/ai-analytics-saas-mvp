from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.deps import map_app_error
from backend.rag.indexing_service import delete_index, get_index_status, index_dataset
from backend.rag.retrieval_service import retrieve_chunks
from backend.rag.schemas import (
    RagDeleteResponse,
    RagIndexRequest,
    RagIndexResponse,
    RagRetrieveRequest,
    RagRetrieveResponse,
    RagStatusResponse,
)

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/{dataset_id}/index", response_model=RagIndexResponse)
def index_rag_dataset(dataset_id: str, payload: RagIndexRequest | None = None):
    try:
        request = payload or RagIndexRequest()
        return index_dataset(dataset_id, rebuild=request.rebuild, max_row_samples=request.max_row_samples)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.get("/{dataset_id}/status", response_model=RagStatusResponse)
def rag_status(dataset_id: str):
    try:
        return get_index_status(dataset_id)
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.post("/{dataset_id}/retrieve", response_model=RagRetrieveResponse)
def retrieve_rag(dataset_id: str, payload: RagRetrieveRequest):
    try:
        return retrieve_chunks(dataset_id, query=payload.query, k=payload.k, chunk_types=payload.chunk_types)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.delete("/{dataset_id}/index", response_model=RagDeleteResponse)
def delete_rag_index(dataset_id: str):
    try:
        return delete_index(dataset_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise map_app_error(exc) from exc
