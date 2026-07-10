from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from frontend.api.analyst_client import AnalystClient
from frontend.api.base import ApiClient, ApiError, friendly_api_error
from frontend.api.evaluation_client import EvaluationClient
from frontend.api.knowledge_client import KnowledgeClient
from frontend.api.system_client import SystemClient
from frontend.api.workflow_client import WorkflowClient


def test_api_client_v1_prefix():
    client = ApiClient(base_url="http://example.test")
    assert client.v1("/health") == "/api/v1/health"
    assert client.v1("capabilities") == "/api/v1/capabilities"


def test_friendly_api_error_from_api_error():
    err = ApiError("Validation failed", status_code=422, details={"field": "query"})
    assert friendly_api_error(err) == "Validation failed"


@patch("frontend.api.base.requests.request")
def test_analyst_client_analyze_posts_v1(mock_request):
    response = MagicMock()
    response.status_code = 200
    response.content = b'{"success": true, "answer": "ok", "session_id": "s1"}'
    response.json.return_value = {"success": True, "answer": "ok", "session_id": "s1"}
    mock_request.return_value = response

    api = ApiClient(base_url="http://example.test")
    client = AnalystClient(api)
    result = client.analyze("Analyze revenue", session_id="s1", follow_up=True)
    assert result["answer"] == "ok"
    args, kwargs = mock_request.call_args
    assert args[0] == "POST"
    assert args[1].endswith("/api/v1/analyst/analyze")
    assert kwargs["json"]["query"] == "Analyze revenue"
    assert kwargs["json"]["session_id"] == "s1"
    assert kwargs["json"]["follow_up"] is True


@patch("frontend.api.base.requests.request")
def test_workflow_and_evaluation_and_knowledge_paths(mock_request):
    response = MagicMock()
    response.status_code = 200
    response.content = b'{"success": true}'
    response.json.return_value = {"success": True}
    mock_request.return_value = response

    api = ApiClient(base_url="http://example.test")
    WorkflowClient(api).execute(query="Analyze revenue")
    EvaluationClient(api).by_session("sess_1")
    KnowledgeClient(api).search("revenue")
    SystemClient(api).health()

    paths = [call.args[1] for call in mock_request.call_args_list]
    assert any(p.endswith("/api/v1/workflow/execute") for p in paths)
    assert any(p.endswith("/api/v1/evaluation/session/sess_1") for p in paths)
    assert any(p.endswith("/api/v1/knowledge/search") for p in paths)
    assert any(p.endswith("/api/v1/health") for p in paths)


@patch("frontend.api.base.requests.request")
def test_api_error_handling_no_stack(mock_request):
    response = MagicMock()
    response.status_code = 404
    response.content = b'{"success": false, "error": "Session not found"}'
    response.json.return_value = {"success": False, "error": "Session not found"}
    mock_request.return_value = response

    api = ApiClient(base_url="http://example.test")
    with pytest.raises(ApiError) as exc:
        api.get("/api/v1/session/missing")
    assert "Session not found" in str(exc.value)
    assert "Traceback" not in str(exc.value)
