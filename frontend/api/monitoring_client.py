from __future__ import annotations

from typing import Any

from frontend.api.base import ApiClient


class MonitoringClient:
    """HTTP client for monitoring endpoints under `/api/v1`."""

    def __init__(self, client: ApiClient):
        self._client = client

    @staticmethod
    def _auth(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"} if token else {}

    def health(self, token: str = "") -> dict[str, Any]:
        return self._client.get(self._client.v1("/monitoring/health"), headers=self._auth(token))

    def ready(self, token: str = "") -> dict[str, Any]:
        return self._client.get(self._client.v1("/ready"), headers=self._auth(token))

    def live(self, token: str = "") -> dict[str, Any]:
        return self._client.get(self._client.v1("/live"), headers=self._auth(token))

    def metrics(self, token: str = "") -> dict[str, Any]:
        return self._client.get(self._client.v1("/metrics"), headers=self._auth(token))

    def system_status(self, token: str = "") -> dict[str, Any]:
        return self._client.get(self._client.v1("/system/status"), headers=self._auth(token))

    def system_config(self, token: str = "") -> dict[str, Any]:
        return self._client.get(self._client.v1("/system/config"), headers=self._auth(token))

    def dependencies(self, token: str = "") -> dict[str, Any]:
        return self._client.get(self._client.v1("/system/dependencies"), headers=self._auth(token))

    def legacy_health(self) -> dict[str, Any]:
        return self._client.get("/health")
