from __future__ import annotations

"""Frontend token storage + automatic refresh helper (Sprint 8.0).

Tokens live in Streamlit session state only (no backend imports). This helper
transparently refreshes the access token when a call returns 401.
"""

from typing import Any, Callable

import streamlit as st

from frontend.api.auth_client import AuthClient
from frontend.api.base import ApiError
from frontend.utils.workspace_api import get_api_client


def get_auth_client() -> AuthClient:
    return AuthClient(get_api_client())


def store_tokens(payload: dict[str, Any]) -> None:
    st.session_state["auth_access_token"] = payload.get("access_token", "")
    st.session_state["auth_refresh_token"] = payload.get("refresh_token", "")
    st.session_state["auth_session_id"] = payload.get("session_id", "")
    if payload.get("user"):
        st.session_state["auth_user"] = payload["user"]
    st.session_state["auth_is_authenticated"] = bool(payload.get("access_token"))


def clear_tokens() -> None:
    for key in (
        "auth_access_token",
        "auth_refresh_token",
        "auth_session_id",
        "auth_user",
    ):
        st.session_state.pop(key, None)
    st.session_state["auth_is_authenticated"] = False


def get_access_token() -> str:
    return st.session_state.get("auth_access_token", "")


def get_refresh_token() -> str:
    return st.session_state.get("auth_refresh_token", "")


def is_authenticated() -> bool:
    return bool(st.session_state.get("auth_is_authenticated") and get_access_token())


def current_user() -> dict[str, Any]:
    return st.session_state.get("auth_user", {}) or {}


def try_refresh() -> bool:
    """Attempt to refresh the access token. Returns True on success."""
    refresh_token = get_refresh_token()
    if not refresh_token:
        return False
    try:
        payload = get_auth_client().refresh(refresh_token)
        store_tokens(payload)
        return True
    except ApiError:
        clear_tokens()
        return False


def with_auto_refresh(call: Callable[[str], Any]) -> Any:
    """Run ``call(access_token)``; on 401 refresh once and retry.

    Raises ApiError if authentication cannot be recovered.
    """
    token = get_access_token()
    try:
        return call(token)
    except ApiError as exc:
        if exc.status_code == 401 and try_refresh():
            return call(get_access_token())
        raise


def hydrate_current_user() -> dict[str, Any]:
    """Fetch and cache the current user, refreshing the token if needed."""
    if not get_access_token():
        return {}
    try:
        result = with_auto_refresh(lambda token: get_auth_client().me(token))
        user = result.get("user", {})
        if user:
            st.session_state["auth_user"] = user
        return user
    except ApiError:
        return {}
