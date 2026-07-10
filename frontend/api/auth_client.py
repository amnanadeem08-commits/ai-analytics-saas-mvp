from __future__ import annotations

from typing import Any

from frontend.api.base import ApiClient


class AuthClient:
    """HTTP client for authentication endpoints under `/api/v1/auth`."""

    def __init__(self, client: ApiClient):
        self._client = client

    def register(
        self,
        email: str,
        password: str,
        *,
        full_name: str = "",
        profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._client.post(
            self._client.v1("/auth/register"),
            json={
                "email": email,
                "password": password,
                "full_name": full_name,
                "profile": profile or {},
            },
        )

    def login(self, email: str, password: str) -> dict[str, Any]:
        return self._client.post(
            self._client.v1("/auth/login"),
            json={"email": email, "password": password},
        )

    def refresh(self, refresh_token: str) -> dict[str, Any]:
        return self._client.post(
            self._client.v1("/auth/refresh"),
            json={"refresh_token": refresh_token},
        )

    def logout(self, *, access_token: str, refresh_token: str = "", session_id: str = "") -> dict[str, Any]:
        return self._client.post(
            self._client.v1("/auth/logout"),
            json={"refresh_token": refresh_token, "session_id": session_id},
            headers=_bearer(access_token),
        )

    def me(self, access_token: str) -> dict[str, Any]:
        return self._client.get(
            self._client.v1("/auth/me"),
            headers=_bearer(access_token),
        )

    def change_password(self, access_token: str, current_password: str, new_password: str) -> dict[str, Any]:
        return self._client.post(
            self._client.v1("/auth/change-password"),
            json={"current_password": current_password, "new_password": new_password},
            headers=_bearer(access_token),
        )

    def request_password_reset(self, email: str) -> dict[str, Any]:
        return self._client.post(
            self._client.v1("/auth/request-password-reset"),
            json={"email": email},
        )

    def reset_password(self, token: str, new_password: str) -> dict[str, Any]:
        return self._client.post(
            self._client.v1("/auth/reset-password"),
            json={"token": token, "new_password": new_password},
        )

    def verify_email(self, token: str) -> dict[str, Any]:
        return self._client.post(
            self._client.v1("/auth/verify-email"),
            json={"token": token},
        )

    def update_profile(self, access_token: str, profile: dict[str, Any]) -> dict[str, Any]:
        return self._client.request(
            "PUT",
            self._client.v1("/auth/me/profile"),
            json=profile,
            headers=_bearer(access_token),
        )

    def list_sessions(self, access_token: str) -> dict[str, Any]:
        return self._client.get(
            self._client.v1("/auth/sessions"),
            headers=_bearer(access_token),
        )


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}
