import streamlit as st


SEVERITY_RENDERERS = {
    "success": st.success,
    "warning": st.warning,
    "error": st.error,
    "info": st.info,
}


def render_insight(insight: dict) -> None:
    renderer = SEVERITY_RENDERERS.get(insight.get("severity", "info"), st.info)
    renderer(f"**{insight.get('title', 'Insight')}**\n\n{insight.get('message', '')}")
