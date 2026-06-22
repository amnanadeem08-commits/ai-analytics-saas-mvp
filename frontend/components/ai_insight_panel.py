from __future__ import annotations

import html
from typing import Any

import streamlit as st


def _css() -> None:
    st.markdown(
        """
        <style>
        .ai-hero-card {
            background: linear-gradient(135deg, var(--brand-primary), var(--brand-secondary));
            border-radius: 20px;
            padding: 1.5rem 2rem;
            color: white;
            margin-bottom: 1.25rem;
        }
        .ai-hero-title {
            font-size: 1.5rem;
            font-weight: 800;
            margin-bottom: 0.3rem;
        }
        .ai-hero-sub {
            font-size: 0.9rem;
            opacity: 0.85;
        }
        .ai-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 700;
            margin: 3px 4px;
        }
        .ai-badge-green { background: color-mix(in srgb, var(--ui-success) 14%, transparent); color: var(--ui-success); border: 1px solid color-mix(in srgb, var(--ui-success) 28%, transparent); }
        .ai-badge-blue { background: color-mix(in srgb, var(--ui-info) 14%, transparent); color: var(--ui-info); border: 1px solid color-mix(in srgb, var(--ui-info) 28%, transparent); }
        .ai-badge-orange { background: color-mix(in srgb, var(--ui-warning) 14%, transparent); color: var(--ui-warning); border: 1px solid color-mix(in srgb, var(--ui-warning) 28%, transparent); }
        .ai-badge-gray { background: color-mix(in srgb, var(--text-muted) 14%, transparent); color: var(--text-muted); border: 1px solid color-mix(in srgb, var(--text-muted) 28%, transparent); }

        .ai-metric-card {
            border: 1px solid rgba(148,163,184,0.20);
            border-radius: 14px;
            padding: 16px;
            background: white;
            box-shadow: 0 4px 12px rgba(0,0,0,0.04);
            text-align: center;
            min-height: 120px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 4px;
        }
        .ai-metric-icon { font-size: 1.3rem; margin-bottom: 4px; }
        .ai-metric-label { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-muted); }
        .ai-metric-value { font-size: 1.5rem; font-weight: 900; color: var(--text-color); margin-top: 2px; }
        .ai-metric-helper { font-size: 0.7rem; color: var(--text-muted-soft); margin-top: 4px; }

        .ai-grade-circle {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 56px;
            height: 56px;
            border-radius: 50%;
            font-size: 1.5rem;
            font-weight: 900;
            color: white;
            box-shadow: 0 4px 16px rgba(0,0,0,0.10);
            flex-shrink: 0;
        }
        .ai-grade-a { background: linear-gradient(135deg, var(--ui-success), var(--ui-success-strong)); }
        .ai-grade-b { background: linear-gradient(135deg, var(--ui-info-strong), var(--ui-info)); }
        .ai-grade-c { background: linear-gradient(135deg, var(--ui-warning), var(--ui-warning-strong)); }
        .ai-grade-d { background: linear-gradient(135deg, var(--ui-danger), var(--ui-danger-strong)); }

        .ai-dq-card {
            border: 1px solid rgba(148,163,184,0.18);
            border-radius: 16px;
            padding: 1.2rem 1.5rem;
            background: white;
            box-shadow: 0 4px 14px rgba(0,0,0,0.04);
        }
        .ai-progress-track {
            width: 100%;
            height: 8px;
            background: var(--surface-border);
            border-radius: 999px;
            overflow: hidden;
            margin-top: 8px;
        }
        .ai-progress-fill {
            height: 100%;
            border-radius: 999px;
            transition: width 0.5s ease;
        }
        .ai-insight-block {
            border: 1px solid rgba(148,163,184,0.18);
            border-radius: 14px;
            padding: 14px 18px;
            margin-bottom: 10px;
            background: white;
        }
        .ai-insight-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 30px;
            height: 30px;
            border-radius: 8px;
            font-size: 0.9rem;
            flex-shrink: 0;
        }
        .ai-insight-title {
            font-size: 0.75rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .ai-insight-body {
            font-size: 0.88rem;
            color: var(--text-subtle);
            line-height: 1.45;
            margin-top: 4px;
        }
        .ai-risk-card {
            border-left: 4px solid;
            border-radius: 10px;
            padding: 10px 14px;
            margin-bottom: 6px;
            background: rgba(255,255,255,0.06);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _grade_class(grade: str) -> str:
    g = str(grade).upper().strip()
    if g == "A":
        return "ai-grade-a"
    elif g == "B":
        return "ai-grade-b"
    elif g == "C":
        return "ai-grade-c"
    return "ai-grade-d"


def _grade_color(grade: str) -> str:
    g = str(grade).upper().strip()
    if g == "A":
        return "var(--ui-success)"
    elif g == "B":
        return "var(--ui-info-strong)"
    elif g == "C":
        return "var(--ui-warning)"
    return "var(--ui-danger)"


def render_business_insights_overview(
    executive: dict[str, Any] | None = None,
    data_quality: dict[str, Any] | None = None,
    summary: dict[str, Any] | None = None,
    detection: dict[str, Any] | None = None,
    key_findings: list[dict] | None = None,
    risks: list[dict] | None = None,
    recommendations: list[dict] | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> None:
    """Render complete business-friendly AI Insights panel.

    Shows:
    1. Hero card with dataset badges
    2. Metric cards (rows, columns, score, completeness, duplicates, reliability)
    3. Data quality card with grade badge + progress bar
    4. Key findings section
    5. What / Why / Action storyboard blocks
    6. Risks and warnings
    7. Recommendations
    8. Technical evidence collapsed at bottom
    """
    _css()

    names = ["A", "B", "C", "D"]

    # ── 1. Hero Card ──
    dq = data_quality or {}
    grade = str(dq.get("grade", "N/A")).upper()
    row_count = f"{int(summary.get('row_count', 0) or 0):,}" if summary else "—"
    col_count = f"{int(summary.get('column_count', 0) or 0):,}" if summary else "—"
    reliability = "Excellent" if grade == "A" else "Good" if grade == "B" else "Fair" if grade == "C" else "Poor"
    domain = (detection or {}).get("domain", "Dataset")

    st.markdown(
        f"""
        <div class="ai-hero-card">
            <div class="ai-hero-title">Business Insights Overview</div>
            <div class="ai-hero-sub">AI analyzed your dataset and found key quality, KPI, and decision signals.</div>
            <div style="margin-top: 12px; display: flex; flex-wrap: wrap; gap: 6px;">
                <span class="ai-badge ai-badge-blue">📊 {row_count} rows</span>
                <span class="ai-badge ai-badge-blue">📋 {col_count} columns</span>
                <span class="ai-badge ai-badge-green">🏅 Grade {html.escape(str(grade))}</span>
                <span class="ai-badge ai-badge-green">✅ Reliability: {html.escape(reliability)}</span>
                <span class="ai-badge ai-badge-orange">🎯 Domain: {html.escape(domain)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── 2. Metric Cards ──
    score_val = dq.get("score", "—")
    completeness = dq.get("completeness_pct", summary.get("completeness_pct", "—") if summary else "—")
    dup_pct = dq.get("duplicate_pct", summary.get("duplicate_pct", "—") if summary else "—")
    if isinstance(completeness, (int, float)):
        completeness = f"{completeness:.1f}%"
    if isinstance(dup_pct, (int, float)):
        dup_pct = f"{dup_pct:.1f}%"

    cols = st.columns(6)
    metrics = [
        ("📊", "Rows", row_count, "Dataset records"),
        ("📋", "Columns", col_count, "Schema fields"),
        ("🏅", "Quality Score", str(score_val) + "/100" if isinstance(score_val, (int, float)) else str(score_val), f"Grade {grade}"),
        ("✅", "Completeness", completeness, "Cell fill rate"),
        ("🔄", "Duplicates", dup_pct, "Row duplication"),
        ("🔒", "Reliability", reliability, f"Trust Score {grade}"),
    ]
    for i, (icon, label, value, helper) in enumerate(metrics):
        with cols[i]:
            st.markdown(
                f"""
                <div class="ai-metric-card" style="border-top: 4px solid {['var(--ui-info)','var(--ui-accent)','var(--ui-success)','var(--ui-success-strong)','var(--ui-warning-strong)','var(--ui-accent-strong)'][i]};">
                    <div class="ai-metric-icon">{icon}</div>
                    <div class="ai-metric-label">{label}</div>
                    <div class="ai-metric-value">{value}</div>
                    <div class="ai-metric-helper">{helper}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── 3. Data Quality Card ──
    st.markdown("#### Data Quality Assessment")
    gc = _grade_color(grade)
    with st.container():
        st.markdown(
            f"""
            <div class="ai-dq-card">
                <div style="display: flex; align-items: center; gap: 18px;">
                    <div class="ai-grade-circle {_grade_class(grade)}">{html.escape(str(grade))}</div>
                    <div style="flex: 1;">
                        <div style="font-size: 0.72rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Overall Score</div>
                        <div style="font-size: 1.6rem; font-weight: 900; color: var(--text-color);">
                            {dq.get("score", "—")} <span style="font-size: 0.9rem; font-weight: 600; color: var(--text-muted);">/ 100</span>
                        </div>
                        <div style="font-size: 0.82rem; color: var(--text-subtle); margin-top: 2px;">
                            Your dataset is <b style="color: {gc};">{reliability}</b>
                        </div>
                        <div class="ai-progress-track">
                            <div class="ai-progress-fill" style="width: {min(float(str(dq.get('score', 0)).replace('/', '') or '0'), 100)}%; background: linear-gradient(90deg, {gc}, {gc}88);"></div>
                        </div>
                        <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 4px;">{dq.get("explanation", "Score based on completeness with duplicate-row penalty.")}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── 4. Key Findings ──
    if key_findings:
        st.markdown("#### Key Findings")
        for finding in key_findings[:5]:
            title = finding.get("title", "Finding")
            finding_text = finding.get("finding", "")
            finding_evidence = finding.get("evidence", {})
            st.markdown(
                f"""
                <div class="ai-insight-block" style="border-left: 4px solid var(--ui-info);">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <div class="ai-insight-icon" style="background: var(--ui-info); color: white;">📌</div>
                        <div style="flex:1;">
                            <div class="ai-insight-title" style="color: var(--ui-info);">{html.escape(str(title))}</div>
                            <div class="ai-insight-body">{html.escape(str(finding_text))}</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── 5. What / Why / Action ──
    if executive:
        insight = executive.get("insight", "")
        reason = executive.get("reason", "")
        action = executive.get("action", "")
        confidence = str(executive.get("confidence", executive.get("data_confidence", "low"))).title()
        conf_color = "var(--ui-success)" if confidence.lower() == "high" else "var(--ui-warning)" if confidence.lower() == "medium" else "var(--text-muted)"

        st.markdown("#### AI Storyboard")
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <span style="display: inline-flex; align-items: center; gap: 6px; background: {conf_color}14; color: {conf_color}; padding: 3px 10px; border-radius: 999px; font-size: 0.74rem; font-weight: 700;">
                    <span style="width: 7px; height: 7px; border-radius: 50%; background: {conf_color}; display: inline-block;"></span>
                    Confidence: {html.escape(confidence)}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        blocks = [
            ("📊", "var(--ui-info)", "What Happened", insight),
            ("📈", "var(--ui-warning)", "Why It Matters", reason),
            ("🎯", "var(--ui-success)", "Recommended Action", action),
        ]
        for icon, color, title, text in blocks:
            st.markdown(
                f"""
                <div class="ai-insight-block" style="border-left: 4px solid {color};">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <div class="ai-insight-icon" style="background: {color}; color: white;">{icon}</div>
                        <div style="flex:1;">
                            <div class="ai-insight-title" style="color: {color};">{title}</div>
                            <div class="ai-insight-body">{html.escape(str(text or "Insight generated from available dataset fields."))}</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── 6. Risks / Warnings ──
    if risks:
        st.markdown("#### Risks & Warnings")
        for risk in risks[:4]:
            risk_title = risk.get("risk", risk.get("title", "Risk"))
            risk_text = risk.get("why_it_matters", risk.get("message", ""))
            risk_color = "var(--ui-danger)" if "risk" in str(risk_title).lower() else "var(--ui-warning)"
            st.markdown(
                f"""
                <div class="ai-risk-card" style="border-left-color: {risk_color};">
                    <div style="font-size: 0.82rem; font-weight: 700; color: {risk_color};">⚠️ {html.escape(str(risk_title))}</div>
                    <div style="font-size: 0.82rem; color: var(--text-subtle); margin-top: 2px;">{html.escape(str(risk_text))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── 7. Recommendations ──
    if recommendations:
        st.markdown("#### Recommendations")
        for rec in recommendations[:5]:
            rec_text = rec.get("recommendation", rec.get("action", ""))
            rec_reason = rec.get("reason", rec.get("why", ""))
            rec_impact = rec.get("expected_impact", "")
            st.markdown(
                f"""
                <div class="ai-insight-block" style="border-left: 4px solid var(--ui-accent);">
                    <div style="font-size: 0.85rem; font-weight: 700; color: var(--text-color);">✅ {html.escape(str(rec_text))}</div>
                    {f'<div style="font-size: 0.78rem; color: var(--text-subtle); margin-top: 4px;">{html.escape(str(rec_reason))}</div>' if rec_reason else ''}
                    {f'<div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 2px; font-style: italic;">Expected impact: {html.escape(str(rec_impact))}</div>' if rec_impact else ''}
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── 8. Technical Evidence (collapsed at bottom — single expander) ──
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("Developer details / technical evidence", expanded=False):
        if raw_payload:
            st.json(raw_payload)
        elif executive:
            st.json(executive)