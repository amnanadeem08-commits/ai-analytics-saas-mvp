from __future__ import annotations

"""Session History — previous analyst sessions via session API."""

import streamlit as st

from frontend.utils.session_state import navigate_to
from frontend.utils.workspace_api import get_workspace_clients, remember_session, show_api_error


def render_session_history(client=None) -> None:
    st.header("Session History")
    st.caption("Browse previous AI Analyst sessions and resume analysis.")

    clients = get_workspace_clients()
    analyst = clients["analyst"]
    history = list(st.session_state.get("analyst_session_history", []))

    if not history:
        st.info("No sessions yet. Run an analysis from the AI Analyst page.")
        if st.button("Go to AI Analyst"):
            navigate_to("AI Analyst")
            st.rerun()
        return

    for item in history:
        session_id = item.get("session_id")
        query = item.get("query") or ""
        with st.expander(f"{session_id} — {query[:80]}"):
            st.write(f"**Query:** {query}")
            try:
                summary = analyst.session_summary(str(session_id))
                st.json(summary)
            except Exception as exc:
                show_api_error(exc)
                summary = {}

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("Resume", key=f"resume_{session_id}"):
                    remember_session(str(session_id), query=query, summary=summary)
                    navigate_to("AI Analyst")
                    st.rerun()
            with c2:
                if st.button("Open evaluation", key=f"eval_{session_id}"):
                    try:
                        evaluation = analyst.session_evaluation(str(session_id))
                        st.session_state["last_evaluation_id"] = evaluation.get("evaluation_id")
                        st.session_state["evaluation_report_view"] = evaluation
                        navigate_to("Evaluation Dashboard")
                        st.rerun()
                    except Exception as exc:
                        show_api_error(exc)
            with c3:
                if st.button("Refresh detail", key=f"detail_{session_id}"):
                    try:
                        detail = analyst.get_session(str(session_id))
                        st.json(detail)
                    except Exception as exc:
                        show_api_error(exc)
