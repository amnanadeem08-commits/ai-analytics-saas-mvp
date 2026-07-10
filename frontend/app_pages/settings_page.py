"""Settings page.

Consolidates theme selection, branding, dashboard preferences, and connection
diagnostics into a single page so users no longer need to hunt through sidebar
expanders.
"""
from __future__ import annotations

import requests
import streamlit as st

from frontend.api_client.backend_client import BackendClient
from frontend.utils.backend_utils import (
    check_backend_connection,
    invalidate_backend_status_cache,
)
from frontend.utils.theme_manager import (
    DEFAULT_BRANDING,
    DASHBOARD_SETTING_DEFAULTS,
    THEME_PRESETS,
    _apply_theme_preset,
    _render_palette_swatches,
    _sync_branding_state,
    _theme_by_name,
)


def render_settings(client: BackendClient) -> None:
    st.header("Settings")
    st.caption("Configure theme, branding, dashboard preferences, and connection options.")

    tab_theme, tab_branding, tab_dashboard, tab_connection = st.tabs(
        ["Theme", "Branding", "Dashboard", "Connection"]
    )

    # ── Theme ────────────────────────────────────────────────────────────────
    with tab_theme:
        st.subheader("Dashboard Theme")
        display_names = [p["display_name"] for p in THEME_PRESETS]
        active_preset = _theme_by_name(st.session_state.get("selected_theme"))
        selected_display = st.selectbox(
            "Choose a theme preset",
            display_names,
            index=display_names.index(active_preset["display_name"])
            if active_preset["display_name"] in display_names
            else 0,
            key="settings_theme_selector",
        )
        selected_preset = next(p for p in THEME_PRESETS if p["display_name"] == selected_display)
        swatches = _render_palette_swatches(selected_preset["palette"])
        st.markdown(
            f"""
            <div style="padding:12px 14px;border-radius:10px;border:1px solid #ddd;background:#fafafa;margin:8px 0;">
                <b>{selected_preset['display_name']}</b><br/>
                <div style="margin:6px 0;">{swatches}</div>
                <small style="color:#666;">{selected_preset['description']}</small>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Apply Theme", type="primary", key="settings_apply_theme"):
            _apply_theme_preset(selected_preset)
            try:
                applied = client.set_active_theme(selected_preset["name"])
                current = {**st.session_state.get("branding", DEFAULT_BRANDING)}
                current.update({
                    "primary_color": applied.get("primary", selected_preset["palette"][0]),
                    "secondary_color": applied.get("secondary", selected_preset["palette"][1]),
                    "accent_color": applied.get("accent", selected_preset["palette"][2]),
                    "theme_name": selected_preset["name"],
                })
                _sync_branding_state(current, applied.get("palette", selected_preset["palette"]))
                client.update_branding({k: current[k] for k in ["primary_color", "secondary_color", "accent_color", "theme_name"]})
            except requests.RequestException:
                pass
            st.success("Theme applied.")
            st.rerun()

    # ── Branding ─────────────────────────────────────────────────────────────
    with tab_branding:
        st.subheader("Company Branding")
        branding = st.session_state.get("branding", DEFAULT_BRANDING)
        logo_url = branding.get("logo_url")
        if logo_url:
            st.image(f"{client.base_url}{logo_url}", width=120)

        with st.form("settings_branding_form"):
            company_name = st.text_input("Company name", value=branding.get("company_name", ""))
            report_title = st.text_input("Report title", value=branding.get("report_title", ""))
            report_subtitle = st.text_input("Subtitle", value=branding.get("report_subtitle", ""))
            footer_note = st.text_area("Footer note", value=branding.get("footer_note", ""), height=80)
            logo_file = st.file_uploader(
                "Upload company logo", type=["png", "jpg", "jpeg", "webp", "svg"],
                key="settings_logo_upload"
            )
            submitted = st.form_submit_button("Save Branding", type="primary")

        if submitted:
            payload = {
                "company_name": company_name,
                "report_title": report_title,
                "report_subtitle": report_subtitle,
                "footer_note": footer_note,
                "primary_color": branding.get("primary_color", "#118DFF"),
                "secondary_color": branding.get("secondary_color", "#12239E"),
                "accent_color": branding.get("accent_color", "#E66C37"),
            }
            _sync_branding_state({**branding, **payload})
            try:
                client.update_branding(payload)
                if logo_file is not None:
                    _sync_branding_state(client.upload_logo(logo_file))
                st.success("Branding saved.")
            except requests.RequestException:
                st.warning("Backend unavailable — branding saved for this session only.")
            st.rerun()

    # ── Dashboard ────────────────────────────────────────────────────────────
    with tab_dashboard:
        st.subheader("Dashboard Preferences")
        with st.form("settings_dashboard_form"):
            st.selectbox(
                "Dashboard template type",
                ["Executive Dashboard", "Data Visual Analysis", "Business Visual Analysis",
                 "Marketing Dashboard", "Finance Dashboard", "Healthcare Dashboard",
                 "Sales Dashboard", "Operational Dashboard"],
                key="dashboard_template_type",
            )
            c1, c2 = st.columns(2)
            c1.selectbox("KPI density", ["Compact", "Balanced", "Detailed"], key="kpi_density")
            c2.selectbox(
                "Chart density", ["Essential visuals", "Standard visuals", "Full analysis"],
                key="chart_density"
            )
            st.selectbox(
                "Report export package",
                ["Executive PDF", "Full PDF", "PPTX", "Excel", "JSON"],
                key="report_export_package",
            )
            st.divider()
            st.checkbox("Show statistical explanations", key="show_statistical_explanations")
            st.checkbox("Show anomaly panel", key="show_anomaly_panel")
            st.checkbox("Show business recommendations", key="show_business_recommendations")
            st.checkbox("Include visuals in export by default", key="include_visuals_in_export")
            if st.form_submit_button("Save Preferences", type="primary"):
                st.success("Dashboard preferences saved for this session.")

    # ── Connection ───────────────────────────────────────────────────────────
    with tab_connection:
        st.subheader("Connection & Diagnostics")
        conn = check_backend_connection(client)
        st.markdown(f"**Backend URL:** `{client.base_url}`")
        if conn["connected"]:
            version = conn.get("version") or "unknown"
            latency = f" · {conn['latency_ms']} ms" if conn.get("latency_ms") is not None else ""
            st.success(f"Connected · version {version}{latency}")
        else:
            st.warning(conn.get("error") or "Backend is unavailable.")
            st.info(
                "The application works fully in **local analysis mode** when the backend is offline. "
                "Uploads, cleaning, local charts, and report exports remain available."
            )

        if st.button("Re-check connection", key="settings_recheck"):
            invalidate_backend_status_cache()
            st.rerun()

        st.divider()
        st.subheader("API Gateway (/api/v1)")
        st.checkbox("Show detailed API error payloads", key="show_api_details")
        try:
            from frontend.utils.workspace_api import get_workspace_clients, show_api_error

            system = get_workspace_clients(client.base_url)["system"]
            v1_health = system.health()
            st.success(
                f"Gateway status={v1_health.get('status')} · "
                f"services={', '.join(sorted((v1_health.get('services') or {}).keys()))}"
            )
            if st.button("Load capabilities", key="settings_caps"):
                caps = system.capabilities()
                st.json(caps)
        except Exception as exc:
            from frontend.utils.workspace_api import show_api_error

            show_api_error(exc)

        st.divider()
        st.subheader("Session State")
        active_id = st.session_state.get("active_dataset_id") or "None"
        recent = st.session_state.get("recent_datasets", [])
        ai_history = st.session_state.get("ai_conversation_history", [])
        st.markdown(f"- **Active dataset:** `{active_id}`")
        st.markdown(f"- **Recent datasets:** {len(recent)}")
        st.markdown(f"- **AI conversation messages:** {len(ai_history)}")
        st.markdown(f"- **Analyst sessions:** {len(st.session_state.get('analyst_session_history', []))}")
        if st.button("Clear AI conversation history", key="settings_clear_ai_hist"):
            st.session_state["ai_conversation_history"] = []
            st.session_state["ai_analyst_messages"] = []
            st.success("AI conversation history cleared.")
