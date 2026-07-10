from __future__ import annotations

from typing import Any

from frontend.api.base import ApiClient


class AnalystClient:
    """HTTP client for AI Analyst + session endpoints under `/api/v1`."""

    def __init__(self, client: ApiClient):
        self._client = client

    def analyze(
        self,
        query: str,
        *,
        user_context: dict[str, Any] | None = None,
        session_id: str | None = None,
        follow_up: bool = False,
        initial_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "query": query,
            "user_context": user_context or {},
            "follow_up": follow_up,
            "initial_context": initial_context or {},
        }
        if session_id:
            payload["session_id"] = session_id
        return self._client.post(
            self._client.v1("/analyst/analyze"),
            json=payload,
            timeout=self._client._TIMEOUT_SLOW,
        )

    def create_session(
        self,
        query: str,
        *,
        user_context: dict[str, Any] | None = None,
        session_id: str | None = None,
        follow_up: bool = False,
    ) -> dict[str, Any]:
        payload = {
            "query": query,
            "user_context": user_context or {},
            "follow_up": follow_up,
        }
        if session_id:
            payload["session_id"] = session_id
        return self._client.post(
            self._client.v1("/session/create"),
            json=payload,
        )

    def get_session(self, session_id: str) -> dict[str, Any]:
        return self._client.get(self._client.v1(f"/session/{session_id}"))

    def session_summary(self, session_id: str) -> dict[str, Any]:
        return self._client.get(self._client.v1(f"/session/{session_id}/summary"))

    def session_evaluation(self, session_id: str) -> dict[str, Any]:
        return self._client.get(self._client.v1(f"/session/{session_id}/evaluation"))

    def execute_session(
        self,
        session_id: str,
        *,
        initial_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._client.post(
            self._client.v1(f"/session/{session_id}/execute"),
            json={"initial_context": initial_context or {}},
            timeout=self._client._TIMEOUT_SLOW,
        )
