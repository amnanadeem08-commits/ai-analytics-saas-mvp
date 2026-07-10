from __future__ import annotations

from typing import Any

from frontend.api.base import ApiClient


class StorageClient:
    """HTTP client for storage endpoints under `/api/v1/storage`."""

    def __init__(self, client: ApiClient):
        self._client = client

    @staticmethod
    def _auth(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"} if token else {}

    def upload(
        self,
        token: str,
        *,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        artifact_type: str = "temporary_upload",
        organization_id: str = "",
        workspace_id: str = "",
        object_id: str | None = None,
        allow_duplicate: bool = True,
    ) -> dict[str, Any]:
        files = {"file": (filename, content, content_type)}
        params: dict[str, Any] = {
            "artifact_type": artifact_type,
            "organization_id": organization_id,
            "workspace_id": workspace_id,
            "allow_duplicate": allow_duplicate,
        }
        if object_id:
            params["object_id"] = object_id
        return self._client.post(
            self._client.v1("/storage/upload"),
            files=files,
            params=params,
            headers=self._auth(token),
            timeout=self._client._TIMEOUT_UPLOAD,
        )

    def list_files(
        self,
        token: str,
        *,
        artifact_type: str | None = None,
        status: str | None = None,
        mine: bool = False,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"mine": mine}
        if artifact_type:
            params["artifact_type"] = artifact_type
        if status:
            params["status"] = status
        return self._client.get(self._client.v1("/storage/files"), params=params, headers=self._auth(token))

    def get(self, token: str, object_id: str) -> dict[str, Any]:
        return self._client.get(self._client.v1(f"/storage/{object_id}"), headers=self._auth(token))

    def download(self, token: str, object_id: str, *, version: int | None = None) -> dict[str, Any]:
        params = {"version": version} if version is not None else None
        return self._client.get(
            self._client.v1(f"/storage/{object_id}/download"),
            params=params,
            headers=self._auth(token),
            timeout=self._client._TIMEOUT_SLOW,
        )

    def delete(self, token: str, object_id: str) -> dict[str, Any]:
        return self._client.delete(self._client.v1(f"/storage/{object_id}"), headers=self._auth(token))

    def archive(self, token: str, object_id: str) -> dict[str, Any]:
        return self._client.post(self._client.v1(f"/storage/{object_id}/archive"), headers=self._auth(token))

    def restore(self, token: str, object_id: str) -> dict[str, Any]:
        return self._client.post(self._client.v1(f"/storage/{object_id}/restore"), headers=self._auth(token))

    def rollback(self, token: str, object_id: str, *, version_number: int) -> dict[str, Any]:
        return self._client.post(
            self._client.v1(f"/storage/{object_id}/rollback"),
            json={"version_number": version_number},
            headers=self._auth(token),
        )

    def verify(self, token: str, object_id: str, *, version: int | None = None) -> dict[str, Any]:
        params = {"version": version} if version is not None else None
        return self._client.post(
            self._client.v1(f"/storage/{object_id}/verify"),
            params=params,
            headers=self._auth(token),
        )

    def statistics(self, token: str) -> dict[str, Any]:
        return self._client.get(self._client.v1("/storage/statistics"), headers=self._auth(token))
