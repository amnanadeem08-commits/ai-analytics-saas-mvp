from __future__ import annotations

"""AI Analyst workspace page — communicates only via `/api/v1` HTTP clients."""

import streamlit as st

from frontend.components.ux_states import page_intro, section_header, success_banner
from frontend.utils.session_state import navigate_to
from frontend.utils.workspace_api import get_workspace_clients, remember_session, show_api_error


def _render_structured_answer(
    answer: str,
    insights: list,
    recommendations: list,
    *,
    next_actions: list | None = None,
    charts: list | None = None,
) -> None:
    """Organize analyst output into executive-friendly sections."""
    tabs = st.tabs(
        [
            "Executive Summary",
            "Key Insights",
            "Charts",
            "Recommendations",
            "Next Actions",
        ]
    )
    with tabs[0]:
        st.markdown(answer or "_No summary returned._")
    with tabs[1]:
        if insights:
            for item in insights:
                st.markdown(f"- {item}")
        else:
            st.caption("No discrete insights in this response.")
    with tabs[2]:
        if charts:
            for chart in charts:
                st.write(chart)
        else:
            st.caption("No chart specs in this response. Open Dashboard or Charts for visuals.")
    with tabs[3]:
        if recommendations:
            for item in recommendations:
                st.markdown(f"- {item}")
        else:
            st.caption("No recommendations returned.")
    with tabs[4]:
        actions = next_actions or [
            "Open Workflow Monitor to inspect the run",
            "Review Evaluation Dashboard for quality scores",
            "Export findings from Reports or Storyboard",
        ]
        for item in actions:
            st.markdown(f"- {item}")


def render_ai_analyst_workspace(client=None) -> None:
    """Chat-style AI Analyst page backed by POST /api/v1/analyst/analyze."""
    page_intro(
        "AI Analyst",
        "Ask natural-language questions. Analysis runs through the FastAPI `/api/v1` gateway.",
        workflow_index=4,
    )

    clients = get_workspace_clients()
    analyst = clients["analyst"]

    try:
        health = clients["system"].health()
        success_banner(f"API connected · status={health.get('status', 'ok')}")
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
            if msg.get("role") == "assistant":
                _render_structured_answer(
                    msg.get("content", ""),
                    list(msg.get("insights") or []),
                    list(msg.get("recommendations") or []),
                    next_actions=msg.get("next_actions"),
                    charts=msg.get("charts"),
                )
            else:
                st.markdown(msg.get("content", ""))
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
            charts = list(result.get("charts") or result.get("visuals") or [])
            next_actions = list(result.get("next_actions") or [])
            session_id = result.get("session_id")
            _render_structured_answer(
                answer,
                insights,
                recommendations,
                next_actions=next_actions or None,
                charts=charts or None,
            )

            grade = result.get("evaluation_grade")
            score = result.get("evaluation_score")
            if grade or score is not None:
                st.caption(f"Evaluation: grade={grade} score={score}")

            assistant_msg = {
                "role": "assistant",
                "content": answer,
                "insights": insights,
                "recommendations": recommendations,
                "charts": charts,
                "next_actions": next_actions,
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
    section_header("Continue the workflow", "Inspect runs, scores, or start fresh")
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
