from __future__ import annotations

from typing import Any

from frontend.api.base import ApiClient


class WorkspaceClient:
    """HTTP client for workspace endpoints under `/api/v1/workspaces`."""

    def __init__(self, client: ApiClient):
        self._client = client

    @staticmethod
    def _auth(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"} if token else {}

    def create(self, token: str, organization_id: str, name: str, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._client.post(
            self._client.v1("/workspaces"),
            json={"organization_id": organization_id, "name": name, "metadata": metadata or {}},
            headers=self._auth(token),
        )

    def list(self, token: str, organization_id: str, *, include_archived: bool = True) -> dict[str, Any]:
        return self._client.get(
            self._client.v1("/workspaces"),
            params={"organization_id": organization_id, "include_archived": include_archived},
            headers=self._auth(token),
        )

    def get(self, token: str, workspace_id: str) -> dict[str, Any]:
        return self._client.get(
            self._client.v1(f"/workspaces/{workspace_id}"),
            headers=self._auth(token),
        )

    def update(self, token: str, workspace_id: str, *, name: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._client.request(
            "PUT",
            self._client.v1(f"/workspaces/{workspace_id}"),
            json={"name": name, "metadata": metadata},
            headers=self._auth(token),
        )

    def archive(self, token: str, workspace_id: str) -> dict[str, Any]:
        return self._client.delete(
            self._client.v1(f"/workspaces/{workspace_id}"),
            headers=self._auth(token),
        )

    def restore(self, token: str, workspace_id: str) -> dict[str, Any]:
        return self._client.post(
            self._client.v1(f"/workspaces/{workspace_id}/restore"),
            headers=self._auth(token),
        )

    def members(self, token: str, workspace_id: str) -> dict[str, Any]:
        return self._client.get(
            self._client.v1(f"/workspaces/{workspace_id}/members"),
            headers=self._auth(token),
        )
