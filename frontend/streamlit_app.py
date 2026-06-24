from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frontend.api_client.backend_client import DEFAULT_API_BASE_URL
from frontend.app_pages.ai_insights_page import render_ai_insights, render_business_visual_analysis, render_data_visual_analysis
from frontend.app_pages.dashboard_page import render_dashboard
from frontend.app_pages.dashboard_studio_page import render_visual_builder
from frontend.app_pages.dataset_page import render_data_cleaning, render_dataset_overview
from frontend.app_pages.location_page import render_location_insights
from frontend.app_pages.reports_page import render_reports
from frontend.app_pages.sql_dax_page import render_dax_studio, render_sql_lab
from frontend.app_pages.storyboard_page import render_storyboard_builder
from frontend.utils.backend_utils import get_client, render_backend_status
from frontend.utils.session_state import initialize_session_state
from frontend.utils.theme_manager import _apply_branding_theme, get_active_branding, render_branding_editor, render_dashboard_settings, render_theme_selector

st.set_page_config(page_title="AI Analytics SaaS MVP", layout="wide")

def main() -> None:
    initialize_session_state()
    api_base_url = st.sidebar.text_input("Backend API URL", value=DEFAULT_API_BASE_URL)
    client = get_client(api_base_url)
    if "branding_loaded" not in st.session_state:
        initialize_session_state(get_active_branding(client))
        st.session_state["branding_loaded"] = True
    else:
        initialize_session_state()
    branding = st.session_state["branding"]
    _apply_branding_theme()

    st.title(branding.get("company_name", "AI Analytics SaaS MVP"))
    st.caption(branding.get("report_title", "Executive Decision Intelligence Report"))
    if branding.get("report_subtitle"):
        st.caption(branding["report_subtitle"])

    render_backend_status(client)
    render_theme_selector(client)
    render_dashboard_settings()
    render_branding_editor(client, branding)

    nav_groups = {
        ":material/folder: Data Management": [
            ("Dataset Preview", "Upload, explore and preview your raw data"),
            ("Data Cleaning", "Fix nulls, duplicates, outliers automatically"),
        ],
        ":material/analytics: Analytics & Statistics": [
            ("Stats Dashboard", "Mean, Median, Mode, Std Dev, Variance - full statistical summary"),
            ("Data Visual Analysis", "Distribution plots, correlation heatmaps, scatter analysis"),
            ("Business Visual Analysis", "KPI trends, segment comparison, business metrics"),
        ],
        ":material/psychology: AI Intelligence": [
            ("AI Insights", "RAG-powered findings: anomalies, risks, opportunities"),
            ("Dashboard Studio", "Drag-and-drop visual builder - Power BI style"),
        ],
        ":material/summarize: Reports & Export": [
            ("Reports", "PDF & PowerPoint executive reports"),
            ("Storyboard Builder", "Tableau-style narrative slides for board presentation"),
        ],
        ":material/build: Advanced Tools": [
            ("SQL Lab", "Write SQL queries directly on your dataset"),
            ("DAX Studio", "Power BI-style DAX measures and calculated columns"),
            ("Location Insights", "Geographic and regional map-based analysis"),
        ],
    }
    st.session_state.setdefault("current_page", "Dataset Preview")
    st.sidebar.markdown(
        """
        <style>
        .sidebar-active-page {
            background: color-mix(in srgb, var(--brand-primary) 16%, transparent);
            border: 1px solid color-mix(in srgb, var(--brand-primary) 36%, var(--surface-border));
            border-radius: 8px;
            color: var(--text-color);
            font-weight: 800;
            margin: .25rem 0 .1rem;
            padding: .45rem .65rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    for group_name, options in nav_groups.items():
        is_active_group = any(page_name == st.session_state["current_page"] for page_name, _ in options)
        with st.sidebar.expander(group_name, expanded=is_active_group):
            for page_name, description in options:
                if page_name == st.session_state["current_page"]:
                    st.markdown(f'<div class="sidebar-active-page">{page_name}</div>', unsafe_allow_html=True)
                elif st.button(page_name, key=f"nav_{page_name}", use_container_width=True):
                    st.session_state["current_page"] = page_name
                    st.rerun()
                st.caption(description)
    page = st.session_state["current_page"]

    if page == "Dataset Preview":
        render_dataset_overview(client)
    elif page == "Data Cleaning":
        render_data_cleaning(client)
    elif page == "Stats Dashboard":
        render_dashboard(client)
    elif page == "Data Visual Analysis":
        render_data_visual_analysis(client)
    elif page == "Business Visual Analysis":
        render_business_visual_analysis(client)
    elif page == "AI Insights":
        render_ai_insights(client)
    elif page == "Dashboard Studio":
        render_visual_builder(client)
    elif page == "Reports":
        render_reports(client)
    elif page == "SQL Lab":
        render_sql_lab(client)
    elif page == "DAX Studio":
        render_dax_studio(client)
    elif page == "Location Insights":
        render_location_insights(client)
    elif page == "Storyboard Builder":
        render_storyboard_builder(client)

    if branding.get("footer_note"):
        st.caption(branding["footer_note"])

if __name__ == "__main__":
    main()
