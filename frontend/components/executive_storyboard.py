from __future__ import annotations

from dataclasses import dataclass, field
import html
from typing import Any

import streamlit as st

from frontend.components.ai_business_insight_cards import render_ai_business_insight_cards
from frontend.components.chart_components import PLOTLY_CONFIG, _prepare_figure


MAX_PREVIEW_CHARTS = 4


@dataclass(slots=True)
class ReportContext:
    payload: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    kpis: list[dict[str, Any]] = field(default_factory=list)
    ai_cards: list[dict[str, Any]] = field(default_factory=list)
    charts: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    ranked_recommendations: list[dict[str, Any]] = field(default_factory=list)
    prioritized_risk_cards: list[dict[str, Any]] = field(default_factory=list)
    prioritized_opportunity_cards: list[dict[str, Any]] = field(default_factory=list)


def _escape(value: Any) -> str:
    return html.escape(str(value or ""))


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _as_score(value: Any, default: int = 0) -> int:
    try:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return default
        score = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(0, min(100, score))


def _priority_level_score(value: Any, *, default: int = 50) -> int:
    if isinstance(value, (int, float)):
        return _as_score(value, default=default)
    text = str(value or "").strip().lower()
    if not text:
        return default

    if any(token in text for token in ("critical", "severe", "urgent", "immediate", "p0", "very high")):
        return 100
    if any(token in text for token in ("high", "major", "p1")):
        return 85
    if any(token in text for token in ("medium", "moderate", "p2")):
        return 60
    if any(token in text for token in ("low", "minor", "p3")):
        return 35
    return default


def _difficulty_score(value: Any) -> int:
    if isinstance(value, (int, float)):
        return _as_score(value, default=50)
    text = str(value or "").strip().lower()
    if not text:
        return 50
    if any(token in text for token in ("low", "easy", "simple", "quick")):
        return 30
    if any(token in text for token in ("medium", "moderate")):
        return 55
    if any(token in text for token in ("high", "hard", "complex", "difficult")):
        return 80
    return 50


def _text_relevance_score(value: Any, keywords: set[str]) -> int:
    text = str(value or "").lower()
    if not text:
        return 0
    return sum(1 for keyword in keywords if keyword in text) * 12


def _recommendation_priority_score(rec: dict[str, Any]) -> int:
    priority = _priority_level_score(rec.get("priority"), default=60)
    value_score = _priority_level_score(rec.get("business_value"), default=55)
    impact_score = _priority_level_score(rec.get("expected_impact"), default=55)
    difficulty_penalty = _difficulty_score(rec.get("difficulty"))

    evidence_score = _text_relevance_score(
        " ".join(
            str(rec.get(key, ""))
            for key in ("title", "recommendation", "rationale", "business_value", "expected_impact")
        ),
        {"revenue", "cost", "margin", "retention", "risk", "growth", "churn", "profit"},
    )

    # Higher impact/value and lower difficulty should bubble up.
    raw = (0.35 * priority) + (0.30 * value_score) + (0.25 * impact_score) + (0.10 * (100 - difficulty_penalty))
    return max(0, min(100, int(round(raw + min(evidence_score, 10)))))


def _rank_recommendations(recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for rec in recommendations:
        rec_with_score = {**rec, "priority_score": _recommendation_priority_score(rec)}
        ranked.append(rec_with_score)
    return sorted(ranked, key=lambda item: int(item.get("priority_score", 0)), reverse=True)


def _card_priority_score(card: dict[str, Any], *, theme: str) -> int:
    text = " ".join(str(card.get(key, "")) for key in ("title", "type", "business_meaning", "supporting_evidence", "recommendation")).lower()
    confidence_score = _priority_level_score(card.get("confidence"), default=55)
    impact_score = _priority_level_score(card.get("impact"), default=55)

    if theme == "risk":
        relevance = _text_relevance_score(text, {"risk", "anomaly", "volatility", "decline", "drop", "loss", "failure"})
        urgency = _text_relevance_score(text, {"critical", "urgent", "immediate", "exposure", "warning"})
        raw = (0.45 * confidence_score) + (0.35 * impact_score) + relevance + urgency
    else:
        relevance = _text_relevance_score(text, {"opportunity", "growth", "upside", "expand", "improve", "increase"})
        value_signal = _text_relevance_score(text, {"revenue", "margin", "efficiency", "retention", "conversion"})
        raw = (0.40 * confidence_score) + (0.35 * impact_score) + relevance + value_signal

    return max(0, min(100, int(round(raw / 1.2))))


def _prioritize_cards(cards: list[dict[str, Any]], *, theme: str) -> list[dict[str, Any]]:
    scored = [{**card, "priority_score": _card_priority_score(card, theme=theme)} for card in cards]
    return sorted(scored, key=lambda item: int(item.get("priority_score", 0)), reverse=True)


def _executive_summary_priority_score(summary: dict[str, Any], ranked_recommendations: list[dict[str, Any]]) -> dict[str, int]:
    readiness_score = _as_score(_as_dict(summary.get("dataset_readiness")).get("score"), default=0)
    health_score = _as_score(summary.get("overall_business_health"), default=0)
    top_recommendation_score = _as_score((ranked_recommendations[:1] or [{}])[0].get("priority_score"), default=0)
    top_opportunity_score = _priority_level_score(summary.get("top_opportunity"), default=55)
    biggest_risk_score = _priority_level_score(summary.get("biggest_risk"), default=55)

    total = int(
        round(
            (0.25 * readiness_score)
            + (0.25 * health_score)
            + (0.30 * top_recommendation_score)
            + (0.10 * top_opportunity_score)
            + (0.10 * (100 - biggest_risk_score))
        )
    )

    return {
        "total": max(0, min(100, total)),
        "readiness": readiness_score,
        "health": health_score,
        "recommendation": top_recommendation_score,
        "opportunity": top_opportunity_score,
        "risk_pressure": biggest_risk_score,
    }


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

    cards = []
    for card in kpis[:limit]:
        cards.append(
            _metric(
                str(card.get("label", "KPI")),
                card.get("value", "N/A"),
                _first_text(card.get("business_context"), card.get("description"), card.get("status"), fallback=""),
            )
        )
    st.markdown(f'<div class="exec-metric-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


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


def _build_report_context(payload: dict[str, Any] | None) -> ReportContext:
    safe_payload = _as_dict(payload)
    sections = _as_list_of_dicts(safe_payload.get("sections"))
    section_index: dict[str, dict[str, Any]] = {}
    for section in sections:
        section_id = section.get("section_id")
        if isinstance(section_id, str) and section_id:
            section_index[section_id] = section

    summary = _as_dict(_as_dict(section_index.get("executive_summary")).get("content"))
    readiness = _as_dict(summary.get("dataset_readiness"))
    recommendations = _as_list_of_dicts(_as_dict(section_index.get("executive_recommendations")).get("recommendations"))
    ranked_recommendations = _rank_recommendations(recommendations)
    risk_cards = _prioritize_cards(
        [card for card in _as_list_of_dicts(_as_dict(section_index.get("ai_business_insights")).get("cards")) if "risk" in str(card).lower() or "anomal" in str(card).lower()],
        theme="risk",
    )
    opportunity_cards = _prioritize_cards(
        [card for card in _as_list_of_dicts(_as_dict(section_index.get("ai_business_insights")).get("cards")) if "opportun" in str(card).lower() or "growth" in str(card).lower()],
        theme="opportunity",
    )

    normalized_summary = {
        **summary,
        "dataset_readiness": {
            "score": _as_score(readiness.get("score"), default=0),
            "reason": _first_text(readiness.get("reason"), fallback=""),
        },
        "overall_business_health": _as_score(summary.get("overall_business_health"), default=0),
    }
    normalized_summary["priority_scores"] = _executive_summary_priority_score(normalized_summary, ranked_recommendations)

    return ReportContext(
        payload=safe_payload,
        summary=normalized_summary,
        kpis=_as_list_of_dicts(_as_dict(section_index.get("kpi_overview")).get("kpis")),
        ai_cards=_as_list_of_dicts(_as_dict(section_index.get("ai_business_insights")).get("cards")),
        charts=_as_list_of_dicts(_as_dict(section_index.get("executive_charts")).get("charts")),
        recommendations=recommendations,
        ranked_recommendations=ranked_recommendations,
        prioritized_risk_cards=risk_cards,
        prioritized_opportunity_cards=opportunity_cards,
    )


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


def render_header(context: ReportContext) -> None:
    summary = context.summary
    readiness = _as_dict(summary.get("dataset_readiness"))
    priority_scores = _as_dict(summary.get("priority_scores"))
    with st.container(border=True):
        st.markdown(
            f"""
            <div class="exec-cover">
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
                    {_metric('Executive Priority', f"{priority_scores.get('total', 0)}/100", 'Composite of readiness, health, risk and top recommendation')}
                    {_metric('Confidence', _confidence_label(summary.get('confidence')), 'No storyboard regeneration performed')}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_business_health(context: ReportContext) -> None:
    summary = context.summary
    ranked_recommendations = context.ranked_recommendations
    with st.container(border=True):
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
        _recommendation_strip((ranked_recommendations[:1] or [{}])[0].get("recommendation") or summary.get("top_opportunity"))


def render_kpi_section(context: ReportContext) -> None:
    with st.container(border=True):
        _block_header(
            "03 KPI Summary",
            "Performance indicators for executive review",
            "KPI cards are reused from the existing storyboard payload and arranged for fast comparison.",
        )
        _render_kpi_cards(context.kpis, limit=8)
        _recommendation_strip(_first_text((context.ranked_recommendations[:1] or [{}])[0].get("recommendation"), fallback="Prioritize KPI movements with the clearest operational owner."))


def render_ai_insights(context: ReportContext) -> None:
    ai_cards = context.ai_cards
    with st.container(border=True):
        _block_header(
            "04 AI Business Insights",
            "Decision intelligence from existing AI cards",
            "The original AI Business Insight cards are reused directly to preserve evidence and recommendation lineage.",
        )
        render_ai_business_insight_cards({"cards": ai_cards})
        if ai_cards:
            _recommendation_strip(_first_text(ai_cards[0].get("executive_recommendation"), ai_cards[0].get("recommendation")))


def render_charts(context: ReportContext) -> None:
    with st.container(border=True):
        _block_header(
            "05 Dashboard Visuals",
            "Charts already prepared by Dashboard Studio",
            "Visuals are rendered from the existing chart specifications; no chart is regenerated for the storyboard.",
        )
        _render_charts(_select_charts(context.charts, limit=MAX_PREVIEW_CHARTS), prefix="exec_story_chart")
        _recommendation_strip(_first_text((context.ranked_recommendations[:1] or [{}])[0].get("recommendation"), fallback="Use the strongest visual as the opening evidence slide."))


def render_trends(context: ReportContext) -> None:
    trend_charts = _select_charts(context.charts, keywords={"trend", "time", "date", "month", "year", "line"}, limit=2)
    with st.container(border=True):
        _block_header(
            "06 Trends",
            "Directional movement and time-based signals",
            "Trend evidence is selected from existing dashboard visuals when available.",
        )
        cols = st.columns([0.38, 0.62])
        with cols[0]:
            _render_ai_card_summaries(context.ai_cards, limit=2)
        with cols[1]:
            _render_charts(trend_charts, prefix="exec_story_trend", empty="No trend-specific dashboard visual is available; using the existing dashboard visuals above.")
        _recommendation_strip("Translate sustained directional movement into one owner, one metric, and one review cadence.")


def render_risks(context: ReportContext) -> None:
    risk_cards = context.prioritized_risk_cards
    with st.container(border=True):
        _block_header(
            "07 Risks",
            "Issues that could affect confidence or performance",
            _first_text(context.summary.get("biggest_risk"), fallback="Risks are inferred from existing AI cards and executive recommendations."),
        )
        _render_ai_card_summaries(risk_cards or context.ai_cards, limit=3)
        _recommendation_strip(_first_text(context.summary.get("biggest_risk"), (context.ranked_recommendations[:1] or [{}])[0].get("recommendation")))


def render_opportunities(context: ReportContext) -> None:
    opportunity_cards = context.prioritized_opportunity_cards
    with st.container(border=True):
        _block_header(
            "08 Opportunities",
            "Value creation themes for leadership action",
            _first_text(context.summary.get("top_opportunity"), fallback="Opportunities are drawn from existing insight and recommendation evidence."),
        )
        _render_ai_card_summaries(opportunity_cards or context.ai_cards, limit=3)
        _recommendation_strip(_first_text(context.summary.get("top_opportunity"), (context.ranked_recommendations[:1] or [{}])[0].get("recommendation")))


def render_recommendations(context: ReportContext) -> None:
    recommendations = context.ranked_recommendations
    with st.container(border=True):
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
                            {_badge(f"Score: {rec.get('priority_score', 0)}")}
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


def render_footer(context: ReportContext) -> None:
    summary = context.summary
    recommendations = context.ranked_recommendations
    priority_scores = _as_dict(summary.get("priority_scores"))
    with st.container(border=True):
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
            + _metric("Priority Score", f"{priority_scores.get('total', 0)}/100", "Executive summary scoring")
            + "</div>",
            unsafe_allow_html=True,
        )
        _recommendation_strip(_first_text((recommendations[:1] or [{}])[0].get("recommendation"), fallback="Move the selected recommendation into the next executive operating review."), label="Closing Recommendation")
    st.caption("Storyboard UI uses existing payload, AI cards, and dashboard chart specifications.")


def render_executive_storyboard(payload: dict[str, Any] | None) -> None:
    if not payload:
        st.info("Executive Storyboard is not available yet.")
        return

    _inject_styles()
    context = _build_report_context(payload)
    render_header(context)
    render_business_health(context)
    render_kpi_section(context)
    render_ai_insights(context)
    render_charts(context)
    render_trends(context)
    render_risks(context)
    render_opportunities(context)
    render_recommendations(context)
    render_footer(context)
