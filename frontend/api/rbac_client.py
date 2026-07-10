from __future__ import annotations

from typing import Any

from frontend.api.base import ApiClient


class RBACClient:
    """HTTP client for RBAC endpoints under `/api/v1`."""

    def __init__(self, client: ApiClient):
        self._client = client

    @staticmethod
    def _auth(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"} if token else {}

    def list_roles(self, token: str) -> dict[str, Any]:
        return self._client.get(self._client.v1("/roles"), headers=self._auth(token))

    def list_permissions(self, token: str) -> dict[str, Any]:
        return self._client.get(self._client.v1("/permissions"), headers=self._auth(token))

    def assign_role(
        self,
        token: str,
        *,
        user_id: str,
        role_id: str,
        scope: str = "organization",
        organization_id: str = "",
        workspace_id: str = "",
    ) -> dict[str, Any]:
        return self._client.post(
            self._client.v1("/roles/assign"),
            json={
                "user_id": user_id,
                "role_id": role_id,
                "scope": scope,
                "organization_id": organization_id,
                "workspace_id": workspace_id,
            },
            headers=self._auth(token),
        )

    def remove_role(self, token: str, assignment_id: str) -> dict[str, Any]:
        return self._client.post(
            self._client.v1("/roles/remove"),
            json={"assignment_id": assignment_id},
            headers=self._auth(token),
        )

    def check_access(
        self,
        token: str,
        *,
        permission: str,
        organization_id: str = "",
        workspace_id: str = "",
    ) -> dict[str, Any]:
        return self._client.get(
            self._client.v1("/access/check"),
            params={
                "permission": permission,
                "organization_id": organization_id,
                "workspace_id": workspace_id,
            },
            headers=self._auth(token),
        )
