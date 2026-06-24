from __future__ import annotations

import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from urllib.parse import urlparse

import pandas as pd
import requests
import streamlit as st

from frontend.api_client.backend_client import BackendClient


PROJECT_ROOT = Path(__file__).resolve().parents[2]

LOCAL_MODE_INFO_MESSAGE = "Backend unavailable — running local Streamlit analysis mode."


def get_client(base_url: str) -> BackendClient:
    return BackendClient(base_url=base_url)

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
    try:
        if not ensure_backend_available(client):
            raise requests.RequestException(st.session_state.get("backend_autostart_error", "Backend unavailable"))
        health = client.health()
        st.sidebar.success(f"Backend connected: {health.get('version', '')}")
        st.session_state["local_mode_notice"] = False
    except requests.RequestException:
        st.sidebar.info(LOCAL_MODE_INFO_MESSAGE)

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

