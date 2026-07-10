from __future__ import annotations

import html

import plotly.graph_objects as go
import plotly.io as pio
import requests
import streamlit as st

from frontend.api_client.backend_client import BackendClient
from frontend.themes.theme_manager import css_variable_block, get_theme, legacy_preset, list_themes


THEME_PRESETS = [legacy_preset(theme) for theme in list_themes()]

DASHBOARD_SETTING_DEFAULTS = {
    "dashboard_template_type": "Executive Dashboard",
    "kpi_density": "Balanced",
    "chart_density": "Standard visuals",
    "report_export_package": "Executive PDF",
    "show_statistical_explanations": True,
    "show_anomaly_panel": True,
    "show_business_recommendations": True,
    "include_visuals_in_export": True,
}

DEFAULT_BRANDING = {
    "company_name": "AI Analytics",
    "report_title": "Executive Decision Intelligence Report",
    "report_subtitle": "Upload a dataset to generate board-ready KPIs, charts, and insights.",
    "footer_note": "",
    "logo_url": "",
    "primary_color": "#174A7C",
    "secondary_color": "#243B53",
    "accent_color": "#B88322",
    "theme_name": "executive",
}


def _sync_branding_state(branding: dict, palette: list[str] | None = None, background: str | None = None) -> None:
    merged = {**DEFAULT_BRANDING, **branding}
    resolved_palette = list(palette or st.session_state.get("chart_palette", []))
    if not resolved_palette:
        resolved_palette = [merged["primary_color"], merged["secondary_color"], merged["accent_color"]]
    for color in [merged["primary_color"], merged["secondary_color"], merged["accent_color"]]:
        if color not in resolved_palette:
            resolved_palette.append(color)
    st.session_state["branding"] = merged
    st.session_state["selected_theme"] = merged.get("theme_name", "executive")
    st.session_state["primary_color"] = merged["primary_color"]
    st.session_state["secondary_color"] = merged["secondary_color"]
    st.session_state["background_color"] = background or get_theme(st.session_state.get("selected_theme")).background
    st.session_state["chart_palette"] = resolved_palette

def _apply_branding_theme() -> None:
    branding = st.session_state.get("branding", DEFAULT_BRANDING)
    active_theme = get_theme(st.session_state.get("selected_theme") or branding.get("theme_name"))
    palette = st.session_state.get("chart_palette") or active_theme.palette
    template_name = "ai_analytics_brand"
    pio.templates[template_name] = go.layout.Template(
        layout={
            "font": {"family": active_theme.typography.font_family, "color": active_theme.text},
            "colorway": palette,
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
        }
    )
    pio.templates.default = template_name
    st.markdown(
        f"""
        <style>
        :root {{
{css_variable_block(active_theme.name, branding)}
        }}
        html, body, .stApp, .stMarkdown, .stDataFrame, .stButton button, .stTextInput input, .stSelectbox div {{
            font-family: var(--brand-font);
        }}
        .stApp {{ background: var(--ui-surface); color: var(--text-color); }}
        span.material-symbols-rounded, span.material-symbols-outlined {{
            font-family: "Material Symbols Rounded", "Material Symbols Outlined" !important;
        }}
        .chart-card-pill {{ color: var(--brand-primary) !important; border-color: var(--brand-primary) !important; }}
        .ai-hero-card {{ background: linear-gradient(135deg, var(--brand-primary), var(--brand-secondary)) !important; }}
        .ai-badge-blue {{ color: var(--brand-primary) !important; border-color: var(--brand-primary) !important; }}
        .ai-card-title {{ color: var(--text-muted); font-size: .78rem; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; }}
        .ai-card-value {{ color: var(--text-color); font-size: 1.55rem; font-weight: 900; margin-top: .25rem; }}
        .ai-card-caption {{ color: var(--text-subtle); font-size: .86rem; margin-top: .35rem; line-height: 1.35; }}
        .evidence-pill {{
            display: inline-block; padding: .28rem .55rem; border-radius: 999px; margin: .12rem;
            color: var(--text-color); background: color-mix(in srgb, var(--brand-primary) 12%, transparent); border: 1px solid color-mix(in srgb, var(--brand-primary) 22%, transparent);
            font-size: .78rem; font-weight: 700;
        }}
        .rag-box {{ border-left: 5px solid var(--brand-accent); padding: .85rem 1rem; border-radius: var(--theme-radius); background: var(--surface-card); }}
        div.stButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"] {{
            background: var(--brand-primary) !important;
            border-color: var(--brand-primary) !important;
            color: #FFFFFF !important;
        }}
        div.stButton > button, div.stDownloadButton > button {{
            border-color: color-mix(in srgb, var(--brand-primary) 42%, var(--surface-border)) !important;
            border-radius: var(--theme-radius) !important;
        }}
        div[data-testid="stMetric"], .ai-card {{
            border: 1px solid color-mix(in srgb, var(--brand-primary) 24%, var(--surface-border));
            border-top: 4px solid var(--brand-accent);
            background: var(--surface-card);
            border-radius: var(--theme-radius);
            padding: .75rem;
            box-shadow: var(--theme-shadow);
        }}
        div[data-testid="stMetricValue"] {{ color: var(--brand-primary); }}
        div[data-testid="stMetricDelta"] {{ color: var(--ui-success); }}
        [data-testid="stSidebar"] {{ background: color-mix(in srgb, var(--ui-surface) 84%, var(--surface-card)); }}
        </style>
        """,
        unsafe_allow_html=True,
    )
def _render_palette_swatches(palette: list[str]) -> str:
    """Render inline colour swatch HTML for a palette."""
    swatches = "".join(f'<span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:{c};margin-right:3px;border:1px solid rgba(0,0,0,0.08)"></span>' for c in palette)
    return swatches

def _theme_by_name(theme_name: str | None) -> dict:
    return next((preset for preset in THEME_PRESETS if preset["name"] == theme_name), THEME_PRESETS[0])

def _apply_theme_preset(preset: dict) -> None:
    current_branding = {**st.session_state.get("branding", DEFAULT_BRANDING)}
    current_branding.update(
        {
            "primary_color": preset["palette"][0],
            "secondary_color": preset["palette"][1],
            "accent_color": preset["palette"][2],
            "theme_name": preset["name"],
        }
    )
    _sync_branding_state(current_branding, preset["palette"], preset["background"])
    st.session_state["theme_apply_message"] = "local"

def render_theme_selector(client: BackendClient) -> None:
    st.sidebar.markdown("#### Choose dashboard theme")
    if st.session_state.pop("theme_apply_message", ""):
        st.sidebar.success("Theme applied locally for this Streamlit session.")
    try:
        client.list_themes()
    except requests.RequestException:
        st.sidebar.caption("Theme presets apply locally; backend sync is unavailable right now.")

    display_names = [preset["display_name"] for preset in THEME_PRESETS]
    active_preset = _theme_by_name(st.session_state.get("selected_theme"))
    selected_display = st.sidebar.selectbox(
        "Choose dashboard theme",
        display_names,
        index=display_names.index(active_preset["display_name"]) if active_preset["display_name"] in display_names else 0,
        key="theme_template_selector",
    )
    selected_preset = next(preset for preset in THEME_PRESETS if preset["display_name"] == selected_display)
    swatches = _render_palette_swatches(selected_preset["palette"])
    st.sidebar.markdown(
        f"""
        <div style="padding:10px 11px;margin:8px 0;border-radius:8px;border:1px solid color-mix(in srgb, var(--brand-primary) 28%, var(--surface-border));background:color-mix(in srgb, var(--ui-surface) 88%, #FFFFFF);">
            <div style="font-weight:800;color:var(--text-color);">{html.escape(selected_preset['display_name'])}</div>
            <div style="margin:7px 0;">{swatches}</div>
            <div style="font-size:.78rem;color:var(--text-muted);line-height:1.35;">{html.escape(selected_preset['description'])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Apply theme", key="apply_selected_theme", use_container_width=True, type="primary"):
        _apply_theme_preset(selected_preset)
        try:
            applied_theme = client.set_active_theme(selected_preset["name"])
            current_branding = {**st.session_state.get("branding", DEFAULT_BRANDING)}
            current_branding.update(
                {
                    "primary_color": applied_theme.get("primary", selected_preset["palette"][0]),
                    "secondary_color": applied_theme.get("secondary", selected_preset["palette"][1]),
                    "accent_color": applied_theme.get("accent", selected_preset["palette"][2]),
                    "theme_name": selected_preset["name"],
                }
            )
            _sync_branding_state(current_branding, applied_theme.get("palette", selected_preset["palette"]), applied_theme.get("background", selected_preset["background"]))
            client.update_branding({key: current_branding[key] for key in ["primary_color", "secondary_color", "accent_color", "theme_name"]})
        except requests.RequestException:
            pass
        st.rerun()

def render_dashboard_settings() -> None:
    st.sidebar.divider()
    with st.sidebar.expander("Dashboard Settings", expanded=False):
        st.selectbox(
            "Dashboard template type",
            [
                "Executive Dashboard",
                "Data Visual Analysis",
                "Business Visual Analysis",
                "Marketing Dashboard",
                "Finance Dashboard",
                "Healthcare Dashboard",
                "Sales Dashboard",
                "Operational Dashboard",
            ],
            key="dashboard_template_type",
        )
        st.selectbox("KPI density", ["Compact", "Balanced", "Detailed"], key="kpi_density")
        st.selectbox("Chart density", ["Essential visuals", "Standard visuals", "Full analysis"], key="chart_density")
        st.selectbox("Report export package", ["Executive PDF", "Full PDF", "PPTX", "Excel", "JSON"], key="report_export_package")
        st.checkbox("Show statistical explanations", key="show_statistical_explanations")
        st.checkbox("Show anomaly panel", key="show_anomaly_panel")
        st.checkbox("Show business recommendations", key="show_business_recommendations")
        st.checkbox("Include visuals in export by default", key="include_visuals_in_export")
        st.caption("Settings are saved for this Streamlit session and follow you across pages.")

def get_active_branding(client: BackendClient) -> dict:
    try:
        return client.get_branding()
    except requests.RequestException:
        return {
            "company_name": "AI Analytics",
            "report_title": "Executive Decision Intelligence Report",
            "report_subtitle": "Upload a dataset to generate board-ready KPIs, charts, and insights.",
            "footer_note": "",
            "logo_url": "",
            "primary_color": "#118DFF",
            "secondary_color": "#12239E",
            "accent_color": "#E66C37",
            "theme_name": "executive",
        }

def render_branding_editor(client: BackendClient, branding: dict) -> None:
    st.sidebar.divider()
    with st.sidebar.expander("Branding Settings", expanded=False):
        logo_url = branding.get("logo_url")
        if logo_url:
            st.image(f"{client.base_url}{logo_url}", width=100)

        company_name = st.text_input("Company name", value=branding.get("company_name", "AI Analytics"))
        report_title = st.text_input(
            "Report title",
            value=branding.get("report_title", "Executive Decision Intelligence Report"),
        )
        report_subtitle = st.text_input(
            "Subtitle",
            value=branding.get("report_subtitle", "Upload a dataset to generate board-ready KPIs, charts, and insights."),
        )
        footer_note = st.text_area(
            "Footer / brand note",
            value=branding.get("footer_note", ""),
            height=80,
        )
        logo_file = st.file_uploader("Upload Company Logo", type=["png", "jpg", "jpeg", "webp", "svg"], key="branding_logo_upload")
        primary_color = branding.get("primary_color", "#118DFF")
        secondary_color = branding.get("secondary_color", "#12239E")
        accent_color = branding.get("accent_color", "#E66C37")
        st.caption("Theme preset colors are managed from the dashboard theme selector.")

        col1, col2 = st.columns(2)
        if col1.button("Save", use_container_width=True, key="branding_save_button"):
            branding_payload = {
                "company_name": company_name,
                "report_title": report_title,
                "report_subtitle": report_subtitle,
                "footer_note": footer_note,
                "primary_color": primary_color,
                "secondary_color": secondary_color,
                "accent_color": accent_color,
            }
            _sync_branding_state({**st.session_state.get("branding", DEFAULT_BRANDING), **branding_payload})
            try:
                client.update_branding(branding_payload)
                if logo_file is not None:
                    _sync_branding_state(client.upload_logo(logo_file))
                st.rerun()
            except requests.RequestException as exc:
                st.warning("Could not save branding while the backend is unavailable. Session branding was kept locally.")
        if col2.button("Reset", use_container_width=True, key="branding_reset_button"):
            reset_payload = {
                "company_name": "AI Analytics",
                "report_title": "Executive Decision Intelligence Report",
                "report_subtitle": "Upload a dataset to generate board-ready KPIs, charts, and insights.",
                "footer_note": "",
                "logo_url": "",
                "primary_color": "#118DFF",
                "secondary_color": "#12239E",
                "accent_color": "#E66C37",
                "theme_name": "executive",
            }
            _sync_branding_state({**DEFAULT_BRANDING, **reset_payload}, ["#0078D4", "#004E8C", "#00B7C3", "#F2C811", "#107C10"], "#F5F7FA")
            try:
                client.update_branding(reset_payload)
                st.rerun()
            except requests.RequestException as exc:
                st.warning("Could not reset backend branding right now. Session branding was reset locally.")

def _ai_dashboard_css(primary: str, secondary: str, accent: str) -> None:
    st.markdown(
        f"""
        <style>
        .ai-hero {{
            padding: 1.15rem 1.25rem;
            border-radius: 24px;
            color: white;
            background: radial-gradient(circle at 10% 20%, rgba(255,255,255,.28), transparent 24%),
                        linear-gradient(135deg, {primary}, {secondary} 52%, {accent});
            box-shadow: 0 18px 48px rgba(15,23,42,.18);
            margin-bottom: 1rem;
        }}
        .ai-hero h1 {{ margin: 0; font-size: 2rem; line-height: 1.1; }}
        .ai-hero p {{ margin: .4rem 0 0; opacity: .92; }}
        .ai-card {{
            border: 1px solid rgba(148,163,184,.22);
            border-radius: 20px;
            padding: 1rem;
            background: linear-gradient(180deg, rgba(255,255,255,.92), rgba(248,250,252,.78));
            box-shadow: 0 12px 34px rgba(15,23,42,.08);
            min-height: 116px;
        }}
        .ai-card-title {{ color: var(--text-muted); font-size: .78rem; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; }}
        .ai-card-value {{ color: var(--text-color); font-size: 1.55rem; font-weight: 900; margin-top: .25rem; }}
        .ai-card-caption {{ color: var(--text-subtle); font-size: .86rem; margin-top: .35rem; line-height: 1.35; }}
        .evidence-pill {{
            display: inline-block; padding: .28rem .55rem; border-radius: 999px; margin: .12rem;
            color: var(--text-color); background: color-mix(in srgb, var(--brand-primary) 12%, transparent); border: 1px solid color-mix(in srgb, var(--brand-primary) 22%, transparent);
            font-size: .78rem; font-weight: 700;
        }}
        .rag-box {{ border-left: 5px solid {accent}; padding: .85rem 1rem; border-radius: 14px; background: rgba(255,255,255,.82); }}
        </style>
        """,
        unsafe_allow_html=True,
    )

def _storyboard_theme_snapshot(theme: str | None = None) -> dict:
    return {
        "theme": theme or st.session_state.get("selected_theme", "power_bi_professional"),
        "primary_color": st.session_state.get("primary_color", "#118DFF"),
        "secondary_color": st.session_state.get("secondary_color", "#12239E"),
        "background_color": st.session_state.get("background_color", "#F5F7FA"),
        "palette": st.session_state.get("chart_palette", []),
    }

