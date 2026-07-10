from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

from frontend.utils.theme_manager import DASHBOARD_SETTING_DEFAULTS, DEFAULT_BRANDING


_MAX_RECENT_DATASETS = 6
_MAX_AI_HISTORY = 50


def initialize_session_state(initial_branding: dict | None = None) -> None:
    """Keep app state stable across navigation, uploads, and theme changes."""
    branding = {**DEFAULT_BRANDING, **(initial_branding or {})}
    # --- Dataset state ---
    st.session_state.setdefault("uploaded_datasets", {})
    st.session_state.setdefault("local_dataframes", {})
    st.session_state.setdefault("active_dataset_id", st.session_state.get("selected_dataset_id"))
    st.session_state.setdefault("active_dataframe", None)
    # --- Recent datasets (persists across page changes within a session) ---
    st.session_state.setdefault("recent_datasets", [])
    # --- Theme / branding ---
    st.session_state.setdefault("selected_theme", branding.get("theme_name", "power_bi_professional"))
    st.session_state.setdefault("branding", branding)
    st.session_state.setdefault("primary_color", branding.get("primary_color", "#118DFF"))
    st.session_state.setdefault("secondary_color", branding.get("secondary_color", "#12239E"))
    st.session_state.setdefault("background_color", "#F5F7FA")
    st.session_state.setdefault("chart_palette", [branding["primary_color"], branding["secondary_color"], branding["accent_color"]])
    # --- Connection state ---
    st.session_state.setdefault("local_mode_notice", False)
    st.session_state.setdefault("backend_connected", False)
    # --- Storyboard ---
    st.session_state.setdefault("storyboard_items", [])
    st.session_state.setdefault("storyboard_slides", [])
    st.session_state.setdefault("active_storyboard_dataset_id", None)
    st.session_state.setdefault("storyboard_user_edited", False)
    # --- Domain detection ---
    st.session_state.setdefault("detected_domains", {})
    st.session_state.setdefault("active_detected_domain", {"domain": "General", "confidence_score": 0.0, "confidence": "low", "signals": []})
    st.session_state.setdefault("detected_domain", "General")
    # --- AI conversation history ---
    st.session_state.setdefault("ai_conversation_history", [])
    st.session_state.setdefault("ai_chat_input", "")
    # --- Sprint 8.0 authentication state ---
    st.session_state.setdefault("auth_access_token", "")
    st.session_state.setdefault("auth_refresh_token", "")
    st.session_state.setdefault("auth_session_id", "")
    st.session_state.setdefault("auth_user", {})
    st.session_state.setdefault("auth_is_authenticated", False)
    # --- Sprint 8.1 org/workspace context ---
    st.session_state.setdefault("active_organization_id", "")
    st.session_state.setdefault("active_workspace_id", "")
    # --- Sprint 7.9 workspace state ---
    st.session_state.setdefault("api_base_url", st.session_state.get("api_base_url_input") or "http://127.0.0.1:8000")
    st.session_state.setdefault("ai_analyst_messages", [])
    st.session_state.setdefault("analyst_session_history", [])
    st.session_state.setdefault("active_analyst_session_id", None)
    st.session_state.setdefault("workflow_execution_history", [])
    st.session_state.setdefault("active_workflow_execution_id", None)
    st.session_state.setdefault("last_evaluation_id", None)
    st.session_state.setdefault("show_api_details", False)
    # --- Navigation ---
    st.session_state.setdefault("current_page", "Home")
    st.session_state.setdefault("nav_history", [])
    # --- Dashboard settings ---
    for setting_key, setting_value in DASHBOARD_SETTING_DEFAULTS.items():
        st.session_state.setdefault(setting_key, setting_value)

    if st.session_state.get("active_dataset_id") and not st.session_state.get("selected_dataset_id"):
        st.session_state["selected_dataset_id"] = st.session_state["active_dataset_id"]


def track_recent_dataset(dataset_id: str, filename: str) -> None:
    """Add or promote a dataset to the front of the recent-datasets list."""
    if not dataset_id:
        return
    entry: dict[str, Any] = {
        "dataset_id": dataset_id,
        "filename": filename or dataset_id,
        "visited_at": datetime.now().isoformat(timespec="seconds"),
    }
    recent: list[dict[str, Any]] = [
        r for r in st.session_state.get("recent_datasets", []) if r.get("dataset_id") != dataset_id
    ]
    recent.insert(0, entry)
    st.session_state["recent_datasets"] = recent[:_MAX_RECENT_DATASETS]


def append_ai_conversation(role: str, text: str) -> None:
    """Append a message to the AI conversation history (capped at _MAX_AI_HISTORY)."""
    history: list[dict[str, Any]] = st.session_state.get("ai_conversation_history", [])
    history.append({
        "role": role,
        "text": text,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    })
    st.session_state["ai_conversation_history"] = history[-_MAX_AI_HISTORY:]


def navigate_to(page: str) -> None:
    """Change the current page and record it in nav history."""
    current = st.session_state.get("current_page", "Home")
    if current != page:
        history: list[str] = st.session_state.get("nav_history", [])
        history.append(current)
        st.session_state["nav_history"] = history[-20:]
    st.session_state["current_page"] = page


def _sync_storyboard_keys(dataset_id: str, items: list[dict]) -> None:
    st.session_state["storyboard_items"] = items
    st.session_state["storyboard_slides"] = [item.get("slide_id") for item in items]
    st.session_state["active_storyboard_dataset_id"] = dataset_id


def _ensure_default_local_storyboard(dataset_id: str, df: pd.DataFrame) -> list[dict]:
    current_dataset = st.session_state.get("active_storyboard_dataset_id")
    items = st.session_state.get("storyboard_items")
    has_items = isinstance(items, list) and bool(items)
    if current_dataset != dataset_id or not has_items:
        from frontend.app_pages.storyboard_page import build_default_storyboard

        built = build_default_storyboard(df, dataset_id, st.session_state.get("selected_theme"), dict(st.session_state))
        _sync_storyboard_keys(dataset_id, built)
        st.session_state["storyboard_user_edited"] = False
        return built
    return items if isinstance(items, list) else []

