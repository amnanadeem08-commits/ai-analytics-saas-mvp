from __future__ import annotations

from typing import Any

from frontend.api.base import ApiClient


class OrganizationClient:
    """HTTP client for organization + membership endpoints under `/api/v1`."""

    def __init__(self, client: ApiClient):
        self._client = client

    @staticmethod
    def _auth(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"} if token else {}

    def create(self, token: str, name: str, *, slug: str = "", settings: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._client.post(
            self._client.v1("/organizations"),
            json={"name": name, "slug": slug, "settings": settings or {}},
            headers=self._auth(token),
        )

    def list(self, token: str, *, include_archived: bool = True) -> dict[str, Any]:
        return self._client.get(
            self._client.v1("/organizations"),
            params={"include_archived": include_archived},
            headers=self._auth(token),
        )

    def get(self, token: str, organization_id: str) -> dict[str, Any]:
        return self._client.get(
            self._client.v1(f"/organizations/{organization_id}"),
            headers=self._auth(token),
        )

    def update(self, token: str, organization_id: str, *, name: str | None = None, settings: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._client.request(
            "PUT",
            self._client.v1(f"/organizations/{organization_id}"),
            json={"name": name, "settings": settings},
            headers=self._auth(token),
        )

    def archive(self, token: str, organization_id: str) -> dict[str, Any]:
        return self._client.delete(
            self._client.v1(f"/organizations/{organization_id}"),
            headers=self._auth(token),
        )

    def invite(self, token: str, organization_id: str, email: str, *, role_id: str = "member") -> dict[str, Any]:
        return self._client.post(
            self._client.v1(f"/organizations/{organization_id}/invite"),
            json={"email": email, "role_id": role_id},
            headers=self._auth(token),
        )

    def accept_invitation(self, token: str, invitation_token: str) -> dict[str, Any]:
        return self._client.post(
            self._client.v1("/organizations/invitations/accept"),
            json={"token": invitation_token},
            headers=self._auth(token),
        )

    def decline_invitation(self, token: str, invitation_token: str) -> dict[str, Any]:
        return self._client.post(
            self._client.v1("/organizations/invitations/decline"),
            json={"token": invitation_token},
            headers=self._auth(token),
        )

    def list_members(self, token: str, organization_id: str) -> dict[str, Any]:
        return self._client.get(
            self._client.v1(f"/organizations/{organization_id}/members"),
            headers=self._auth(token),
        )

    def remove_member(self, token: str, organization_id: str, member_user_id: str) -> dict[str, Any]:
        return self._client.delete(
            self._client.v1(f"/organizations/{organization_id}/members/{member_user_id}"),
            headers=self._auth(token),
        )

    def transfer_ownership(self, token: str, organization_id: str, new_owner_id: str) -> dict[str, Any]:
        return self._client.post(
            self._client.v1(f"/organizations/{organization_id}/transfer-ownership"),
            json={"new_owner_id": new_owner_id},
            headers=self._auth(token),
        )
