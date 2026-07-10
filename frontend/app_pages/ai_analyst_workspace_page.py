from __future__ import annotations

"""AI Analyst workspace page — communicates only via `/api/v1` HTTP clients."""

import streamlit as st

from frontend.utils.session_state import navigate_to
from frontend.utils.workspace_api import get_workspace_clients, remember_session, show_api_error


def render_ai_analyst_workspace(client=None) -> None:
    """Chat-style AI Analyst page backed by POST /api/v1/analyst/analyze."""
    st.header("AI Analyst")
    st.caption("Ask natural-language questions. All analysis runs through the FastAPI `/api/v1` gateway.")

    clients = get_workspace_clients()
    analyst = clients["analyst"]

    # Connection probe
    try:
        health = clients["system"].health()
        st.success(f"API connected · status={health.get('status', 'ok')}")
    except Exception as exc:
        show_api_error(exc)
        st.info("Start the FastAPI backend to use the AI Analyst workspace.")
        return

    dataset_id = st.session_state.get("active_dataset_id") or st.session_state.get("selected_dataset_id")
    active_session = st.session_state.get("active_analyst_session_id")

    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.markdown(f"**Active session:** `{active_session or 'none'}`")
    with col_b:
        st.markdown(f"**Dataset:** `{dataset_id or 'none'}`")

    history = list(st.session_state.get("ai_analyst_messages", []))
    for msg in history:
        with st.chat_message(msg.get("role", "assistant")):
            st.markdown(msg.get("content", ""))
            if msg.get("insights"):
                st.markdown("**Insights**")
                for item in msg["insights"]:
                    st.markdown(f"- {item}")
            if msg.get("recommendations"):
                st.markdown("**Recommendations**")
                for item in msg["recommendations"]:
                    st.markdown(f"- {item}")
            meta_bits = []
            if msg.get("evaluation_grade"):
                meta_bits.append(f"Grade {msg['evaluation_grade']}")
            if msg.get("evaluation_score") is not None:
                meta_bits.append(f"Score {msg['evaluation_score']}")
            if msg.get("session_id"):
                meta_bits.append(f"Session `{msg['session_id']}`")
            if meta_bits:
                st.caption(" · ".join(meta_bits))

    prompt = st.chat_input("Ask a question about your data…")
    follow_up = bool(active_session)
    if prompt:
        history.append({"role": "user", "content": prompt})
        st.session_state["ai_analyst_messages"] = history
        with st.chat_message("user"):
            st.markdown(prompt)

        user_context = {}
        initial_context = {}
        if dataset_id:
            user_context["dataset_id"] = dataset_id
            initial_context["dataset_id"] = dataset_id

        with st.chat_message("assistant"):
            with st.spinner("Running AI Analyst via `/api/v1/analyst/analyze`…"):
                try:
                    result = analyst.analyze(
                        prompt,
                        user_context=user_context,
                        session_id=active_session,
                        follow_up=follow_up,
                        initial_context=initial_context,
                    )
                except Exception as exc:
                    show_api_error(exc)
                    return

            answer = result.get("answer") or "No answer returned."
            insights = list(result.get("insights") or [])
            recommendations = list(result.get("recommendations") or [])
            session_id = result.get("session_id")
            st.markdown(answer)
            if insights:
                st.markdown("**Insights**")
                for item in insights:
                    st.markdown(f"- {item}")
            if recommendations:
                st.markdown("**Recommendations**")
                for item in recommendations:
                    st.markdown(f"- {item}")

            grade = result.get("evaluation_grade")
            score = result.get("evaluation_score")
            if grade or score is not None:
                st.caption(f"Evaluation: grade={grade} score={score}")

            assistant_msg = {
                "role": "assistant",
                "content": answer,
                "insights": insights,
                "recommendations": recommendations,
                "session_id": session_id,
                "evaluation_id": result.get("evaluation_id"),
                "evaluation_grade": grade,
                "evaluation_score": score,
                "workflow_id": result.get("workflow_id"),
            }
            history.append(assistant_msg)
            st.session_state["ai_analyst_messages"] = history
            if session_id:
                remember_session(session_id, query=prompt, summary={"answer": answer, "grade": grade})
                if result.get("workflow_results", {}).get("execution_id"):
                    st.session_state["active_workflow_execution_id"] = result["workflow_results"]["execution_id"]
                st.session_state["last_evaluation_id"] = result.get("evaluation_id")

        st.rerun()

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Open Workflow Monitor", use_container_width=True):
            navigate_to("Workflow Monitor")
            st.rerun()
    with c2:
        if st.button("Open Evaluation Dashboard", use_container_width=True):
            navigate_to("Evaluation Dashboard")
            st.rerun()
    with c3:
        if st.button("Clear conversation", use_container_width=True):
            st.session_state["ai_analyst_messages"] = []
            st.rerun()
