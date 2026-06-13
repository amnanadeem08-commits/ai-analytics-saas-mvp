import html

import streamlit as st


SEVERITY_COLORS = {
    "success": "#16A34A",
    "warning": "#D97706",
    "error": "#DC2626",
    "info": "#2563EB",
}


def render_insight(insight: dict) -> None:
    severity = insight.get("severity", "info")
    color = SEVERITY_COLORS.get(severity, SEVERITY_COLORS["info"])
    title = html.escape(str(insight.get("title", "Insight")))
    message = html.escape(str(insight.get("message", "")))
    st.markdown(
        f"""
        <div style="
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-left: 4px solid {color};
            border-radius: 8px;
            padding: 12px 14px;
            margin-bottom: 10px;
            background: rgba(255,255,255,0.04);
        ">
            <div style="font-weight: 800; color: var(--text-color); margin-bottom: 4px;">{title}</div>
            <div style="font-size: 0.9rem; color: rgba(100,116,139,0.98); line-height: 1.45;">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if insight.get("metadata"):
        with st.expander(f"Evidence: {title}", expanded=False):
            st.json(insight["metadata"])
