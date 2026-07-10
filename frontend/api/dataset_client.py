from __future__ import annotations

"""Dataset HTTP helpers for the workspace (legacy upload/dataset routes via HTTP only)."""

from typing import Any

from frontend.api.base import ApiClient


class DatasetClient:
    """HTTP client for dataset upload/preview endpoints (existing FastAPI routes)."""

    def __init__(self, client: ApiClient):
        self._client = client

    def list_datasets(self) -> list[dict[str, Any]]:
        data = self._client.get("/datasets")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return list(data.get("datasets") or data.get("items") or [])
        return []

    def overview(self, dataset_id: str) -> dict[str, Any]:
        return self._client.get(f"/datasets/{dataset_id}/overview")

    def preview(self, dataset_id: str, *, limit: int = 20) -> dict[str, Any]:
        return self._client.get(f"/datasets/{dataset_id}/preview", params={"limit": limit})

    def status(self, dataset_id: str) -> dict[str, Any]:
        return self._client.get(f"/datasets/{dataset_id}/status")

    def upload(self, filename: str, content: bytes, content_type: str = "text/csv") -> dict[str, Any]:
        files = {"file": (filename, content, content_type)}
        return self._client.post(
            "/upload",
            files=files,
            timeout=self._client._TIMEOUT_UPLOAD,
        )
