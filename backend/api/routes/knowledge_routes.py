from __future__ import annotations

from fastapi import APIRouter, status

from backend.api.dependencies import get_knowledge_ingestion, get_rag_service
from backend.api.error_handlers import map_service_exception, raise_api_error
from backend.api.models.knowledge import (
    KnowledgeDocumentRequest,
    KnowledgeDocumentResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)

router = APIRouter(prefix="/api/v1", tags=["Knowledge"])


@router.post(
    "/knowledge/ingest",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a knowledge document",
    description="Validates, chunks, and indexes a knowledge document via the RAG ingestion service.",
    responses={
        201: {"description": "Document ingested"},
        400: {"description": "Invalid document"},
    },
)
def ingest_knowledge(request: KnowledgeDocumentRequest) -> KnowledgeDocumentResponse:
    try:
        if not request.storage_object_id and not str(request.content or "").strip():
            raise_api_error(400, "content or storage_object_id is required")
        knowledge = get_knowledge_ingestion()
        doc, chunks = knowledge.ingest_document(
            title=request.title,
            content=request.content,
            source=request.source,
            tags=request.tags,
            metadata=request.metadata,
            document_id=request.document_id,
            index=request.index,
            storage_object_id=request.storage_object_id,
        )
        return KnowledgeDocumentResponse(
            success=True,
            document_id=doc.document_id,
            title=doc.title,
            source=doc.source,
            chunk_count=len(chunks),
            tags=list(doc.tags),
            created_at=doc.created_at,
            metadata=dict(doc.metadata or {}),
        )
    except Exception as exc:
        raise map_service_exception(exc) from exc


@router.post(
    "/knowledge/search",
    response_model=KnowledgeSearchResponse,
    summary="Search knowledge base",
    description="Semantic retrieval over ingested knowledge using the RAG service.",
    responses={200: {"description": "Search results"}},
)
def search_knowledge(request: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
    try:
        rag = get_rag_service()
        result = rag.retrieve_knowledge(
            request.query,
            agent_name=request.agent_name,
            top_k=request.top_k,
            filters=request.filters or None,
        )
        chunks = []
        for chunk, score in zip(result.chunks, result.relevance_scores, strict=False):
            chunks.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "content": chunk.content,
                    "relevance": score,
                    "metadata": dict(chunk.metadata or {}),
                }
            )
        return KnowledgeSearchResponse(
            success=True,
            query=result.query,
            chunk_count=len(chunks),
            sources=list(result.sources),
            chunks=chunks,
            relevance_scores=list(result.relevance_scores),
            metadata=dict(result.metadata or {}),
        )
    except Exception as exc:
        raise map_service_exception(exc) from exc


@router.get(
    "/knowledge/documents",
    summary="List knowledge documents",
    description="Lists ingested knowledge documents (metadata only).",
    responses={200: {"description": "Document list"}},
)
def list_knowledge_documents() -> dict:
    try:
        knowledge = get_knowledge_ingestion()
        docs = knowledge.list_documents()
        return {
            "success": True,
            "count": len(docs),
            "documents": [
                {
                    "document_id": d.document_id,
                    "title": d.title,
                    "source": d.source,
                    "tags": list(d.tags),
                    "created_at": d.created_at,
                }
                for d in docs
            ],
            "summary": knowledge.knowledge_summary(),
        }
    except Exception as exc:
        raise map_service_exception(exc) from exc


@router.delete(
    "/knowledge/{document_id}",
    summary="Delete a knowledge document",
    description="Removes a knowledge document and its indexed chunks.",
    responses={
        200: {"description": "Deleted"},
        404: {"description": "Not found"},
    },
)
def delete_knowledge(document_id: str) -> dict:
    try:
        knowledge = get_knowledge_ingestion()
        removed = knowledge.remove_document(document_id)
        if not removed:
            raise_api_error(404, f"Knowledge document not found: {document_id}")
        return {"success": True, "document_id": document_id, "deleted": True}
    except Exception as exc:
        if hasattr(exc, "status_code"):
            raise
        raise map_service_exception(exc) from exc
