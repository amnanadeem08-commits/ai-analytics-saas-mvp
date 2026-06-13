from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.services.export_render_service import chart_to_png_bytes, filter_charts


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
    overview_table = _wrapped_table(
        [
            ["Rows", "Columns", "Charts", "Generated"],
            [
                f"{overview.get('row_count', 0):,}",
                f"{overview.get('column_count', 0):,}",
                f"{len(filter_charts(report, chart_ids)):,}",
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
                card.get("value", ""),
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

    charts = filter_charts(report, chart_ids)
    if charts:
        story.append(PageBreak())
        story.append(_paragraph("Dashboard Visuals", styles["Section"]))
        for chart in charts:
            png = chart_to_png_bytes(chart, width=920, height=480)
            story.append(_paragraph(chart.get("title", "Chart"), styles["Heading3"]))
            if png:
                image = Image(io.BytesIO(png), width=6.55 * inch, height=3.45 * inch)
                story.extend([image, Spacer(1, 0.14 * inch)])
            else:
                story.append(_paragraph("Chart image could not be rendered; chart spec is included in JSON export.", styles["BodyText"]))

    business_story = report.get("business_story", {})
    story.extend(
        [
            _paragraph("Executive Narrative", styles["Section"]),
            _paragraph(business_story.get("business_story", ""), styles["BodyText"]),
        ]
    )

    doc.build(story, onFirstPage=lambda canvas, doc_obj: _footer(canvas, doc_obj, branding), onLaterPages=lambda canvas, doc_obj: _footer(canvas, doc_obj, branding))
    return buffer.getvalue()
