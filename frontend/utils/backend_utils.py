from __future__ import annotations

import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from typing import Any
from urllib.parse import urlparse

import pandas as pd
import requests
import streamlit as st

from frontend.api_client.backend_client import BackendClient


PROJECT_ROOT = Path(__file__).resolve().parents[2]

LOCAL_MODE_INFO_MESSAGE = "Backend unavailable — running local Streamlit analysis mode."

# How long (seconds) to re-use a cached health check result before probing again.
_BACKEND_STATUS_CACHE_TTL = 15.0


def get_client(base_url: str) -> BackendClient:
    return BackendClient(base_url=base_url)


# ── Connection status ────────────────────────────────────────────────────────


def check_backend_connection(client: BackendClient) -> dict[str, Any]:
    """Probe the backend health endpoint and return a status dict.

    The result is cached in ``st.session_state`` for ``_BACKEND_STATUS_CACHE_TTL``
    seconds so repeated Streamlit reruns do not flood the backend with health checks.

    Returned keys:
        connected (bool): True when the backend responded successfully.
        version (str): Backend version string (may be empty).
        latency_ms (int | None): Round-trip time in milliseconds, or None on failure.
        error (str): Human-readable error message when not connected.
        checked_at (float): UNIX timestamp of the last probe.
    """
    now = time.time()
    cache: dict[str, Any] = st.session_state.get("_backend_status_cache", {})
    if cache.get("checked_at", 0) > now - _BACKEND_STATUS_CACHE_TTL:
        return cache

    status: dict[str, Any] = {
        "checked_at": now,
        "connected": False,
        "version": "",
        "latency_ms": None,
        "error": "",
    }
    try:
        t0 = time.time()
        health = client.health()
        status["latency_ms"] = round((time.time() - t0) * 1000)
        status["connected"] = True
        status["version"] = health.get("version", "")
    except requests.RequestException as exc:
        status["error"] = BackendClient._friendly_error(exc)

    st.session_state["_backend_status_cache"] = status
    return status


def invalidate_backend_status_cache() -> None:
    """Force the next ``check_backend_connection`` call to probe the backend."""
    st.session_state.pop("_backend_status_cache", None)

def safe_table(rows: list[dict]) -> pd.DataFrame:
    """Normalize nested API values so Streamlit/PyArrow can render them."""
    normalized_rows = []
    for row in rows:
        normalized = {}
        for key, value in row.items():
            if isinstance(value, (dict, list)):
                normalized[key] = json.dumps(value, ensure_ascii=False)
            else:
                normalized[key] = value
        normalized_rows.append(normalized)
    return pd.DataFrame(normalized_rows)

def _is_local_backend_url(base_url: str) -> bool:
    parsed = urlparse(base_url)
    host = (parsed.hostname or "").lower()
    port = parsed.port or 80
    return parsed.scheme in {"http", ""} and host in {"127.0.0.1", "localhost"} and port == 8000

def _backend_python_executable() -> str:
    venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable

def _wait_for_local_backend(host: str = "127.0.0.1", port: int = 8000, timeout_seconds: float = 8.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.25)
    return False

def ensure_backend_available(client: BackendClient) -> bool:
    try:
        client.health()
        st.session_state["backend_autostart_error"] = ""
        return True
    except requests.RequestException:
        if not _is_local_backend_url(client.base_url):
            return False

    if st.session_state.get("backend_autostart_failed"):
        return False

    if not st.session_state.get("backend_autostart_attempted"):
        creation_flags = 0
        if os.name == "nt":
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        try:
            subprocess.Popen(
                [
                    _backend_python_executable(),
                    "-m",
                    "uvicorn",
                    "backend.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                ],
                cwd=PROJECT_ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
            )
            st.session_state["backend_autostart_attempted"] = True
            st.session_state["backend_autostart_failed"] = False
            st.session_state["backend_autostart_error"] = ""
        except OSError as exc:
            st.session_state["backend_autostart_attempted"] = True
            st.session_state["backend_autostart_failed"] = True
            st.session_state["backend_autostart_error"] = "Backend unavailable."
            return False

    if _wait_for_local_backend():
        try:
            client.health()
            st.session_state["backend_autostart_error"] = ""
            return True
        except requests.RequestException:
            pass

    st.session_state["backend_autostart_failed"] = True
    st.session_state["backend_autostart_error"] = "Backend unavailable."
    return False

def render_backend_status(client: BackendClient) -> None:
    """Render backend connectivity status in the sidebar.

    Shows connection, version, latency on success, or a friendly offline notice.
    Never exposes Python tracebacks to the end user.
    """
    if not ensure_backend_available(client):
        error_msg = st.session_state.get("backend_autostart_error", "")
        notice = LOCAL_MODE_INFO_MESSAGE
        if error_msg:
            notice = f"{LOCAL_MODE_INFO_MESSAGE}\n\n{error_msg}"
        st.sidebar.warning(notice)
        st.session_state["local_mode_notice"] = True
        st.session_state["backend_connected"] = False
        return

    status = check_backend_connection(client)
    if status["connected"]:
        version_tag = f" · v{status['version']}" if status.get("version") else ""
        latency_tag = f" · {status['latency_ms']} ms" if status.get("latency_ms") is not None else ""
        st.sidebar.success(f"Backend connected{version_tag}{latency_tag}")
        st.session_state["local_mode_notice"] = False
        st.session_state["backend_connected"] = True
    else:
        friendly = status.get("error") or "Backend unavailable."
        st.sidebar.warning(f"{friendly}\n\nLocal analysis mode is active.")
        st.session_state["local_mode_notice"] = True
        st.session_state["backend_connected"] = False

def is_local_dataset_id(dataset_id: str | None) -> bool:
    if not dataset_id:
        return False
    return str(dataset_id).startswith("local_") or str(dataset_id).startswith("local::")

def _is_local_dataset_id(dataset_id: str | None) -> bool:
    return is_local_dataset_id(dataset_id)

def _warn_backend_unavailable(context: str) -> None:
    st.warning(f"{context} is temporarily unavailable. Local upload preview and dashboards are still available.")

def _build_local_dataset_id(filename: str) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename).stem).strip("._-") or "dataset"
    return f"local_{int(time.time() * 1000)}_{safe_name}"

