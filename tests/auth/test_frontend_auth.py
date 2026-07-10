from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

from frontend.api.auth_client import AuthClient
from frontend.api.base import ApiClient, ApiError

AUTH_FRONTEND_FILES = [
    "frontend/api/auth_client.py",
    "frontend/utils/auth_state.py",
    "frontend/app_pages/auth_pages.py",
]


def _imports_backend(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "backend" or alias.name.startswith("backend."):
                    hits.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == "backend" or mod.startswith("backend."):
                hits.append(mod)
    return hits


def test_auth_frontend_has_no_backend_imports():
    root = Path(".")
    for rel in AUTH_FRONTEND_FILES:
        path = root / rel
        assert path.exists(), f"Missing file: {rel}"
        assert _imports_backend(path) == [], f"{rel} imports backend modules"


@patch("frontend.api.base.requests.request")
def test_auth_client_login_posts_v1(mock_request):
    response = MagicMock()
    response.status_code = 200
    response.content = b'{"access_token": "a", "refresh_token": "r", "session_id": "s"}'
    response.json.return_value = {"access_token": "a", "refresh_token": "r", "session_id": "s"}
    mock_request.return_value = response

    auth = AuthClient(ApiClient(base_url="http://example.test"))
    result = auth.login("a@b.com", "Str0ngPass")
    assert result["access_token"] == "a"
    args, kwargs = mock_request.call_args
    assert args[0] == "POST"
    assert args[1].endswith("/api/v1/auth/login")


@patch("frontend.api.base.requests.request")
def test_auth_client_me_sends_bearer(mock_request):
    response = MagicMock()
    response.status_code = 200
    response.content = b'{"user": {"email": "a@b.com"}}'
    response.json.return_value = {"user": {"email": "a@b.com"}}
    mock_request.return_value = response

    auth = AuthClient(ApiClient(base_url="http://example.test"))
    auth.me("token-123")
    _args, kwargs = mock_request.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer token-123"


@patch("frontend.api.base.requests.request")
def test_auth_client_surfaces_friendly_error(mock_request):
    response = MagicMock()
    response.status_code = 401
    response.content = b'{"success": false, "error": "Invalid email or password"}'
    response.json.return_value = {"success": False, "error": "Invalid email or password"}
    mock_request.return_value = response

    auth = AuthClient(ApiClient(base_url="http://example.test"))
    try:
        auth.login("a@b.com", "bad")
        assert False, "expected ApiError"
    except ApiError as exc:
        assert exc.status_code == 401
        assert "Invalid email or password" in str(exc)
        assert "Traceback" not in str(exc)


def test_auth_state_helpers_importable():
    # Import lazily to ensure the module is import-safe without a Streamlit runtime.
    from frontend.utils import auth_state

    assert hasattr(auth_state, "store_tokens")
    assert hasattr(auth_state, "try_refresh")
    assert hasattr(auth_state, "with_auto_refresh")
    assert hasattr(auth_state, "is_authenticated")
