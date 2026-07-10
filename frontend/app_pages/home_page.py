"""Home / landing page.

Shown by default when the application starts.  Provides:
- Welcome hero with backend connection status
- Active dataset summary (rows, columns, domain, quality score)
- Recent datasets list with quick-navigate buttons
- Quick-action buttons for the core workflow
- Domain-aware suggested AI questions
- Mini KPI preview if a dataset is already loaded
"""
from __future__ import annotations

import html
from typing import Any

import pandas as pd
import requests
import streamlit as st

from frontend.api_client.backend_client import BackendClient
from frontend.utils.backend_utils import check_backend_connection, is_local_dataset_id
from frontend.utils.session_state import navigate_to, track_recent_dataset


# ── Internal helpers ─────────────────────────────────────────────────────────


def _esc(v: Any) -> str:
    return html.escape(str(v or ""))


def _card(icon: str, label: str, value: Any, sub: str = "") -> str:
    return (
        f'<div class="home-stat-card">'
        f'<div class="home-stat-icon">{icon}</div>'
        f'<div class="home-stat-label">{_esc(label)}</div>'
        f'<div class="home-stat-value">{_esc(value)}</div>'
        f'<div class="home-stat-sub">{_esc(sub)}</div>'
        f'</div>'
    )


def _inject_home_css() -> None:
    st.markdown(
        """
        <style>
        .home-hero {
            padding: 1.5rem 1.75rem;
            border-radius: 16px;
            background: linear-gradient(135deg, var(--brand-primary), var(--brand-secondary));
            color: #FFFFFF;
            margin-bottom: 1.25rem;
        }
        .home-hero h1 { color: #FFFFFF; font-size: 1.8rem; font-weight: 900; margin: 0 0 .3rem; }
        .home-hero p  { color: rgba(255,255,255,.85); font-size: 1rem; margin: 0; }

        .home-stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
            gap: 12px;
            margin: 1rem 0;
        }
        .home-stat-card {
            background: var(--surface-card);
            border: 1px solid color-mix(in srgb, var(--brand-primary) 20%, var(--surface-border));
            border-top: 4px solid var(--brand-accent);
            border-radius: var(--theme-radius, 8px);
            padding: .85rem 1rem;
            box-shadow: var(--theme-shadow, 0 1px 4px rgba(0,0,0,.06));
        }
        .home-stat-icon { font-size: 1.4rem; margin-bottom: .3rem; }
        .home-stat-label { font-size: .75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: .05em; }
        .home-stat-value { font-size: 1.35rem; font-weight: 900; color: var(--brand-primary); }
        .home-stat-sub   { font-size: .78rem; color: var(--text-subtle, #888); margin-top: .2rem; }

        .home-quick-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 10px;
            margin: 1rem 0;
        }
        .home-recent-row {
            display: flex;
            align-items: center;
            gap: .75rem;
            padding: .55rem .75rem;
            border-radius: 8px;
            border: 1px solid var(--surface-border);
            background: var(--surface-card);
            margin-bottom: .4rem;
        }
        .home-recent-name { font-weight: 700; font-size: .9rem; color: var(--text-color); flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .home-recent-ts   { font-size: .75rem; color: var(--text-muted); white-space: nowrap; }

        .home-ai-pill {
            display: inline-block;
            padding: .35rem .75rem;
            border-radius: 999px;
            border: 1px solid color-mix(in srgb, var(--brand-primary) 35%, var(--surface-border));
            background: color-mix(in srgb, var(--brand-primary) 8%, transparent);
            color: var(--brand-primary);
            font-size: .82rem;
            font-weight: 700;
            margin: .2rem .2rem .2rem 0;
            cursor: pointer;
        }
        .home-section-title {
            font-size: .78rem;
            font-weight: 900;
            color: var(--text-muted);
            letter-spacing: .07em;
            text-transform: uppercase;
            margin: 1.2rem 0 .5rem;
        }
        .home-conn-ok   { color: #22C55E; font-weight: 700; }
        .home-conn-warn { color: #F59E0B; font-weight: 700; }
        .home-workflow-step {
            display: flex;
            align-items: center;
            gap: .6rem;
            padding: .5rem .7rem;
            border-radius: 8px;
            background: color-mix(in srgb, var(--brand-primary) 6%, transparent);
            margin-bottom: .35rem;
            font-size: .88rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _workflow_arrow_css() -> str:
    return (
        '<div style="text-align:center;color:var(--text-muted);font-size:1.2rem;line-height:1;">↓</div>'
    )


# ── AI question suggestions ───────────────────────────────────────────────────

_DOMAIN_QUESTIONS: dict[str, list[str]] = {
    "Customer Churn": [
        "Which customers are at highest churn risk?",
        "What drives churn in the top revenue segment?",
        "Compare churn rate by contract type",
        "Find anomalies in customer tenure",
        "Generate executive churn report",
    ],
    "Sales": [
        "Compare Sales and Profit by region",
        "Which products have the highest margin?",
        "Show revenue trend over time",
        "Find underperforming sales segments",
        "Create executive sales dashboard",
    ],
    "Healthcare": [
        "Identify high-risk patient groups",
        "Show admission trends by department",
        "Find anomalies in patient outcomes",
        "Compare readmission rates by age group",
        "Generate clinical summary report",
    ],
    "Finance": [
        "Show profit and loss summary",
        "Find anomalies in transaction data",
        "Compare margin by product line",
        "Identify highest-risk accounts",
        "Generate financial KPI dashboard",
    ],
    "General": [
        "Summarize this dataset",
        "Find anomalies and outliers",
        "Show key trends over time",
        "What are the top 5 insights?",
        "Generate executive dashboard",
    ],
}


def _domain_questions(domain: str) -> list[str]:
    for key in _DOMAIN_QUESTIONS:
        if key.lower() in domain.lower():
            return _DOMAIN_QUESTIONS[key]
    return _DOMAIN_QUESTIONS["General"]


# ── Active dataset summary ────────────────────────────────────────────────────

def _active_dataset_info() -> dict[str, Any]:
    """Collect active dataset metadata from session state without API calls."""
    dataset_id: str | None = (
        st.session_state.get("active_dataset_id")
        or st.session_state.get("selected_dataset_id")
    )
    if not dataset_id:
        return {}

    info: dict[str, Any] = {"dataset_id": dataset_id}

    # Filename
    uploaded_datasets: dict = st.session_state.get("uploaded_datasets", {})
    meta = uploaded_datasets.get(dataset_id, {})
    info["filename"] = meta.get("original_filename") or meta.get("filename") or dataset_id

    # DataFrame stats (local)
    local_df: pd.DataFrame | None = st.session_state.get("local_dataframes", {}).get(dataset_id)
    if local_df is not None and not local_df.empty:
        info["rows"] = len(local_df)
        info["cols"] = len(local_df.columns)

    # Domain
    domain_ctx: dict = st.session_state.get("active_detected_domain", {})
    info["domain"] = domain_ctx.get("domain", st.session_state.get("detected_domain", ""))
    info["is_local"] = is_local_dataset_id(dataset_id)
    return info


# ── Section renderers ─────────────────────────────────────────────────────────

def _render_hero(branding: dict, conn_status: dict) -> None:
    company = branding.get("company_name", "AI Analytics")
    subtitle = branding.get("report_subtitle", "Upload a dataset to generate board-ready KPIs, charts, and insights.")
    conn_html = (
        '<span class="home-conn-ok">● Backend connected</span>'
        if conn_status.get("connected")
        else '<span class="home-conn-warn">● Local analysis mode</span>'
    )
    st.markdown(
        f"""
        <div class="home-hero">
            <h1>{_esc(company)}</h1>
            <p>{_esc(subtitle)}</p>
            <p style="margin-top:.5rem;font-size:.82rem;">{conn_html}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_dataset_summary(ds_info: dict) -> None:
    if not ds_info:
        st.info("No dataset is active yet. Upload a CSV or Excel file to begin.")
        return

    cards = [
        _card("📄", "Dataset", ds_info.get("filename", "—")),
        _card("📊", "Rows", f"{ds_info.get('rows', '—'):,}" if isinstance(ds_info.get("rows"), int) else "—"),
        _card("🗂️", "Columns", str(ds_info.get("cols", "—"))),
        _card("🏷️", "Domain", ds_info.get("domain") or "Auto-detected", "Detected from data"),
        _card("🔌", "Source", "Local" if ds_info.get("is_local") else "Backend"),
    ]
    st.markdown(
        f'<div class="home-stat-grid">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )


def _render_quick_actions() -> None:
    st.markdown('<div class="home-section-title">Quick Actions</div>', unsafe_allow_html=True)
    cols = st.columns(5)
    actions = [
        ("⬆️ Upload", "Upload"),
        ("📊 Dashboard", "Dashboard"),
        ("🤖 AI Analyst", "AI Analyst"),
        ("📋 Reports", "Reports"),
        ("📽️ Storyboard", "Storyboard"),
    ]
    for col, (label, page) in zip(cols, actions):
        if col.button(label, use_container_width=True, key=f"home_qa_{page}"):
            navigate_to(page)
            st.rerun()


def _render_workflow_guide() -> None:
    st.markdown('<div class="home-section-title">Recommended Workflow</div>', unsafe_allow_html=True)
    steps = [
        ("1", "⬆️", "Upload Data", "Upload"),
        ("2", "🔍", "Analyze", "Dashboard"),
        ("3", "🤖", "Ask AI", "AI Analyst"),
        ("4", "📊", "Dashboard", "Dashboard Studio"),
        ("5", "📋", "Export Report", "Reports"),
    ]
    for num, icon, label, page in steps:
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(
                f'<div class="home-workflow-step"><b>{num}.</b> {icon} {_esc(label)}</div>',
                unsafe_allow_html=True,
            )
        with col2:
            if st.button("Go", key=f"home_wf_{num}", use_container_width=True):
                navigate_to(page)
                st.rerun()


def _render_recent_datasets() -> None:
    recent: list[dict] = st.session_state.get("recent_datasets", [])
    if not recent:
        return
    st.markdown('<div class="home-section-title">Recent Datasets</div>', unsafe_allow_html=True)
    for item in recent[:5]:
        name = item.get("filename") or item.get("dataset_id", "Dataset")
        ts = item.get("visited_at", "")[:10]
        col1, col2 = st.columns([6, 1])
        col1.markdown(
            f'<div class="home-recent-row">'
            f'<span class="home-recent-name">📂 {_esc(name)}</span>'
            f'<span class="home-recent-ts">{_esc(ts)}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if col2.button("Open", key=f"home_recent_{item.get('dataset_id', name)}", use_container_width=True):
            st.session_state["active_dataset_id"] = item["dataset_id"]
            st.session_state["selected_dataset_id"] = item["dataset_id"]
            navigate_to("Dashboard")
            st.rerun()


def _render_ai_suggestions(domain: str) -> None:
    questions = _domain_questions(domain)
    st.markdown('<div class="home-section-title">Suggested AI Questions</div>', unsafe_allow_html=True)
    pills_html = "".join(
        f'<span class="home-ai-pill">{_esc(q)}</span>' for q in questions
    )
    st.markdown(pills_html, unsafe_allow_html=True)
    st.caption("Click a question in the AI Analyst page to get instant insights.")


def _render_connection_diagnostics(client: BackendClient, conn_status: dict) -> None:
    with st.expander("Connection diagnostics", expanded=False):
        st.markdown(f"**Backend URL:** `{client.base_url}`")
        if conn_status.get("connected"):
            st.success(
                f"Connected · version {conn_status.get('version') or 'unknown'}"
                + (f" · {conn_status['latency_ms']} ms" if conn_status.get("latency_ms") is not None else "")
            )
        else:
            st.warning(conn_status.get("error") or "Backend unavailable.")
            st.info(
                "The app works in **local analysis mode** when the backend is offline. "
                "Upload data, run cleaning, generate charts and export reports without a server connection."
            )
        if st.button("Re-check connection", key="home_recheck"):
            from frontend.utils.backend_utils import invalidate_backend_status_cache
            invalidate_backend_status_cache()
            st.rerun()


# ── Main entry ────────────────────────────────────────────────────────────────

def render_home(client: BackendClient) -> None:
    _inject_home_css()

    branding: dict = st.session_state.get("branding", {})
    conn_status = check_backend_connection(client)
    ds_info = _active_dataset_info()

    _render_hero(branding, conn_status)

    left, right = st.columns([3, 2])

    with left:
        st.subheader("Active Dataset")
        _render_dataset_summary(ds_info)

        _render_quick_actions()

    with right:
        _render_workflow_guide()

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        _render_recent_datasets()
    with col_b:
        domain = ds_info.get("domain") or st.session_state.get("detected_domain", "General")
        _render_ai_suggestions(domain)

    st.divider()
    _render_connection_diagnostics(client, conn_status)
