from __future__ import annotations

import logging
import os
import time
from typing import Any

import requests

DEFAULT_API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
API_V1_PREFIX = "/api/v1"

_log = logging.getLogger("ai_analytics.workspace_api")


class ApiError(Exception):
    """User-facing API error without backend stack traces."""

    def __init__(self, message: str, *, status_code: int | None = None, details: Any = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


def friendly_api_error(exc: Exception) -> str:
    if isinstance(exc, ApiError):
        return exc.message
    if isinstance(exc, requests.exceptions.ConnectionError):
        return "Cannot connect to the API. Start the FastAPI server and check the base URL in Settings."
    if isinstance(exc, requests.exceptions.Timeout):
        return "The API request timed out. Try again shortly."
    if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None:
        return _message_from_response(exc.response)
    return "An unexpected API error occurred."


def _message_from_response(response: requests.Response) -> str:
    try:
        payload = response.json()
    except Exception:
        return f"API error (HTTP {response.status_code})."
    if isinstance(payload, dict):
        if payload.get("error"):
            return str(payload["error"])
        detail = payload.get("detail")
        if isinstance(detail, dict) and detail.get("error"):
            return str(detail["error"])
        if detail is not None:
            return str(detail)[:240]
    return f"API error (HTTP {response.status_code})."


class ApiClient:
    """Thin HTTP client for `/api/v1` and legacy upload endpoints."""

    _TIMEOUT_FAST: tuple[float, float] = (5.0, 20.0)
    _TIMEOUT_SLOW: tuple[float, float] = (10.0, 180.0)
    _TIMEOUT_UPLOAD: tuple[float, float] = (10.0, 600.0)

    def __init__(self, base_url: str = DEFAULT_API_BASE_URL):
        self.base_url = base_url.rstrip("/")

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    def v1(self, path: str) -> str:
        path = path if path.startswith("/") else f"/{path}"
        return f"{API_V1_PREFIX}{path}"

    def request(
        self,
        method: str,
        path: str,
        *,
        timeout: tuple[float, float] | float | None = None,
        max_retries: int = 1,
        **kwargs: Any,
    ) -> Any:
        url = self._url(path)
        timeout = timeout or self._TIMEOUT_FAST
        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                _log.debug("%s %s attempt=%s", method.upper(), path, attempt + 1)
                response = requests.request(method, url, timeout=timeout, **kwargs)
                if response.status_code >= 400:
                    raise ApiError(
                        _message_from_response(response),
                        status_code=response.status_code,
                        details=_safe_json(response),
                    )
                if response.status_code == 204 or not response.content:
                    return {}
                return _safe_json(response)
            except ApiError:
                raise
            except requests.exceptions.Timeout as exc:
                last_exc = exc
                break
            except requests.exceptions.ConnectionError as exc:
                last_exc = exc
                if attempt < max_retries:
                    time.sleep(0.35 * (attempt + 1))
            except requests.RequestException as exc:
                raise ApiError(friendly_api_error(exc)) from exc
        raise ApiError(friendly_api_error(last_exc or RuntimeError("request failed")))

    def get(self, path: str, **kwargs: Any) -> Any:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Any:
        return self.request("POST", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Any:
        return self.request("DELETE", path, **kwargs)


def _safe_json(response: requests.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return {"raw": response.text[:500]}
