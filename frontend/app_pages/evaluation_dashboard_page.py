from __future__ import annotations

"""Evaluation Dashboard — score/report views via evaluation API."""

import streamlit as st

from frontend.utils.workspace_api import get_workspace_clients, show_api_error


def render_evaluation_dashboard(client=None) -> None:
    st.header("Evaluation Dashboard")
    st.caption("Inspect evaluation scores through `/api/v1/evaluation/*`.")

    evaluation = get_workspace_clients()["evaluation"]
    session_id = st.text_input(
        "Session id",
        value=st.session_state.get("active_analyst_session_id") or "",
    )
    evaluation_id = st.text_input(
        "Evaluation id",
        value=st.session_state.get("last_evaluation_id") or "",
    )
    workflow_id = st.text_input("Workflow id", value="")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Load by session", use_container_width=True) and session_id.strip():
            try:
                payload = evaluation.by_session(session_id.strip())
                st.session_state["evaluation_view"] = payload
                st.session_state["last_evaluation_id"] = payload.get("evaluation_id")
            except Exception as exc:
                show_api_error(exc)
    with c2:
        if st.button("Load report", use_container_width=True) and evaluation_id.strip():
            try:
                payload = evaluation.report(evaluation_id.strip())
                st.session_state["evaluation_report_view"] = payload
                st.session_state["last_evaluation_id"] = payload.get("evaluation_id")
            except Exception as exc:
                show_api_error(exc)
    with c3:
        if st.button("Load by workflow", use_container_width=True) and workflow_id.strip():
            try:
                payload = evaluation.by_workflow(workflow_id.strip())
                st.session_state["evaluation_view"] = payload
                st.session_state["last_evaluation_id"] = payload.get("evaluation_id")
            except Exception as exc:
                show_api_error(exc)

    view = st.session_state.get("evaluation_view")
    report_view = st.session_state.get("evaluation_report_view")

    if view:
        st.subheader("Score summary")
        m1, m2, m3 = st.columns(3)
        m1.metric("Overall score", view.get("overall_score", "—"))
        m2.metric("Grade", view.get("grade", "—"))
        summary = view.get("score_summary") or {}
        m3.metric("Metrics", summary.get("metric_count", "—"))
        cats = summary.get("category_scores") or view.get("category_scores") or {}
        if cats:
            st.bar_chart(cats)

    if report_view:
        st.subheader("Report")
        report = report_view.get("report") or {}
        st.write(report.get("summary") or "")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Strengths**")
            for item in report.get("strengths") or []:
                st.markdown(f"- {item}")
        with c2:
            st.markdown("**Weaknesses**")
            for item in report.get("weaknesses") or []:
                st.markdown(f"- {item}")
        st.markdown("**Recommendations**")
        for item in report.get("recommendations") or []:
            st.markdown(f"- {item}")
        with st.expander("Category scores / metrics"):
            st.json(
                {
                    "category_scores": report_view.get("category_scores") or {},
                    "metrics": report_view.get("metrics") or [],
                }
            )

    export_id = (evaluation_id or st.session_state.get("last_evaluation_id") or "").strip()
    if export_id and st.button("Export JSON"):
        try:
            export_payload = evaluation.export(export_id)
            st.json(export_payload.get("export") or export_payload)
        except Exception as exc:
            show_api_error(exc)

    if not view and not report_view:
        st.info("Load an evaluation by session, workflow, or evaluation id.")
