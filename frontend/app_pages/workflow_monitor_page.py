from __future__ import annotations

"""Workflow Monitor — consumes workflow API endpoints only."""

import streamlit as st

from frontend.utils.workspace_api import (
    get_workspace_clients,
    remember_execution,
    show_api_error,
)


def render_workflow_monitor(client=None) -> None:
    st.header("Workflow Monitor")
    st.caption("Execute and inspect workflows through `/api/v1/workflow/*`.")

    clients = get_workspace_clients()
    workflow = clients["workflow"]

    dataset_id = st.session_state.get("active_dataset_id") or st.session_state.get("selected_dataset_id")
    query = st.text_input(
        "Analyst workflow query",
        value=st.session_state.get("workflow_monitor_query", "Analyze revenue decline"),
    )
    st.session_state["workflow_monitor_query"] = query
    include_eval = st.checkbox("Include evaluation stage", value=True)

    if st.button("Execute workflow", type="primary"):
        with st.spinner("POST `/api/v1/workflow/execute`…"):
            try:
                result = workflow.execute(
                    query=query,
                    dataset_id=dataset_id,
                    include_evaluation=include_eval,
                    initial_context={"dataset_id": dataset_id} if dataset_id else {},
                )
                execution_id = result.get("execution_id")
                if execution_id:
                    remember_execution(
                        execution_id,
                        query=query,
                        status=str(result.get("status") or ""),
                    )
                st.success(f"Execution `{execution_id}` · status={result.get('status')}")
                st.json(result)
            except Exception as exc:
                show_api_error(exc)

    history = list(st.session_state.get("workflow_execution_history", []))
    options = [h["execution_id"] for h in history if h.get("execution_id")]
    active = st.session_state.get("active_workflow_execution_id")
    if active and active not in options:
        options.insert(0, active)
    execution_id = st.selectbox(
        "Inspect execution",
        options=options or [""],
        index=0 if options else 0,
    )
    manual_id = st.text_input("Or enter execution id", value=execution_id or "")
    target = (manual_id or execution_id or "").strip()
    if not target:
        st.info("Execute a workflow or paste an execution id to inspect status/results.")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Refresh status", use_container_width=True):
            try:
                st.session_state["workflow_status_view"] = workflow.status(target)
            except Exception as exc:
                show_api_error(exc)
    with c2:
        if st.button("Load results", use_container_width=True):
            try:
                st.session_state["workflow_results_view"] = workflow.results(target)
            except Exception as exc:
                show_api_error(exc)
    with c3:
        if st.button("Statistics", use_container_width=True):
            try:
                st.session_state["workflow_stats_view"] = workflow.statistics(target)
            except Exception as exc:
                show_api_error(exc)

    status_view = st.session_state.get("workflow_status_view")
    if status_view:
        st.subheader("Status")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Status", status_view.get("status", "—"))
        m2.metric("Completed", status_view.get("completed_stages", 0))
        m3.metric("Failed", status_view.get("failed_stages", 0))
        m4.metric("Errors", status_view.get("error_count", 0))

    results_view = st.session_state.get("workflow_results_view")
    if results_view:
        st.subheader("Stage results")
        stages = results_view.get("stage_results") or []
        if stages:
            st.dataframe(stages, use_container_width=True)
        ctx = results_view.get("context") or {}
        if ctx.get("evaluation_score") is not None or ctx.get("evaluation_grade"):
            st.markdown(
                f"**Evaluation score:** {ctx.get('evaluation_score')} · "
                f"**Grade:** {ctx.get('evaluation_grade')}"
            )
        with st.expander("Context snapshot"):
            st.json(ctx)

    stats_view = st.session_state.get("workflow_stats_view")
    if stats_view:
        st.subheader("Statistics")
        st.json(stats_view)
