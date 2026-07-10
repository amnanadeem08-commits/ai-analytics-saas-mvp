from __future__ import annotations

from typing import Any

from frontend.api.base import ApiClient


class ApiKeyClient:
    def __init__(self, client: ApiClient):
        self._client = client

    @staticmethod
    def _auth(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"} if token else {}

    def create(
        self,
        token: str,
        *,
        name: str,
        organization_id: str,
        scopes: list[str] | None = None,
        workspace_id: str = "",
    ) -> dict[str, Any]:
        return self._client.post(
            self._client.v1("/api-keys"),
            json={
                "name": name,
                "organization_id": organization_id,
                "workspace_id": workspace_id,
                "scopes": scopes or ["read"],
            },
            headers=self._auth(token),
        )

    def list(self, token: str, *, organization_id: str | None = None, mine: bool = False) -> dict[str, Any]:
        params: dict[str, Any] = {"mine": mine}
        if organization_id:
            params["organization_id"] = organization_id
        return self._client.get(self._client.v1("/api-keys"), params=params, headers=self._auth(token))

    def revoke(self, token: str, key_id: str) -> dict[str, Any]:
        return self._client.delete(self._client.v1(f"/api-keys/{key_id}"), headers=self._auth(token))

    def rotate(self, token: str, key_id: str) -> dict[str, Any]:
        return self._client.post(self._client.v1(f"/api-keys/{key_id}/rotate"), headers=self._auth(token))
