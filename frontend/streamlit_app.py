from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frontend.api_client.backend_client import DEFAULT_API_BASE_URL
# ── Existing page renderers (unchanged) ──────────────────────────────────────
from frontend.app_pages.ai_insights_page import (
    render_ai_insights,
    render_business_visual_analysis,
    render_data_visual_analysis,
)
from frontend.app_pages.dashboard_page import render_dashboard
from frontend.app_pages.dashboard_studio_page import render_visual_builder
from frontend.app_pages.dataset_page import (
    render_data_cleaning,
    render_dataset_overview,
    render_upload_page,
)
from frontend.app_pages.location_page import render_location_insights
from frontend.app_pages.reports_page import render_reports
from frontend.app_pages.sql_dax_page import render_dax_studio, render_sql_lab
from frontend.app_pages.storyboard_page import render_storyboard_builder
# ── Workspace pages (Sprint 7.9 — API gateway clients only) ───────────────────
from frontend.app_pages.home_page import render_home
from frontend.app_pages.ai_chat_page import render_ai_chat
from frontend.app_pages.settings_page import render_settings
from frontend.app_pages.ai_analyst_workspace_page import render_ai_analyst_workspace
from frontend.app_pages.dataset_manager_page import render_dataset_manager
from frontend.app_pages.workflow_monitor_page import render_workflow_monitor
from frontend.app_pages.knowledge_center_page import render_knowledge_center
from frontend.app_pages.evaluation_dashboard_page import render_evaluation_dashboard
from frontend.app_pages.session_history_page import render_session_history
from frontend.app_pages.job_monitor_page import render_job_monitor
from frontend.app_pages.storage_manager_page import render_storage_manager
from frontend.app_pages.dataset_versions_page import render_dataset_versions
from frontend.app_pages.artifact_browser_page import render_artifact_browser
from frontend.app_pages.storage_statistics_page import render_storage_statistics
from frontend.app_pages.system_health_page import render_system_health
from frontend.app_pages.metrics_dashboard_page import render_metrics_dashboard
from frontend.app_pages.application_status_page import render_application_status
from frontend.app_pages.dependency_status_page import render_dependency_status
from frontend.app_pages.configuration_viewer_page import render_configuration_viewer
from frontend.app_pages.billing_dashboard_page import render_billing_dashboard
from frontend.app_pages.usage_dashboard_page import render_usage_dashboard
from frontend.app_pages.subscription_management_page import render_subscription_management
from frontend.app_pages.api_key_manager_page import render_api_key_manager
from frontend.app_pages.admin_dashboard_page import render_admin_dashboard
from frontend.app_pages.system_analytics_page import render_system_analytics
from frontend.app_pages.organization_billing_page import render_organization_billing
# ── Authentication pages (Sprint 8.0) ─────────────────────────────────────────
from frontend.app_pages.auth_pages import (
    render_change_password,
    render_login,
    render_profile,
    render_register,
)
# ── Organization / RBAC admin pages (Sprint 8.1) ──────────────────────────────
from frontend.app_pages.rbac_pages import (
    render_invitations,
    render_members,
    render_organizations,
    render_permissions,
    render_roles,
    render_workspace_manager,
)
# ── Utilities ─────────────────────────────────────────────────────────────────
from frontend.utils.backend_utils import get_client, render_backend_status
from frontend.utils.session_state import initialize_session_state, navigate_to
from frontend.utils.theme_manager import (
    _apply_branding_theme,
    get_active_branding,
)

st.set_page_config(
    page_title="AI Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Command-box keyword router ────────────────────────────────────────────────

_COMMAND_ROUTES: list[tuple[tuple[str, ...], str]] = [
    (("upload", "import", "load file"), "Dataset Manager"),
    (("clean", "quality", "fix data"), "Data Cleaning"),
    (("preview", "explore", "browse"), "Dataset Preview"),
    (("dashboard", "kpi", "stats", "statistics"), "Dashboard"),
    (("chart", "visual", "plot", "graph"), "Charts"),
    (("pivot",), "Pivot Tables"),
    (("studio", "builder", "drag"), "Dashboard Studio"),
    (("ai analyst", "analyst"), "AI Analyst"),
    (("workflow", "monitor"), "Workflow Monitor"),
    (("knowledge", "rag", "document"), "Knowledge Center"),
    (("evaluation", "score", "grade"), "Evaluation Dashboard"),
    (("session", "history", "resume"), "Session History"),
    (("job", "queue", "worker", "background"), "Job Monitor"),
    (("storage", "artifact", "object store"), "Storage Manager"),
    (("version", "rollback"), "Dataset Versions"),
    (("artifact browser",), "Artifact Browser"),
    (("storage stats", "quota"), "Storage Statistics"),
    (("health", "liveness", "readiness"), "System Health"),
    (("metrics", "monitoring"), "Metrics Dashboard"),
    (("application status", "system status"), "Application Status"),
    (("dependency", "dependencies"), "Dependency Status"),
    (("configuration", "config viewer"), "Configuration Viewer"),
    (("billing", "invoice"), "Billing Dashboard"),
    (("usage dashboard",), "Usage Dashboard"),
    (("subscription", "plan"), "Subscription Management"),
    (("api key",), "API Key Manager"),
    (("admin dashboard",), "Admin Dashboard"),
    (("system analytics",), "System Analytics"),
    (("organization billing",), "Organization Billing"),
    (("chat", "ask", "question"), "AI Chat"),
    (("insight", "anomal", "detect"), "AI Insights"),
    (("recommend",), "AI Analyst"),
    (("pdf", "report"), "Reports"),
    (("powerpoint", "pptx", "presentation"), "Reports"),
    (("storyboard", "story", "slide"), "Storyboard"),
    (("sql", "query"), "SQL Lab"),
    (("dax", "measure"), "DAX Studio"),
    (("location", "map", "regional"), "Location Insights"),
    (("setting", "theme", "branding", "config"), "Settings"),
    (("login", "sign in", "signin"), "Login"),
    (("register", "sign up", "signup", "create account"), "Register"),
    (("profile", "account"), "Profile"),
    (("change password", "password"), "Change Password"),
    (("organization", "org"), "Organizations"),
    (("workspace manager", "workspace admin"), "Workspace Manager"),
    (("member", "membership"), "Members"),
    (("invite", "invitation"), "Invitations"),
    (("role",), "Roles"),
    (("permission", "access"), "Permissions"),
]


def _route_command(cmd: str) -> str | None:
    lower = cmd.strip().lower()
    for keywords, page in _COMMAND_ROUTES:
        if any(kw in lower for kw in keywords):
            return page
    return None


# ── Navigation rendering ──────────────────────────────────────────────────────

_NAV_GROUPS: dict[str, list[tuple[str, str]]] = {
    ":material/home: Start": [
        ("Home", "Overview and guided workflow"),
    ],
    ":material/upload_file: Get data": [
        ("Upload", "Upload a CSV or Excel file"),
        ("Dataset Manager", "Manage datasets via API"),
        ("Dataset Preview", "Explore and preview your data"),
        ("Data Cleaning", "Fix nulls, duplicates, outliers"),
    ],
    ":material/analytics: Analyze": [
        ("Dashboard", "Statistical summary and KPI metrics"),
        ("Charts", "Distribution plots and correlations"),
        ("Business Analysis", "KPI trends and segment comparisons"),
        ("Pivot Tables", "Pivot table explorer"),
        ("Dashboard Studio", "Drag-and-drop visual builder"),
        ("Location Insights", "Geographic and regional analysis"),
    ],
    ":material/psychology: AI insights": [
        ("AI Analyst", "Natural-language analysis via /api/v1"),
        ("AI Chat", "Chat with your data in plain language"),
        ("AI Insights", "Anomalies, risks, and opportunities"),
        ("Knowledge Center", "Ingest and search knowledge"),
        ("Evaluation Dashboard", "Scores, strengths, weaknesses"),
        ("Session History", "Resume previous analyst sessions"),
    ],
    ":material/play_circle: Automate": [
        ("Workflow Monitor", "Inspect workflow executions"),
        ("Job Monitor", "Background jobs, progress, retries"),
    ],
    ":material/folder: Storage": [
        ("Storage Manager", "Upload and manage stored artifacts"),
        ("Dataset Versions", "Version history and rollback"),
        ("Artifact Browser", "Browse artifacts by type"),
        ("Storage Statistics", "Quota and storage usage"),
    ],
    ":material/summarize: Share": [
        ("Reports", "PDF & PowerPoint executive reports"),
        ("Storyboard", "Narrative slide deck for board review"),
    ],
    ":material/build: Advanced": [
        ("SQL Lab", "Write SQL queries on your dataset"),
        ("DAX Studio", "Power BI-style DAX measures"),
        ("Settings", "Theme, branding, and preferences"),
    ],
    ":material/account_circle: Account": [
        ("Login", "Sign in to your account"),
        ("Register", "Create a new account"),
        ("Profile", "View and edit your profile"),
        ("Change Password", "Update your password"),
    ],
    ":material/admin_panel_settings: Admin": [
        ("Organizations", "Manage organizations"),
        ("Workspace Manager", "Create and manage workspaces"),
        ("Members", "Organization membership"),
        ("Invitations", "Invite and respond to invitations"),
        ("Roles", "Roles and role assignment"),
        ("Permissions", "Permissions and access checks"),
        ("Billing Dashboard", "Estimates and invoices"),
        ("Usage Dashboard", "Organization usage metrics"),
        ("Subscription Management", "Plans, trials, limits"),
        ("API Key Manager", "Create, rotate, revoke keys"),
        ("Organization Billing", "Generate invoices"),
        ("Admin Dashboard", "Platform admin overview"),
        ("System Analytics", "Commercial system stats"),
        ("System Health", "Liveness, readiness, health probes"),
        ("Metrics Dashboard", "Counters, gauges, timers"),
        ("Application Status", "Combined system status"),
        ("Dependency Status", "Database, storage, queue, worker"),
        ("Configuration Viewer", "Read-only config (redacted)"),
    ],
}

# Internal alias: some nav labels map to existing renderers with different names
_PAGE_ALIASES: dict[str, str] = {
    "Business Analysis": "Business Visual Analysis",
    "AI Insights": "AI Insights",
    "Storyboard": "Storyboard Builder",
}


def _canonical_page(page: str) -> str:
    """Resolve nav label to the canonical page name used in the renderer map."""
    return _PAGE_ALIASES.get(page, page)


def _render_sidebar_nav(current_page: str) -> None:
    st.sidebar.markdown(
        """
        <style>
        .sidebar-active {
            background: color-mix(in srgb, var(--brand-primary) 16%, transparent);
            border: 1px solid color-mix(in srgb, var(--brand-primary) 36%, var(--surface-border));
            border-radius: 8px;
            color: var(--text-color);
            font-weight: 800;
            margin: .2rem 0;
            padding: .4rem .65rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    for group_name, items in _NAV_GROUPS.items():
        active_in_group = any(_canonical_page(name) == current_page or name == current_page for name, _ in items)
        with st.sidebar.expander(group_name, expanded=active_in_group):
            for page_name, description in items:
                canonical = _canonical_page(page_name)
                is_active = canonical == current_page or page_name == current_page
                if is_active:
                    st.markdown(f'<div class="sidebar-active">{page_name}</div>', unsafe_allow_html=True)
                elif st.button(page_name, key=f"nav_{page_name}", use_container_width=True):
                    navigate_to(page_name)
                    st.rerun()
                st.caption(description)


def _render_ai_command_box() -> None:
    """AI command box at the bottom of the sidebar for workflow shortcuts."""
    st.sidebar.divider()
    st.sidebar.markdown("#### AI Command")
    cmd = st.sidebar.text_input(
        "What do you want to do?",
        placeholder='e.g. "show dashboard" or "upload data"',
        key="ai_command_input",
        label_visibility="collapsed",
    )
    if st.sidebar.button("Run", key="ai_command_run", use_container_width=True, type="primary"):
        if cmd.strip():
            destination = _route_command(cmd)
            if destination:
                navigate_to(destination)
                st.rerun()
            else:
                st.sidebar.info(f'No match found for "{cmd}". Try "dashboard", "upload", or "insights".')


# ── Page renderer map ─────────────────────────────────────────────────────────

def _dispatch_page(page: str, client) -> None:
    """Map canonical page names to their render functions."""
    canonical = _canonical_page(page)
    dispatch = {
        "Home":                     render_home,
        "Upload":                   render_upload_page,
        "Dataset Preview":          render_dataset_overview,
        "Data Cleaning":            render_data_cleaning,
        "Dashboard":                render_dashboard,
        "Charts":                   render_data_visual_analysis,
        "Business Visual Analysis": render_business_visual_analysis,
        "Pivot Tables":             _render_pivot_placeholder,
        "Dashboard Studio":         render_visual_builder,
        "AI Analyst":               render_ai_analyst_workspace,
        "Dataset Manager":          render_dataset_manager,
        "Workflow Monitor":         render_workflow_monitor,
        "Knowledge Center":         render_knowledge_center,
        "Evaluation Dashboard":     render_evaluation_dashboard,
        "Session History":          render_session_history,
        "Job Monitor":              render_job_monitor,
        "Storage Manager":          render_storage_manager,
        "Dataset Versions":         render_dataset_versions,
        "Artifact Browser":         render_artifact_browser,
        "Storage Statistics":       render_storage_statistics,
        "System Health":            render_system_health,
        "Metrics Dashboard":        render_metrics_dashboard,
        "Application Status":       render_application_status,
        "Dependency Status":        render_dependency_status,
        "Configuration Viewer":     render_configuration_viewer,
        "Billing Dashboard":        render_billing_dashboard,
        "Usage Dashboard":          render_usage_dashboard,
        "Subscription Management":  render_subscription_management,
        "API Key Manager":          render_api_key_manager,
        "Admin Dashboard":          render_admin_dashboard,
        "System Analytics":         render_system_analytics,
        "Organization Billing":     render_organization_billing,
        "AI Chat":                  render_ai_chat,
        "AI Insights":              render_ai_insights,
        "Reports":                  render_reports,
        "Storyboard Builder":       render_storyboard_builder,
        "Location Insights":        render_location_insights,
        "SQL Lab":                  render_sql_lab,
        "DAX Studio":               render_dax_studio,
        "Settings":                 render_settings,
        "Login":                    render_login,
        "Register":                 render_register,
        "Profile":                  render_profile,
        "Change Password":          render_change_password,
        "Organizations":            render_organizations,
        "Workspace Manager":        render_workspace_manager,
        "Members":                  render_members,
        "Invitations":              render_invitations,
        "Roles":                    render_roles,
        "Permissions":              render_permissions,
    }
    renderer = dispatch.get(canonical) or dispatch.get(page)
    if renderer is not None:
        renderer(client)
    else:
        st.error(f'Page "{page}" not found.')


def _render_pivot_placeholder(client) -> None:
    """Placeholder for the Pivot Tables feature (roadmap item)."""
    st.header("Pivot Tables")
    st.info(
        "The interactive Pivot Table explorer is coming soon. "
        "In the meantime, use the **Dashboard** or **Charts** pages for grouped summaries."
    )
    from frontend.utils.local_helpers import select_dataset
    import pandas as pd
    dataset_id = select_dataset(client)
    if not dataset_id:
        return
    from frontend.utils.backend_utils import is_local_dataset_id
    local_df: pd.DataFrame | None = st.session_state.get("local_dataframes", {}).get(dataset_id)
    if local_df is not None and not local_df.empty:
        st.subheader("Simple Pivot Preview")
        num_cols = local_df.select_dtypes("number").columns.tolist()
        cat_cols = local_df.select_dtypes(["object", "category"]).columns.tolist()
        if num_cols and cat_cols:
            c1, c2, c3 = st.columns(3)
            row_col = c1.selectbox("Row (index)", cat_cols, key="pivot_row")
            val_col = c2.selectbox("Value", num_cols, key="pivot_val")
            agg = c3.selectbox("Aggregation", ["sum", "mean", "count", "min", "max"], key="pivot_agg")
            try:
                pivot = local_df.pivot_table(values=val_col, index=row_col, aggfunc=agg)
                st.dataframe(pivot, use_container_width=True)
            except Exception as exc:
                st.warning(f"Could not build pivot: {exc}")
        else:
            st.dataframe(local_df.head(25), use_container_width=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    initialize_session_state()

    from frontend.components.ux_states import error_panel, inject_ux_css
    from frontend.design_system import apply_design_system, ensure_session_palette

    apply_design_system()
    inject_ux_css()
    ensure_session_palette()

    # ── Sidebar top: connection (collapsed for non-technical users) ───────
    with st.sidebar:
        with st.expander("Connection", expanded=False):
            api_base_url = st.text_input(
                "Backend API URL",
                value=st.session_state.get("api_base_url", DEFAULT_API_BASE_URL),
                key="api_base_url_input",
                help="Usually leave as default unless your API runs on another host.",
            )
            st.session_state["api_base_url"] = api_base_url
            render_backend_status(get_client(api_base_url))
        api_base_url = st.session_state.get("api_base_url", DEFAULT_API_BASE_URL)

    client = get_client(api_base_url)

    # Load branding once per session
    if "branding_loaded" not in st.session_state:
        initialize_session_state(get_active_branding(client))
        st.session_state["branding_loaded"] = True
    else:
        initialize_session_state()

    _apply_branding_theme()

    # ── Sidebar: Active Dataset switcher (Power BI–style) ────────────────
    from frontend.components.active_dataset import (
        render_active_dataset_banner,
        render_sidebar_dataset_switcher,
    )

    render_sidebar_dataset_switcher(client)

    # ── Sidebar: navigation ───────────────────────────────────────────────
    current_page = st.session_state.get("current_page", "Home")
    _render_sidebar_nav(current_page)

    # ── Sidebar: AI command box ───────────────────────────────────────────
    _render_ai_command_box()

    # ── Main area ─────────────────────────────────────────────────────────
    branding = st.session_state["branding"]
    company = branding.get("company_name", "AI Analytics")

    if current_page != "Home":
        st.sidebar.caption(f"© {company}")
        render_active_dataset_banner()

    try:
        _dispatch_page(current_page, client)
    except Exception as exc:
        import traceback

        error_panel(
            f"Something went wrong on **{current_page}**. Your other pages still work.",
            suggestion="Try Home, or Retry after checking the API connection.",
            retry_key=f"page_err_retry_{current_page}",
        )
        with st.expander("Technical details (for debugging)", expanded=False):
            st.code(f"{exc}\n\n{traceback.format_exc()}")

    if branding.get("footer_note"):
        st.caption(branding["footer_note"])


if __name__ == "__main__":
    main()
