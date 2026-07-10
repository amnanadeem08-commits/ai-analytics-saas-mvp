from __future__ import annotations

from typing import Any

from frontend.api.base import ApiClient


class KnowledgeClient:
    """HTTP client for knowledge endpoints under `/api/v1`."""

    def __init__(self, client: ApiClient):
        self._client = client

    def ingest(
        self,
        *,
        title: str,
        content: str,
        source: str = "text",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        document_id: str | None = None,
        index: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "title": title,
            "content": content,
            "source": source,
            "tags": tags or [],
            "metadata": metadata or {},
            "index": index,
        }
        if document_id:
            payload["document_id"] = document_id
        return self._client.post(self._client.v1("/knowledge/ingest"), json=payload)

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        agent_name: str = "",
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._client.post(
            self._client.v1("/knowledge/search"),
            json={
                "query": query,
                "top_k": top_k,
                "agent_name": agent_name,
                "filters": filters or {},
            },
        )

    def list_documents(self) -> dict[str, Any]:
        return self._client.get(self._client.v1("/knowledge/documents"))

    def delete(self, document_id: str) -> dict[str, Any]:
        return self._client.delete(self._client.v1(f"/knowledge/{document_id}"))
