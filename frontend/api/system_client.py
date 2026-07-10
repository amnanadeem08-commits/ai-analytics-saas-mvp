from __future__ import annotations

from typing import Any

from frontend.api.base import ApiClient


class SystemClient:
    """HTTP client for system endpoints under `/api/v1`."""

    def __init__(self, client: ApiClient):
        self._client = client

    def health(self) -> dict[str, Any]:
        return self._client.get(self._client.v1("/health"))

    def version(self) -> dict[str, Any]:
        return self._client.get(self._client.v1("/version"))

    def capabilities(self) -> dict[str, Any]:
        return self._client.get(self._client.v1("/capabilities"))
