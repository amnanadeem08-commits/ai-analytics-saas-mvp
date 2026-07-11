from __future__ import annotations

"""Job Monitor page (Sprint 8.3) — background jobs via `/api/v1/jobs` only."""

import streamlit as st

from frontend.api.base import friendly_api_error
from frontend.api.job_client import JobClient
from frontend.components.ux_states import (
    empty_state,
    page_intro,
    render_status_badge,
    section_header,
    success_banner,
)
from frontend.utils.auth_state import is_authenticated, with_auto_refresh
from frontend.utils.workspace_api import get_api_client


def _client() -> JobClient:
    return JobClient(get_api_client())


def _error(exc: Exception) -> None:
    st.error(friendly_api_error(exc))


def render_job_monitor(client=None) -> None:
    page_intro(
        "Job Monitor",
        "Submit and track background jobs through the FastAPI `/api/v1/jobs` gateway.",
    )

    if not is_authenticated():
        empty_state(
            "Sign in to manage jobs",
            "Background jobs require an authenticated session.",
            primary_label="Go to Login",
            primary_page="Login",
            key="jobs_login",
        )
        return

    jobs = _client()

    try:
        stats = with_auto_refresh(lambda t: jobs.statistics(t)).get("statistics", {})
        section_header("Queue health")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total", stats.get("total_jobs", 0))
        c2.metric("Queued", stats.get("queued_depth", 0))
        c3.metric("Dead-letter", stats.get("dead_letter_depth", 0))
        c4.metric("Backend", stats.get("backend", "memory"))
    except Exception as exc:
        _error(exc)

    st.divider()
    section_header("Submit a job", "Choose a type and optional payload fields")
    with st.form("submit_job_form"):
        job_type = st.selectbox(
            "Job type",
            ["analysis", "workflow_execution", "evaluation", "knowledge_ingestion", "generic"],
        )
        query = st.text_input("Query (analysis/workflow)", value="Analyze revenue decline")
        session_id = st.text_input("Session id (evaluation)", value="")
        title = st.text_input("Title (knowledge)", value="")
        content = st.text_area("Content (knowledge)", value="")
        priority = st.selectbox("Priority", ["low", "normal", "high", "critical"], index=1)
        inline = st.checkbox("Run inline (synchronous)", value=True)
        submitted = st.form_submit_button("Submit job", type="primary")

    if submitted:
        payload: dict = {}
        if job_type in {"analysis", "workflow_execution"}:
            payload["query"] = query
        elif job_type == "evaluation":
            payload["session_id"] = session_id
        elif job_type == "knowledge_ingestion":
            payload["title"] = title
            payload["content"] = content
        elif job_type == "generic":
            payload["echo"] = "hello"
            payload["steps"] = 3
        try:
            result = with_auto_refresh(
                lambda t: jobs.submit(t, job_type=job_type, payload=payload, priority=priority, inline=inline)
            )
            job = result.get("job", {})
            success_banner(f"Job `{job.get('job_id')}` submitted")
            render_status_badge(str(job.get("status") or "queued"), job.get("status"))
            st.session_state["last_job_id"] = job.get("job_id")
        except Exception as exc:
            _error(exc)

    st.divider()
    section_header("Job history", "Progress, cancel, and retry")
    only_mine = st.checkbox("Only my jobs", value=False)
    try:
        listing = with_auto_refresh(lambda t: jobs.list(t, mine=only_mine))
        job_list = listing.get("jobs", [])
        st.caption(f"{len(job_list)} job(s)")
        if not job_list:
            empty_state(
                "No jobs yet",
                "Submit a job above to see progress and history here.",
                key="jobs_empty",
            )
            return
        for job in job_list:
            status = str(job.get("status") or "pending")
            header_cols = st.columns([4, 1])
            with header_cols[0]:
                st.markdown(
                    f"**{job.get('job_type')}** · `{job.get('job_id')}`"
                )
            with header_cols[1]:
                render_status_badge(status.replace("_", " ").title(), status)
            with st.expander("Details", expanded=status in {"running", "queued", "pending", "retrying"}):
                progress = job.get("progress", {}) or {}
                pct = float(progress.get("percent", 0) or 0)
                st.progress(min(1.0, pct / 100.0))
                st.caption(progress.get("message", "") or f"{pct:.0f}% complete")
                if job.get("result"):
                    with st.expander("Result JSON", expanded=False):
                        st.json(job["result"])
                if job.get("error"):
                    st.error(job["error"])
                c1, c2 = st.columns(2)
                with c1:
                    if job.get("status") in {"pending", "queued", "running", "retrying"}:
                        if st.button("Cancel", key=f"cancel_{job['job_id']}"):
                            try:
                                with_auto_refresh(lambda t: jobs.cancel(t, job["job_id"]))
                                st.rerun()
                            except Exception as exc:
                                _error(exc)
                with c2:
                    if job.get("status") in {"failed", "cancelled", "dead_letter"}:
                        if st.button("Retry", key=f"retry_{job['job_id']}"):
                            try:
                                with_auto_refresh(lambda t: jobs.retry(t, job["job_id"], inline=True))
                                st.rerun()
                            except Exception as exc:
                                _error(exc)
    except Exception as exc:
        _error(exc)
