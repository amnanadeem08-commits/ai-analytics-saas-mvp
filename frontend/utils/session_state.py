from __future__ import annotations

import pandas as pd
import streamlit as st

from frontend.utils.theme_manager import DASHBOARD_SETTING_DEFAULTS, DEFAULT_BRANDING



def initialize_session_state(initial_branding: dict | None = None) -> None:
    """Keep app state stable across navigation, uploads, and theme changes."""
    branding = {**DEFAULT_BRANDING, **(initial_branding or {})}
    st.session_state.setdefault("uploaded_datasets", {})
    st.session_state.setdefault("local_dataframes", {})
    st.session_state.setdefault("active_dataset_id", st.session_state.get("selected_dataset_id"))
    st.session_state.setdefault("active_dataframe", None)
    st.session_state.setdefault("selected_theme", branding.get("theme_name", "power_bi_professional"))
    st.session_state.setdefault("branding", branding)
    st.session_state.setdefault("primary_color", branding.get("primary_color", "#118DFF"))
    st.session_state.setdefault("secondary_color", branding.get("secondary_color", "#12239E"))
    st.session_state.setdefault("background_color", "#F5F7FA")
    st.session_state.setdefault("chart_palette", [branding["primary_color"], branding["secondary_color"], branding["accent_color"]])
    st.session_state.setdefault("local_mode_notice", False)
    st.session_state.setdefault("storyboard_items", [])
    st.session_state.setdefault("storyboard_slides", [])
    st.session_state.setdefault("active_storyboard_dataset_id", None)
    st.session_state.setdefault("storyboard_user_edited", False)
    st.session_state.setdefault("detected_domains", {})
    st.session_state.setdefault("active_detected_domain", {"domain": "General", "confidence_score": 0.0, "confidence": "low", "signals": []})
    st.session_state.setdefault("detected_domain", "General")
    for setting_key, setting_value in DASHBOARD_SETTING_DEFAULTS.items():
        st.session_state.setdefault(setting_key, setting_value)

    if st.session_state.get("active_dataset_id") and not st.session_state.get("selected_dataset_id"):
        st.session_state["selected_dataset_id"] = st.session_state["active_dataset_id"]

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

