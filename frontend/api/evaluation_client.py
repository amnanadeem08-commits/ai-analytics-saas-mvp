from __future__ import annotations

from typing import Any

from frontend.api.base import ApiClient


class EvaluationClient:
    """HTTP client for evaluation endpoints under `/api/v1`."""

    def __init__(self, client: ApiClient):
        self._client = client

    def run(self, session_id: str, *, weights: dict[str, float] | None = None) -> dict[str, Any]:
        return self._client.post(
            self._client.v1("/evaluation/run"),
            json={"session_id": session_id, "weights": weights or {}},
            timeout=self._client._TIMEOUT_SLOW,
        )

    def by_session(self, session_id: str) -> dict[str, Any]:
        return self._client.get(self._client.v1(f"/evaluation/session/{session_id}"))

    def by_workflow(self, workflow_id: str) -> dict[str, Any]:
        return self._client.get(self._client.v1(f"/evaluation/workflow/{workflow_id}"))

    def report(self, evaluation_id: str) -> dict[str, Any]:
        return self._client.get(self._client.v1(f"/evaluation/report/{evaluation_id}"))

    def export(self, evaluation_id: str) -> dict[str, Any]:
        return self._client.get(self._client.v1(f"/evaluation/export/{evaluation_id}"))
