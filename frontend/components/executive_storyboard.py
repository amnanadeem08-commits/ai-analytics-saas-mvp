from __future__ import annotations

import html
from typing import Any

import streamlit as st

from frontend.components.ai_business_insight_cards import render_ai_business_insight_cards
from frontend.components.chart_components import PLOTLY_CONFIG, _prepare_figure


MAX_PREVIEW_CHARTS = 4


def _section(payload: dict[str, Any], section_id: str) -> dict[str, Any]:
    return next((section for section in payload.get("sections", []) if section.get("section_id") == section_id), {})


def _escape(value: Any) -> str:
    return html.escape(str(value or ""))


def _first_text(*values: Any, fallback: str = "Not available") -> str:
    for value in values:
        if value not in (None, "", [], {}):
            return str(value)
    return fallback


def _confidence_label(value: Any = None) -> str:
    if isinstance(value, (int, float)):
        return f"{round(float(value))}% confidence"
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "Evidence-backed confidence"


def _metric(label: str, value: Any, helper: str = "") -> str:
    return f"""
    <div class="exec-metric-card">
        <div class="exec-story-label">{_escape(label)}</div>
        <div class="exec-story-value">{_escape(value)}</div>
        <div class="exec-story-helper">{_escape(helper)}</div>
    </div>
    """


def _badge(label: str, modifier: str = "") -> str:
    class_name = f"exec-badge {modifier}".strip()
    return f'<span class="{class_name}">{_escape(label)}</span>'


def _block_header(number: str, headline: str, summary: str, confidence: Any = None) -> None:
    st.markdown(
        f"""
        <div class="exec-block-head">
            <div>
                <div class="exec-kicker">{_escape(number)}</div>
                <h2>{_escape(headline)}</h2>
                <p>{_escape(summary)}</p>
            </div>
            <div class="exec-confidence">{_escape(_confidence_label(confidence))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _recommendation_strip(text: Any, label: str = "Business Recommendation") -> None:
    st.markdown(
        f"""
        <div class="exec-rec-strip">
            <div class="exec-story-label">{_escape(label)}</div>
            <div class="exec-rec-text">{_escape(_first_text(text, fallback='No recommendation is available yet.'))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_kpi_cards(kpis: list[dict[str, Any]], limit: int = 4) -> None:
    if not kpis:
        st.info("No KPI cards are available for this dataset.")
        return

    st.markdown('<div class="exec-metric-grid">', unsafe_allow_html=True)
    cards = []
    for card in kpis[:limit]:
        cards.append(
            _metric(
                str(card.get("label", "KPI")),
                card.get("value", "N/A"),
                _first_text(card.get("business_context"), card.get("description"), card.get("status"), fallback=""),
            )
        )
    st.markdown("".join(cards), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def _chart_matches(chart: dict[str, Any], keywords: set[str]) -> bool:
    text = " ".join(
        str(chart.get(key, "")) for key in ("title", "chart_type", "kind", "description", "business_context")
    ).lower()
    return any(keyword in text for keyword in keywords)


def _select_charts(charts: list[dict[str, Any]], *, keywords: set[str] | None = None, limit: int = MAX_PREVIEW_CHARTS) -> list[dict[str, Any]]:
    if not charts:
        return []
    if keywords:
        matched = [chart for chart in charts if _chart_matches(chart, keywords)]
        if matched:
            return matched[:limit]
    return charts[:limit]


def _render_charts(charts: list[dict[str, Any]], *, prefix: str, empty: str = "No chart-ready visuals were generated for this dataset.") -> None:
    if not charts:
        st.info(empty)
        return

    for offset in range(0, len(charts), 2):
        cols = st.columns(2)
        for index, (col, chart) in enumerate(zip(cols, charts[offset : offset + 2]), start=offset):
            fig = _prepare_figure(chart)
            with col:
                if fig is None:
                    st.info(f"{chart.get('title', 'Chart')} has no renderable trace data.")
                    continue
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    config=PLOTLY_CONFIG,
                    key=f"{prefix}_{index}_{chart.get('chart_id')}",
                )
                st.caption(chart.get("title", "Executive chart"))


def _render_ai_card_summaries(cards: list[dict[str, Any]], limit: int = 3) -> None:
    if not cards:
        st.info("No AI Business Insight cards are available yet.")
        return

    for card in cards[:limit]:
        st.markdown(
            f"""
            <div class="exec-insight-card">
                <div class="exec-badges">
                    {_badge(card.get('type', 'Insight'), 'exec-badge-primary')}
                    {_badge(_confidence_label(card.get('confidence')))}
                </div>
                <div class="exec-insight-title">{_escape(card.get('title', 'AI insight'))}</div>
                <div class="exec-story-helper">{_escape(_first_text(card.get('business_meaning'), card.get('supporting_evidence'), fallback='Evidence is available in AI Business Insights.'))}</div>
                <div class="exec-card-body">{_escape(_first_text(card.get('executive_recommendation'), card.get('recommendation'), fallback='Use this insight in leadership review.'))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _extract_story_parts(payload: dict[str, Any]) -> dict[str, Any]:
    summary = (_section(payload, "executive_summary") or {}).get("content") or {}
    kpis = _section(payload, "kpi_overview").get("kpis") or []
    ai_cards = _section(payload, "ai_business_insights").get("cards") or []
    charts = _section(payload, "executive_charts").get("charts") or []
    recommendations = _section(payload, "executive_recommendations").get("recommendations") or []
    return {"summary": summary, "kpis": kpis, "ai_cards": ai_cards, "charts": charts, "recommendations": recommendations}


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --exec-ink: var(--text-color);
            --exec-muted: var(--text-muted);
            --exec-soft: var(--surface-alt);
            --exec-paper: var(--surface-card);
            --exec-panel: var(--ui-surface);
            --exec-line: var(--surface-border);
            --exec-blue: var(--brand-primary);
            --exec-teal: var(--ui-success);
            --exec-gold: var(--brand-accent);
            --exec-shadow: var(--theme-shadow);
        }

        .exec-story-wrap {
            display: grid;
            gap: 22px;
            color: var(--exec-ink);
        }

        .exec-block {
            border: 1px solid var(--exec-line);
            border-radius: 8px;
            background: var(--exec-paper);
            box-shadow: var(--exec-shadow);
            padding: 28px;
        }

        .exec-cover {
            min-height: 360px;
            display: grid;
            grid-template-columns: minmax(0, 1.25fr) minmax(280px, .75fr);
            gap: 26px;
            align-items: stretch;
            background: linear-gradient(135deg, var(--surface-card) 0%, var(--ui-surface) 58%, var(--surface-alt) 100%);
        }

        .exec-cover h1 {
            margin: 0;
            color: var(--exec-ink);
            font-size: 2.55rem;
            line-height: 1.02;
            font-weight: 900;
            letter-spacing: 0;
        }

        .exec-cover-copy {
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 22px;
        }

        .exec-cover-sub {
            color: var(--exec-muted);
            font-size: 1rem;
            line-height: 1.55;
            max-width: 780px;
            margin-top: 14px;
        }

        .exec-cover-panel {
            border-left: 4px solid var(--exec-blue);
            background: color-mix(in srgb, var(--surface-card) 72%, transparent);
            padding: 20px;
            display: grid;
            gap: 14px;
        }

        .exec-block-head {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 18px;
            align-items: start;
            border-bottom: 1px solid var(--exec-line);
            padding-bottom: 16px;
            margin-bottom: 18px;
        }

        .exec-block-head h2 {
            margin: 0;
            color: var(--exec-ink);
            font-size: 1.58rem;
            line-height: 1.15;
            font-weight: 900;
            letter-spacing: 0;
        }

        .exec-block-head p {
            color: var(--exec-muted);
            font-size: .96rem;
            line-height: 1.45;
            margin: 8px 0 0;
        }

        .exec-kicker {
            color: var(--exec-blue);
            font-size: .73rem;
            font-weight: 900;
            letter-spacing: .08em;
            text-transform: uppercase;
            margin-bottom: 8px;
        }

        .exec-confidence {
            border: 1px solid color-mix(in srgb, var(--exec-teal) 34%, var(--exec-line));
            color: var(--exec-teal);
            background: color-mix(in srgb, var(--exec-teal) 9%, white);
            border-radius: 999px;
            padding: 8px 12px;
            font-size: .78rem;
            font-weight: 850;
            white-space: nowrap;
        }

        .exec-metric-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin: 10px 0 4px;
        }

        .exec-metric-card {
            border: 1px solid var(--exec-line);
            border-radius: 8px;
            padding: 15px;
            background: var(--exec-panel);
            min-height: 118px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .exec-story-label {
            color: var(--exec-muted);
            font-size: .7rem;
            font-weight: 850;
            text-transform: uppercase;
            letter-spacing: .04em;
        }

        .exec-story-value {
            color: var(--exec-ink);
            font-size: 1.28rem;
            font-weight: 900;
            margin-top: 8px;
            line-height: 1.2;
            overflow-wrap: anywhere;
        }

        .exec-story-helper {
            color: var(--exec-muted);
            font-size: .82rem;
            margin-top: 7px;
            line-height: 1.38;
        }

        .exec-two-col {
            display: grid;
            grid-template-columns: minmax(0, .9fr) minmax(0, 1.1fr);
            gap: 18px;
            align-items: start;
        }

        .exec-insight-card, .exec-rec-strip {
            border: 1px solid var(--exec-line);
            border-radius: 8px;
            background: var(--surface-card);
            padding: 15px;
            margin-bottom: 12px;
        }

        .exec-insight-title {
            color: var(--exec-ink);
            font-size: 1rem;
            font-weight: 900;
            line-height: 1.25;
            margin-bottom: 6px;
        }

        .exec-card-body {
            border-top: 1px solid var(--exec-line);
            color: var(--exec-ink);
            padding-top: 11px;
            margin-top: 12px;
            line-height: 1.42;
            font-size: .9rem;
        }

        .exec-rec-strip {
            border-left: 4px solid var(--exec-gold);
            background: color-mix(in srgb, var(--exec-gold) 7%, white);
            margin-top: 16px;
        }

        .exec-rec-text {
            color: var(--exec-ink);
            font-size: .94rem;
            font-weight: 720;
            line-height: 1.42;
            margin-top: 6px;
        }

        .exec-badges { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
        .exec-badge {
            display: inline-flex;
            align-items: center;
            padding: 5px 9px;
            border-radius: 999px;
            border: 1px solid var(--exec-line);
            color: var(--exec-muted);
            background: var(--exec-panel);
            font-size: .74rem;
            font-weight: 850;
        }
        .exec-badge-primary {
            border-color: color-mix(in srgb, var(--exec-blue) 45%, var(--exec-line));
            color: var(--exec-blue);
            background: color-mix(in srgb, var(--exec-blue) 9%, white);
        }

        .exec-footer {
            color: var(--exec-muted);
            font-size: .82rem;
            text-align: right;
            padding: 2px 4px 8px;
        }

        @media (max-width: 1120px) {
            .exec-cover, .exec-two-col { grid-template-columns: 1fr; }
            .exec-metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .exec-block-head { grid-template-columns: 1fr; }
            .exec-confidence { width: fit-content; }
        }

        @media (max-width: 720px) {
            .exec-block { padding: 20px; }
            .exec-cover h1 { font-size: 2rem; }
            .exec-metric-grid { grid-template-columns: 1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(summary: dict[str, Any]) -> None:
    readiness = summary.get("dataset_readiness") or {}
    st.markdown('<section class="exec-block exec-cover">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="exec-cover-copy">
            <div>
                <div class="exec-kicker">01 Executive Cover</div>
                <h1>Executive Storyboard</h1>
                <div class="exec-cover-sub">{_escape(_first_text(summary.get('executive_summary'), fallback='Presentation-ready overview from validated Data Insights, AI Business Insights, and Dashboard visuals.'))}</div>
            </div>
            <div class="exec-badges">
                {_badge('Existing storyboard payload', 'exec-badge-primary')}
                {_badge('AI insights reused')}
                {_badge('Dashboard visuals reused')}
            </div>
        </div>
        <div class="exec-cover-panel">
            {_metric('Dataset Readiness', f"{readiness.get('score', 0)}/100", readiness.get('reason', ''))}
            {_metric('Business Health', f"{summary.get('overall_business_health', 0)}/100", 'Validated from current evidence')}
            {_metric('Confidence', _confidence_label(summary.get('confidence')), 'No storyboard regeneration performed')}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("</section>", unsafe_allow_html=True)


def render_business_health(payload: dict[str, Any]) -> None:
    parts = _extract_story_parts(payload)
    summary = parts["summary"]
    recommendations = parts["recommendations"]
    st.markdown('<section class="exec-block">', unsafe_allow_html=True)
    _block_header(
        "02 Business Health",
        "Current health, readiness, and leadership context",
        _first_text(summary.get("executive_summary"), fallback="A concise operating view assembled from existing storyboard evidence."),
        summary.get("confidence"),
    )
    readiness = summary.get("dataset_readiness") or {}
    st.markdown(
        '<div class="exec-metric-grid">'
        + _metric("Dataset Readiness", f"{readiness.get('score', 0)}/100", readiness.get("reason", ""))
        + _metric("Overall Business Health", f"{summary.get('overall_business_health', 0)}/100", "Board-level health index")
        + _metric("Top Opportunity", summary.get("top_opportunity", "Not available"), "Where leadership can create value")
        + _metric("Biggest Risk", summary.get("biggest_risk", "Not available"), "Where attention is needed")
        + "</div>",
        unsafe_allow_html=True,
    )
    _recommendation_strip((recommendations[:1] or [{}])[0].get("recommendation") or summary.get("top_opportunity"))
    st.markdown("</section>", unsafe_allow_html=True)


def render_kpi_section(payload: dict[str, Any]) -> None:
    parts = _extract_story_parts(payload)
    st.markdown('<section class="exec-block">', unsafe_allow_html=True)
    _block_header(
        "03 KPI Summary",
        "Performance indicators for executive review",
        "KPI cards are reused from the existing storyboard payload and arranged for fast comparison.",
    )
    _render_kpi_cards(parts["kpis"], limit=8)
    _recommendation_strip(_first_text((parts["recommendations"][:1] or [{}])[0].get("recommendation"), fallback="Prioritize KPI movements with the clearest operational owner."))
    st.markdown("</section>", unsafe_allow_html=True)


def render_ai_insights(payload: dict[str, Any]) -> None:
    ai_cards = _section(payload, "ai_business_insights").get("cards") or []
    st.markdown('<section class="exec-block">', unsafe_allow_html=True)
    _block_header(
        "04 AI Business Insights",
        "Decision intelligence from existing AI cards",
        "The original AI Business Insight cards are reused directly to preserve evidence and recommendation lineage.",
    )
    render_ai_business_insight_cards({"cards": ai_cards})
    if ai_cards:
        _recommendation_strip(_first_text(ai_cards[0].get("executive_recommendation"), ai_cards[0].get("recommendation")))
    st.markdown("</section>", unsafe_allow_html=True)


def render_charts(payload: dict[str, Any]) -> None:
    parts = _extract_story_parts(payload)
    st.markdown('<section class="exec-block">', unsafe_allow_html=True)
    _block_header(
        "05 Dashboard Visuals",
        "Charts already prepared by Dashboard Studio",
        "Visuals are rendered from the existing chart specifications; no chart is regenerated for the storyboard.",
    )
    _render_charts(_select_charts(parts["charts"], limit=MAX_PREVIEW_CHARTS), prefix="exec_story_chart")
    _recommendation_strip(_first_text((parts["recommendations"][:1] or [{}])[0].get("recommendation"), fallback="Use the strongest visual as the opening evidence slide."))
    st.markdown("</section>", unsafe_allow_html=True)


def render_trends(payload: dict[str, Any]) -> None:
    parts = _extract_story_parts(payload)
    trend_charts = _select_charts(parts["charts"], keywords={"trend", "time", "date", "month", "year", "line"}, limit=2)
    st.markdown('<section class="exec-block">', unsafe_allow_html=True)
    _block_header(
        "06 Trends",
        "Directional movement and time-based signals",
        "Trend evidence is selected from existing dashboard visuals when available.",
    )
    cols = st.columns([0.38, 0.62])
    with cols[0]:
        _render_ai_card_summaries(parts["ai_cards"], limit=2)
    with cols[1]:
        _render_charts(trend_charts, prefix="exec_story_trend", empty="No trend-specific dashboard visual is available; using the existing dashboard visuals above.")
    _recommendation_strip("Translate sustained directional movement into one owner, one metric, and one review cadence.")
    st.markdown("</section>", unsafe_allow_html=True)


def render_risks(payload: dict[str, Any]) -> None:
    parts = _extract_story_parts(payload)
    risk_cards = [card for card in parts["ai_cards"] if "risk" in str(card).lower() or "anomal" in str(card).lower()]
    st.markdown('<section class="exec-block">', unsafe_allow_html=True)
    _block_header(
        "07 Risks",
        "Issues that could affect confidence or performance",
        _first_text(parts["summary"].get("biggest_risk"), fallback="Risks are inferred from existing AI cards and executive recommendations."),
    )
    _render_ai_card_summaries(risk_cards or parts["ai_cards"], limit=3)
    _recommendation_strip(_first_text(parts["summary"].get("biggest_risk"), (parts["recommendations"][:1] or [{}])[0].get("recommendation")))
    st.markdown("</section>", unsafe_allow_html=True)


def render_opportunities(payload: dict[str, Any]) -> None:
    parts = _extract_story_parts(payload)
    opportunity_cards = [card for card in parts["ai_cards"] if "opportun" in str(card).lower() or "growth" in str(card).lower()]
    st.markdown('<section class="exec-block">', unsafe_allow_html=True)
    _block_header(
        "08 Opportunities",
        "Value creation themes for leadership action",
        _first_text(parts["summary"].get("top_opportunity"), fallback="Opportunities are drawn from existing insight and recommendation evidence."),
    )
    _render_ai_card_summaries(opportunity_cards or parts["ai_cards"], limit=3)
    _recommendation_strip(_first_text(parts["summary"].get("top_opportunity"), (parts["recommendations"][:1] or [{}])[0].get("recommendation")))
    st.markdown("</section>", unsafe_allow_html=True)


def render_recommendations(payload: dict[str, Any]) -> None:
    recommendations = _section(payload, "executive_recommendations").get("recommendations") or []
    st.markdown('<section class="exec-block">', unsafe_allow_html=True)
    _block_header(
        "09 Recommendations",
        "Ranked management actions",
        "Recommendations are reused from the existing storyboard payload and organized by priority, impact, and difficulty.",
    )
    if not recommendations:
        st.info("No ranked recommendations are available yet.")
    else:
        for rec in recommendations[:8]:
            st.markdown(
                f"""
                <div class="exec-insight-card">
                    <div class="exec-badges">
                        {_badge(f"{rec.get('priority', 'Medium')} priority", 'exec-badge-primary')}
                        {_badge(f"Value: {rec.get('business_value', 'Not available')}")}
                        {_badge(f"Difficulty: {rec.get('difficulty', 'Not available')}")}
                        {_badge(f"Impact: {rec.get('expected_impact', 'Not available')}")}
                    </div>
                    <div class="exec-insight-title">{_escape(rec.get('title', 'Recommendation'))}</div>
                    <div class="exec-card-body">{_escape(rec.get('recommendation', ''))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown("</section>", unsafe_allow_html=True)


def render_footer(payload: dict[str, Any] | None = None) -> None:
    parts = _extract_story_parts(payload or {}) if payload else {"summary": {}, "recommendations": []}
    summary = parts["summary"]
    recommendations = parts["recommendations"]
    st.markdown('<section class="exec-block">', unsafe_allow_html=True)
    _block_header(
        "10 Executive Conclusion",
        "Board-ready closing view",
        _first_text(summary.get("executive_summary"), fallback="The storyboard is ready for executive review using the current evidence set."),
        summary.get("confidence"),
    )
    st.markdown(
        '<div class="exec-metric-grid">'
        + _metric("Decision Focus", _first_text(summary.get("top_opportunity"), fallback="Align on the highest-value action"), "Opportunity")
        + _metric("Control Focus", _first_text(summary.get("biggest_risk"), fallback="Track the highest-risk assumption"), "Risk")
        + _metric("Next Action", _first_text((recommendations[:1] or [{}])[0].get("title"), fallback="Assign ownership"), "Recommendation")
        + _metric("Confidence", _confidence_label(summary.get("confidence")), "Evidence preserved")
        + "</div>",
        unsafe_allow_html=True,
    )
    _recommendation_strip(_first_text((recommendations[:1] or [{}])[0].get("recommendation"), fallback="Move the selected recommendation into the next executive operating review."), label="Closing Recommendation")
    st.markdown("</section>", unsafe_allow_html=True)
    st.markdown('<div class="exec-footer">Storyboard UI uses existing payload, AI cards, and dashboard chart specifications.</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_executive_storyboard(payload: dict[str, Any] | None) -> None:
    if not payload:
        st.info("Executive Storyboard is not available yet.")
        return

    _inject_styles()
    parts = _extract_story_parts(payload)

    st.markdown('<div class="exec-story-wrap">', unsafe_allow_html=True)
    render_header(parts["summary"])
    render_business_health(payload)
    render_kpi_section(payload)
    render_ai_insights(payload)
    render_charts(payload)
    render_trends(payload)
    render_risks(payload)
    render_opportunities(payload)
    render_recommendations(payload)
    render_footer(payload)
