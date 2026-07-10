from __future__ import annotations

from typing import Any

from frontend.api.base import ApiClient


class WorkflowClient:
    """HTTP client for workflow endpoints under `/api/v1`."""

    def __init__(self, client: ApiClient):
        self._client = client

    def execute(
        self,
        *,
        query: str | None = None,
        workflow_name: str = "Intelligence Pipeline",
        stage_ids: list[str] | None = None,
        initial_context: dict[str, Any] | None = None,
        dataset_id: str | None = None,
        domain: str | None = None,
        include_evaluation: bool = True,
        stop_on_error: bool = True,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "workflow_name": workflow_name,
            "initial_context": initial_context or {},
            "include_evaluation": include_evaluation,
            "stop_on_error": stop_on_error,
        }
        if query:
            payload["query"] = query
        if stage_ids is not None:
            payload["stage_ids"] = stage_ids
        if dataset_id:
            payload["dataset_id"] = dataset_id
        if domain:
            payload["domain"] = domain
        return self._client.post(
            self._client.v1("/workflow/execute"),
            json=payload,
            timeout=self._client._TIMEOUT_SLOW,
        )

    def status(self, execution_id: str) -> dict[str, Any]:
        return self._client.get(self._client.v1(f"/workflow/status/{execution_id}"))

    def results(self, execution_id: str) -> dict[str, Any]:
        return self._client.get(self._client.v1(f"/workflow/results/{execution_id}"))

    def statistics(self, execution_id: str | None = None) -> dict[str, Any]:
        params = {"execution_id": execution_id} if execution_id else None
        return self._client.get(self._client.v1("/workflow/statistics"), params=params)
