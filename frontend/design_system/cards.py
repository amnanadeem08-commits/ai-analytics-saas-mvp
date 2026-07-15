from __future__ import annotations

"""Card primitives — section, KPI, metric (Streamlit-native, no raw HTML)."""

import streamlit as st


def section_card(title: str, body: str | None = None, *, caption: str | None = None) -> None:
    st.subheader(title)
    if caption:
        st.caption(caption)
    if body:
        st.write(body)


def kpi_card(label: str, value: object, *, hint: str | None = None, delta: str | None = None) -> None:
    """Native Streamlit metric — no raw HTML."""
    st.metric(label, value, delta=delta, help=hint)


def metric_cards(items: list[tuple[str, object, str | None]]) -> None:
    """items: (label, value, help_text?). Uses Streamlit metrics only."""
    if not items:
        return
    cols = st.columns(len(items))
    for col, (label, value, help_text) in zip(cols, items):
        with col:
            st.metric(label, value, help=help_text)


def rich_kpi_grid(
    cards: list[dict],
    *,
    key_prefix: str = "kpi",
    on_add_to_storyboard=None,
    on_add_to_report=None,
) -> None:
    """Render API KPI payloads with title, value, description, and tooltips."""
    if not cards:
        return

    st.subheader("Key metrics")
    st.caption("From the active dataset — use the ⓘ on each metric for definitions")

    label_map = {
        "Entities": "Distinct categories",
        "Entity Count": "Distinct categories",
        "Records": "Row count",
        "Fields": "Column count",
    }

    for offset in range(0, min(len(cards), 8), 4):
        cols = st.columns(4)
        for card_index, (col, card) in enumerate(zip(cols, cards[offset : offset + 4]), start=offset):
            label = str(card.get("label") or card.get("name") or "Metric")
            label = label_map.get(label, label)
            value = card.get("formatted_value", card.get("value", "—"))
            if not card.get("formatted_value") and card.get("format") == "percent" and isinstance(value, (int, float)):
                value = f"{value}%"
            delta = card.get("delta_percentage")
            trend_arrow = str(card.get("trend_arrow") or "").strip()
            delta_text = None
            if delta is not None:
                delta_text = f"{trend_arrow} {delta}%".strip() if trend_arrow else f"{delta}%"
            help_bits = [
                card.get("business_context") or card.get("description") or "",
                card.get("statistical_explanation") or "",
                f"Reason: {card['reason']}" if card.get("reason") else "",
                f"Action: {card['recommended_action']}" if card.get("recommended_action") else "",
            ]
            help_text = " · ".join(b for b in help_bits if b) or None
            with col:
                st.metric(label, value, delta=delta_text, help=help_text)
                context = card.get("business_context") or card.get("description")
                if context:
                    st.caption(str(context)[:160])
                risk = card.get("risk_indicator")
                conf = card.get("confidence_score")
                meta_parts = []
                if risk:
                    meta_parts.append(f"Risk: {str(risk).title()}")
                if conf is not None:
                    try:
                        meta_parts.append(f"Confidence: {round(float(conf) * 100)}%")
                    except (TypeError, ValueError):
                        pass
                if meta_parts:
                    st.caption(" · ".join(meta_parts))
                action = card.get("recommended_action")
                if action:
                    with st.expander("Recommendation", expanded=False):
                        st.write(action)
                        if card.get("expected_impact"):
                            st.caption(f"Impact: {card['expected_impact']}")
                if on_add_to_storyboard or on_add_to_report:
                    kpi_id = card.get("kpi_id") or label.replace(" ", "_").lower()
                    key_suffix = f"{key_prefix}_{kpi_id}_{card_index}"
                    a1, a2 = st.columns(2)
                    if on_add_to_storyboard and a1.button("Storyboard", key=f"{key_suffix}_storyboard", use_container_width=True):
                        on_add_to_storyboard(card)
                    if on_add_to_report and a2.button("Report", key=f"{key_suffix}_report", use_container_width=True):
                        on_add_to_report(card)
