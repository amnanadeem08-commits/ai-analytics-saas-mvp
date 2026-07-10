"""AI Chat page.

A lightweight conversational interface that wraps the backend ``ask_question``
endpoint.  Works in local mode too by generating simple heuristic answers from
the in-session dataframe.

History is kept in ``st.session_state["ai_conversation_history"]`` so it
survives page navigation within the same session.
"""
from __future__ import annotations

import html
from typing import Any

import pandas as pd
import requests
import streamlit as st

from frontend.api_client.backend_client import BackendClient
from frontend.utils.backend_utils import is_local_dataset_id
from frontend.utils.session_state import append_ai_conversation
from frontend.utils.local_helpers import select_dataset


# ── Suggested prompts ─────────────────────────────────────────────────────────

_PROMPT_EXAMPLES = [
    "Summarize this dataset",
    "What are the top 5 insights?",
    "Find anomalies and outliers",
    "Compare key metrics by category",
    "Show revenue trends over time",
    "Which segment has the highest risk?",
    "What should I focus on first?",
    "Explain the main patterns",
]


# ── Local fallback ────────────────────────────────────────────────────────────

def _local_answer(df: pd.DataFrame, question: str) -> str:
    """Very simple heuristic response for local mode (no LLM needed)."""
    q = question.strip().lower()
    rows, cols = len(df), len(df.columns)
    if any(kw in q for kw in ("summarize", "summary", "overview")):
        numeric_cols = df.select_dtypes("number").columns.tolist()
        return (
            f"This dataset has **{rows:,} rows** and **{cols} columns**. "
            f"Numeric columns: {', '.join(numeric_cols[:6]) or 'none detected'}. "
            "Connect the backend for full AI analysis."
        )
    if any(kw in q for kw in ("anomal", "outlier")):
        return (
            "Local anomaly detection is available on the **AI Insights** page. "
            "For AI-powered anomaly narratives, connect the backend."
        )
    if any(kw in q for kw in ("trend", "over time", "time series")):
        date_cols = [c for c in df.columns if "date" in c.lower() or "time" in c.lower() or "year" in c.lower()]
        if date_cols:
            return f"Possible time columns detected: **{', '.join(date_cols[:3])}**. Use the Charts page to explore trends."
        return "No date/time columns detected. Use the Charts page to explore distributions."
    return (
        f"Your dataset has **{rows:,} rows** and **{cols} columns**. "
        "Connect the backend for AI-powered answers to this question."
    )


# ── Chat message renderer ─────────────────────────────────────────────────────

def _render_message(role: str, text: str) -> None:
    icon = "🤖" if role == "assistant" else "🧑"
    align = "left" if role == "assistant" else "right"
    bg = "var(--surface-card)" if role == "assistant" else "color-mix(in srgb, var(--brand-primary) 12%, transparent)"
    st.markdown(
        f"""
        <div style="display:flex;justify-content:{align};margin:.4rem 0;">
          <div style="max-width:80%;padding:.65rem .85rem;border-radius:12px;
                      background:{bg};border:1px solid var(--surface-border);
                      font-size:.9rem;line-height:1.5;">
            <span style="font-size:.8rem;opacity:.6;">{icon}</span>
            &nbsp;{html.escape(text)}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def render_ai_chat(client: BackendClient) -> None:
    st.header("AI Chat")
    st.caption(
        "Ask questions about your data in plain language. "
        "Full AI answers require a backend connection; local mode provides structural hints."
    )

    dataset_id = select_dataset(client)
    if not dataset_id:
        st.info("Select or upload a dataset to start chatting with your data.")
        return

    # Resolve local dataframe for local-mode fallback
    local_df: pd.DataFrame | None = None
    if is_local_dataset_id(dataset_id):
        local_df = st.session_state.get("local_dataframes", {}).get(dataset_id)

    backend_available = not is_local_dataset_id(dataset_id) and st.session_state.get("backend_connected", False)

    # ── Conversation history ──────────────────────────────────────────────
    history: list[dict[str, Any]] = st.session_state.get("ai_conversation_history", [])

    if history:
        # Show messages scoped to the active dataset (simple prefix filter)
        ds_history = [m for m in history if m.get("dataset_id") == dataset_id or "dataset_id" not in m]
        for msg in ds_history[-20:]:
            _render_message(msg["role"], msg["text"])
    else:
        st.info("Ask your first question below, or choose a suggestion.")

    # ── Suggested prompts ─────────────────────────────────────────────────
    with st.expander("Suggested prompts", expanded=not history):
        cols = st.columns(2)
        for i, prompt in enumerate(_PROMPT_EXAMPLES):
            if cols[i % 2].button(prompt, key=f"chat_suggestion_{i}", use_container_width=True):
                st.session_state["ai_chat_pending"] = prompt
                st.rerun()

    # ── Input ─────────────────────────────────────────────────────────────
    with st.form("ai_chat_form", clear_on_submit=True):
        question = st.text_area(
            "Your question",
            value=st.session_state.pop("ai_chat_pending", ""),
            placeholder="e.g. Which customers are at highest churn risk?",
            height=90,
            key="ai_chat_input_field",
        )
        submitted = st.form_submit_button("Send", type="primary", use_container_width=True)

    if submitted and question.strip():
        user_q = question.strip()
        append_ai_conversation("user", user_q)
        # Tag with dataset id for filtering
        st.session_state["ai_conversation_history"][-1]["dataset_id"] = dataset_id

        with st.spinner("Thinking…"):
            if backend_available:
                try:
                    result = client.ask_question(dataset_id, user_q)
                    answer = (
                        result.get("answer")
                        or result.get("response")
                        or result.get("text")
                        or str(result)
                    )
                except requests.RequestException as exc:
                    answer = f"Backend unavailable: {BackendClient._friendly_error(exc)}"
            elif local_df is not None:
                answer = _local_answer(local_df, user_q)
            else:
                answer = (
                    "Backend connection is required for AI answers. "
                    "Start the backend server and reload, or upload a local CSV to use local hints."
                )

        append_ai_conversation("assistant", answer)
        st.session_state["ai_conversation_history"][-1]["dataset_id"] = dataset_id
        st.rerun()

    # ── Clear history ─────────────────────────────────────────────────────
    if history and st.button("Clear conversation", key="chat_clear", use_container_width=False):
        st.session_state["ai_conversation_history"] = []
        st.rerun()
