from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.services.export_render_service import build_export_bundle


def _hex_color(value: str, fallback: colors.Color) -> colors.Color:
    try:
        return colors.HexColor(value)
    except Exception:
        return fallback


def _paragraph(text: Any, style: ParagraphStyle) -> Paragraph:
    safe = str(text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(safe, style)


def _footer(canvas, doc, branding: dict[str, Any]) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    footer = f"{branding.get('company_name', 'AI Analytics')} | Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    canvas.drawString(doc.leftMargin, 0.35 * inch, footer)
    canvas.drawRightString(letter[0] - doc.rightMargin, 0.35 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _wrapped_table(rows: list[list[Any]], widths: list[float], header_color: colors.Color, body_style: ParagraphStyle) -> Table:
    wrapped_rows = []
    for row_index, row in enumerate(rows):
        style = body_style
        wrapped_rows.append([_paragraph(value, style) for value in row])
    table = Table(wrapped_rows, colWidths=widths, repeatRows=1, splitByRow=True)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), header_color),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def build_executive_pdf(
    report: dict[str, Any],
    chart_ids: list[str] | None = None,
    package: str = "executive",
) -> bytes:
    if package == "storyboard":
        return build_storyboard_pdf(report, chart_ids=chart_ids, package=package)
    buffer = io.BytesIO()
    branding = report.get("branding", {})
    primary = _hex_color(branding.get("primary_color", "#118DFF"), colors.HexColor("#118DFF"))
    accent = _hex_color(branding.get("accent_color", "#E66C37"), colors.HexColor("#E66C37"))

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.62 * inch,
        title=branding.get("report_title", "Executive Report"),
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BrandTitle", parent=styles["Title"], textColor=primary, fontSize=20, leading=24))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], textColor=primary, spaceBefore=10, keepWithNext=True))
    styles.add(ParagraphStyle(name="WrappedBody", parent=styles["BodyText"], fontSize=8.5, leading=11))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))

    story = [
        _paragraph(branding.get("company_name", "AI Analytics"), styles["BrandTitle"]),
        _paragraph(branding.get("report_title", "Executive Decision Intelligence Report"), styles["Heading1"]),
        _paragraph(f"Package: {package.title()} | Dataset: {report.get('dataset_id', '')}", styles["BodyText"]),
        Spacer(1, 0.16 * inch),
    ]

    overview = report.get("overview", {})
    export_bundle = build_export_bundle(report, chart_ids, width=920, height=480)
    rendered_charts = export_bundle.charts
    overview_table = _wrapped_table(
        [
            ["Rows", "Columns", "Charts", "Generated"],
            [
                f"{overview.get('row_count', 0):,}",
                f"{overview.get('column_count', 0):,}",
                f"{len(rendered_charts):,}",
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            ],
        ],
        [1.25 * inch, 1.25 * inch, 1.25 * inch, 2.2 * inch],
        primary,
        styles["WrappedBody"],
    )
    story.extend([overview_table, Spacer(1, 0.18 * inch)])

    executive = report.get("executive_summary", {})
    story.extend(
        [
            _paragraph("Executive Summary", styles["Section"]),
            _paragraph(executive.get("insight", ""), styles["BodyText"]),
            _paragraph(f"Reason: {executive.get('reason', '')}", styles["BodyText"]),
            _paragraph(f"Recommended Action: {executive.get('action', '')}", styles["BodyText"]),
        ]
    )

    quality = report.get("data_quality_score", {})
    if quality:
        story.extend(
            [
                _paragraph("Data Quality", styles["Section"]),
                _wrapped_table(
                    [
                        ["Score", "Grade", "Completeness", "Duplicate Rate", "Meaning"],
                        [
                            quality.get("score", ""),
                            quality.get("grade", ""),
                            f"{quality.get('completeness_pct', '')}%",
                            f"{quality.get('duplicate_pct', '')}%",
                            quality.get("explanation", ""),
                        ],
                    ],
                    [0.75 * inch, 0.65 * inch, 1.05 * inch, 1.05 * inch, 2.85 * inch],
                    primary,
                    styles["WrappedBody"],
                ),
            ]
        )

    kpi_rows = [["KPI", "Value", "Variance", "Business Evidence"]]
    for card in report.get("kpi_cards", [])[:8]:
        kpi_rows.append(
            [
                card.get("label", ""),
                card.get("formatted_value", card.get("value", "")),
                card.get("delta_percentage", ""),
                card.get("reason", card.get("description", "")),
            ]
        )
    story.extend(
        [
            _paragraph("KPI Overview", styles["Section"]),
            _wrapped_table(kpi_rows, [1.25 * inch, 0.9 * inch, 0.85 * inch, 3.35 * inch], accent, styles["WrappedBody"]),
        ]
    )

    story.append(_paragraph("What / Why / Action Framework", styles["Section"]))
    for block in executive.get("decision_framework", [])[:6]:
        story.append(
            KeepTogether(
                [
                    _paragraph(f"What happened: {block.get('what_happened', '')}", styles["BodyText"]),
                    _paragraph(f"Why: {block.get('why_it_happened', '')}", styles["BodyText"]),
                    _paragraph(f"What to do: {block.get('what_to_do', '')}", styles["BodyText"]),
                    _paragraph(f"Expected impact: {block.get('expected_impact', '')}", styles["BodyText"]),
                    _paragraph(f"Confidence: {block.get('confidence', '')}", styles["Small"]),
                    Spacer(1, 0.07 * inch),
                ]
            )
        )

    recommendations = executive.get("recommendations", [])
    if recommendations:
        rec_rows = [["Recommendation", "Reason", "Expected Impact"]]
        for item in recommendations[:8]:
            rec_rows.append(
                [
                    item.get("recommendation", ""),
                    item.get("reason", ""),
                    item.get("expected_impact", ""),
                ]
            )
        story.extend(
            [
                _paragraph("Recommendations", styles["Section"]),
                _wrapped_table(rec_rows, [2.0 * inch, 2.0 * inch, 2.35 * inch], accent, styles["WrappedBody"]),
            ]
        )

    if rendered_charts:
        story.append(PageBreak())
        story.append(_paragraph("Dashboard Visuals", styles["Section"]))
        for export_chart in rendered_charts:
            chart = export_chart.chart
            png = export_chart.png
            story.append(_paragraph(chart.get("title", "Chart"), styles["Heading3"]))
            image = Image(io.BytesIO(png), width=6.55 * inch, height=3.45 * inch)
            story.extend([image, Spacer(1, 0.14 * inch)])

    business_story = report.get("business_story", {})
    story.extend(
        [
            _paragraph("Executive Narrative", styles["Section"]),
            _paragraph(business_story.get("business_story", ""), styles["BodyText"]),
        ]
    )

    doc.build(story, onFirstPage=lambda canvas, doc_obj: _footer(canvas, doc_obj, branding), onLaterPages=lambda canvas, doc_obj: _footer(canvas, doc_obj, branding))
    return buffer.getvalue()

def _storyboard_section(payload: dict[str, Any], section_id: str) -> dict[str, Any]:
    return next((section for section in payload.get("sections", []) if section.get("section_id") == section_id), {})


def build_storyboard_pdf(
    report: dict[str, Any],
    chart_ids: list[str] | None = None,
    package: str = "storyboard",
) -> bytes:
    buffer = io.BytesIO()
    branding = report.get("branding", {})
    storyboard = report.get("executive_storyboard", {})
    primary = _hex_color(branding.get("primary_color", "#118DFF"), colors.HexColor("#118DFF"))
    accent = _hex_color(branding.get("accent_color", "#E66C37"), colors.HexColor("#E66C37"))
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.58 * inch,
        bottomMargin=0.58 * inch,
        title="Executive Storyboard",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="StoryTitle", parent=styles["Title"], textColor=primary, fontSize=21, leading=25))
    styles.add(ParagraphStyle(name="StorySection", parent=styles["Heading2"], textColor=primary, fontSize=14, leading=17, spaceBefore=10))
    styles.add(ParagraphStyle(name="StoryBody", parent=styles["BodyText"], fontSize=8.6, leading=11))
    story = [
        _paragraph("Executive Storyboard", styles["StoryTitle"]),
        _paragraph(f"Dataset: {report.get('dataset_id', '')} | Package: {package.title()}", styles["StoryBody"]),
        Spacer(1, 0.12 * inch),
    ]

    summary = _storyboard_section(storyboard, "executive_summary").get("content", {})
    readiness = summary.get("dataset_readiness", {})
    story.extend([
        _paragraph("1. Executive Summary", styles["StorySection"]),
        _wrapped_table(
            [
                ["Dataset Readiness", "Business Health", "Top Opportunity", "Biggest Risk"],
                [
                    f"{readiness.get('score', 0)}/100",
                    f"{summary.get('overall_business_health', 0)}/100",
                    summary.get("top_opportunity", "Not available"),
                    summary.get("biggest_risk", "Not available"),
                ],
            ],
            [1.15 * inch, 1.15 * inch, 2.05 * inch, 2.05 * inch],
            primary,
            styles["StoryBody"],
        ),
        Spacer(1, 0.08 * inch),
        _paragraph(summary.get("executive_summary", ""), styles["StoryBody"]),
    ])

    kpis = _storyboard_section(storyboard, "kpi_overview").get("kpis", [])
    story.append(_paragraph("2. KPI Overview", styles["StorySection"]))
    if kpis:
        rows = [["KPI", "Value", "Context"]]
        for card in kpis[:8]:
            rows.append([card.get("label", ""), card.get("formatted_value", card.get("value", "")), card.get("business_context", card.get("description", ""))])
        story.append(_wrapped_table(rows, [1.6 * inch, 1.1 * inch, 3.7 * inch], accent, styles["StoryBody"]))
    else:
        story.append(_paragraph("No KPI cards are available for this dataset.", styles["StoryBody"]))

    ai_cards = _storyboard_section(storyboard, "ai_business_insights").get("cards", [])
    story.append(_paragraph("3. AI Business Insights", styles["StorySection"]))
    if ai_cards:
        for card in ai_cards:
            story.append(KeepTogether([
                _paragraph(f"{card.get('type', 'Insight')}: {card.get('title', '')}", styles["Heading4"]),
                _paragraph(f"Meaning: {card.get('business_meaning', '')}", styles["StoryBody"]),
                _paragraph(f"Evidence: {card.get('supporting_evidence', '')}", styles["StoryBody"]),
                _paragraph(f"Recommendation: {card.get('executive_recommendation', '')}", styles["StoryBody"]),
                Spacer(1, 0.06 * inch),
            ]))
    else:
        story.append(_paragraph("No AI Business Insight cards are available.", styles["StoryBody"]))

    charts = _storyboard_section(storyboard, "executive_charts").get("charts", [])
    if not charts:
        charts = report.get("chart_specs", [])
    if chart_ids:
        selected = set(chart_ids)
        charts = [chart for chart in charts if chart.get("chart_id") in selected]
    story_report = {**report, "chart_specs": charts}
    export_bundle = build_export_bundle(story_report, None, width=920, height=480)
    rendered_charts = export_bundle.charts
    story.append(PageBreak())
    story.append(_paragraph("4. Executive Charts", styles["StorySection"]))
    if rendered_charts:
        for export_chart in rendered_charts:
            chart = export_chart.chart
            png = export_chart.png
            story.append(_paragraph(chart.get("title", "Chart"), styles["Heading3"]))
            story.append(Image(io.BytesIO(png), width=6.45 * inch, height=3.35 * inch))
            story.append(Spacer(1, 0.12 * inch))
    else:
        story.append(_paragraph("No chart-ready visuals were generated for this dataset.", styles["StoryBody"]))

    recs = _storyboard_section(storyboard, "executive_recommendations").get("recommendations", [])
    story.append(_paragraph("5. Executive Recommendations", styles["StorySection"]))
    if recs:
        rows = [["Priority", "Business Value", "Difficulty", "Expected Impact", "Recommendation"]]
        for rec in recs[:10]:
            rows.append([rec.get("priority", ""), rec.get("business_value", ""), rec.get("difficulty", ""), rec.get("expected_impact", ""), rec.get("recommendation", "")])
        story.append(_wrapped_table(rows, [0.75 * inch, 1.45 * inch, 0.8 * inch, 1.45 * inch, 1.95 * inch], primary, styles["StoryBody"]))
    else:
        story.append(_paragraph("No ranked recommendations are available.", styles["StoryBody"]))

    doc.build(story, onFirstPage=lambda canvas, doc_obj: _footer(canvas, doc_obj, branding), onLaterPages=lambda canvas, doc_obj: _footer(canvas, doc_obj, branding))
    return buffer.getvalue()