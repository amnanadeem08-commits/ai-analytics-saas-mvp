from __future__ import annotations

from typing import Any

from frontend.api.base import ApiClient


class JobClient:
    """HTTP client for job endpoints under `/api/v1/jobs`."""

    def __init__(self, client: ApiClient):
        self._client = client

    @staticmethod
    def _auth(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"} if token else {}

    def submit(
        self,
        token: str,
        *,
        job_type: str,
        payload: dict[str, Any] | None = None,
        priority: str = "normal",
        inline: bool = False,
    ) -> dict[str, Any]:
        return self._client.post(
            self._client.v1("/jobs"),
            json={
                "job_type": job_type,
                "payload": payload or {},
                "priority": priority,
                "inline": inline,
            },
            headers=self._auth(token),
            timeout=self._client._TIMEOUT_SLOW,
        )

    def get(self, token: str, job_id: str) -> dict[str, Any]:
        return self._client.get(self._client.v1(f"/jobs/{job_id}"), headers=self._auth(token))

    def list(self, token: str, *, status: str | None = None, job_type: str | None = None, mine: bool = False) -> dict[str, Any]:
        params: dict[str, Any] = {"mine": mine}
        if status:
            params["status"] = status
        if job_type:
            params["job_type"] = job_type
        return self._client.get(self._client.v1("/jobs"), params=params, headers=self._auth(token))

    def statistics(self, token: str) -> dict[str, Any]:
        return self._client.get(self._client.v1("/jobs/statistics"), headers=self._auth(token))

    def cancel(self, token: str, job_id: str) -> dict[str, Any]:
        return self._client.delete(self._client.v1(f"/jobs/{job_id}"), headers=self._auth(token))

    def retry(self, token: str, job_id: str, *, inline: bool = False) -> dict[str, Any]:
        return self._client.post(
            self._client.v1(f"/jobs/{job_id}/retry"),
            params={"inline": inline},
            headers=self._auth(token),
            timeout=self._client._TIMEOUT_SLOW,
        )
