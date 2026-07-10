from __future__ import annotations

from typing import Any

from frontend.api.base import ApiClient


class AdminClient:
    def __init__(self, client: ApiClient):
        self._client = client

    @staticmethod
    def _auth(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"} if token else {}

    def dashboard(self, token: str) -> dict[str, Any]:
        return self._client.get(self._client.v1("/admin/dashboard"), headers=self._auth(token))

    def statistics(self, token: str) -> dict[str, Any]:
        return self._client.get(self._client.v1("/admin/statistics"), headers=self._auth(token))

    def users(self, token: str) -> dict[str, Any]:
        return self._client.get(self._client.v1("/admin/users"), headers=self._auth(token))

    def organizations(self, token: str) -> dict[str, Any]:
        return self._client.get(self._client.v1("/admin/organizations"), headers=self._auth(token))

    def usage(self, token: str, *, organization_id: str | None = None) -> dict[str, Any]:
        params = {"organization_id": organization_id} if organization_id else None
        return self._client.get(self._client.v1("/admin/usage"), params=params, headers=self._auth(token))

    def audit(self, token: str, *, limit: int = 50) -> dict[str, Any]:
        return self._client.get(self._client.v1("/admin/audit"), params={"limit": limit}, headers=self._auth(token))

    def features(self, token: str) -> dict[str, Any]:
        return self._client.get(self._client.v1("/admin/features"), headers=self._auth(token))
