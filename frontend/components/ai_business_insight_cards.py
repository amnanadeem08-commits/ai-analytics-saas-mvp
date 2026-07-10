from __future__ import annotations

import html
from typing import Any

import streamlit as st

TYPE_COLORS = {
    "Opportunity": "var(--ui-success)",
    "Risk": "var(--ui-danger)",
    "Trend": "var(--ui-info)",
    "Outlier Interpretation": "var(--ui-warning)",
    "Forecast": "var(--brand-primary)",
}


def _confidence_label(score: Any) -> str:
    try:
        value = float(score)
    except (TypeError, ValueError):
        value = 0.0
    if value > 1:
        value /= 100
    if value >= 0.75:
        return "High"
    if value >= 0.45:
        return "Medium"
    if value > 0:
        return "Low"
    return "Insufficient"


def render_ai_business_insight_cards(payload: dict[str, Any] | None) -> None:
    cards = (payload or {}).get("cards") or []
    st.subheader("AI Business Insights")
    if not cards:
        st.info("AI Business Insight cards are not available yet.")
        return

    st.markdown(
        """
        <style>
        .ai-bi-card { border: 1px solid var(--surface-border); border-radius: 8px; padding: 14px 16px; margin-bottom: 12px; background: var(--surface-card); }
        .ai-bi-top { display: flex; justify-content: space-between; gap: 10px; align-items: flex-start; margin-bottom: 8px; }
        .ai-bi-title { color: var(--text-color); font-weight: 900; font-size: 1.02rem; }
        .ai-bi-badges { display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }
        .ai-bi-badge { border-radius: 999px; padding: 3px 9px; color: white; font-size: .72rem; font-weight: 800; white-space: nowrap; }
        .ai-bi-label { color: var(--text-muted); text-transform: uppercase; font-size: .68rem; font-weight: 850; margin-top: 8px; }
        .ai-bi-body { color: var(--text-color); font-size: .9rem; line-height: 1.42; margin-top: 2px; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    for card in cards:
        card_type = str(card.get("type") or "Insight")
        color = TYPE_COLORS.get(card_type, "var(--ui-info)")
        confidence = _confidence_label(card.get("confidence_score"))
        title = html.escape(str(card.get("title") or card_type))
        sections = [
            ("Business Meaning", card.get("business_meaning")),
            ("Supporting Evidence", card.get("supporting_evidence")),
            ("Expected Business Impact", card.get("expected_business_impact")),
            ("Executive Recommendation", card.get("executive_recommendation")),
        ]
        section_html = "".join(
            f'<div class="ai-bi-label">{html.escape(label)}</div><div class="ai-bi-body">{html.escape(str(value or "Not available."))}</div>'
            for label, value in sections
        )
        st.markdown(
            f"""
            <div class="ai-bi-card">
                <div class="ai-bi-top">
                    <div class="ai-bi-title">{title}</div>
                    <div class="ai-bi-badges">
                        <span class="ai-bi-badge" style="background:{color};">{html.escape(card_type)}</span>
                        <span class="ai-bi-badge" style="background:var(--text-muted);">Confidence: {html.escape(confidence)}</span>
                    </div>
                </div>
                {section_html}
            </div>
            """,
            unsafe_allow_html=True,
        )
