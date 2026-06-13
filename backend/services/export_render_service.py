from __future__ import annotations

import io
from typing import Any

import plotly.graph_objects as go
import plotly.io as pio
from PIL import Image, ImageDraw, ImageFont


def filter_charts(report: dict[str, Any], chart_ids: list[str] | None = None) -> list[dict[str, Any]]:
    charts = report.get("chart_specs", [])
    if not chart_ids:
        return charts
    selected = set(chart_ids)
    return [chart for chart in charts if chart.get("chart_id") in selected]


def chart_to_png_bytes(chart: dict[str, Any], width: int = 980, height: int = 520) -> bytes | None:
    try:
        spec = chart.get("plotly", {})
        figure = go.Figure(data=spec.get("data", []), layout=spec.get("layout", {}))
        return pio.to_image(figure, format="png", width=width, height=height, scale=1)
    except Exception:
        return None


def build_dashboard_snapshot(report: dict[str, Any], chart_ids: list[str] | None = None) -> bytes:
    branding = report.get("branding", {})
    theme = report.get("theme", {})
    charts = filter_charts(report, chart_ids)[:4]
    width = 1400
    height = 900
    background = theme.get("background", "#F3F6FA")
    surface = theme.get("surface", "#FFFFFF")
    primary = branding.get("primary_color") or theme.get("primary", "#118DFF")
    text = theme.get("text", "#1F2937")
    muted = theme.get("muted_text", "#64748B")

    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.load_default(size=34)
    section_font = ImageFont.load_default(size=20)
    small_font = ImageFont.load_default(size=15)

    draw.rounded_rectangle((36, 28, width - 36, 118), radius=18, fill=surface)
    draw.text((62, 48), branding.get("company_name", "AI Analytics"), fill=primary, font=title_font)
    draw.text((62, 88), branding.get("report_title", "Executive Dashboard Snapshot"), fill=muted, font=small_font)

    kpis = report.get("kpi_cards", [])[:4]
    card_w = (width - 96 - 36) // 4
    for index, card in enumerate(kpis):
        x = 48 + index * (card_w + 12)
        draw.rounded_rectangle((x, 142, x + card_w, 258), radius=14, fill=surface)
        draw.text((x + 18, 160), str(card.get("label", "KPI"))[:30], fill=muted, font=small_font)
        draw.text((x + 18, 190), str(card.get("value", ""))[:22], fill=text, font=section_font)
        draw.text((x + 18, 224), str(card.get("delta_percentage", "No comparison"))[:28], fill=primary, font=small_font)

    positions = [(48, 292), (724, 292), (48, 596), (724, 596)]
    for chart, (x, y) in zip(charts, positions):
        draw.rounded_rectangle((x, y, x + 628, y + 260), radius=14, fill=surface)
        png = chart_to_png_bytes(chart, width=610, height=240)
        if png:
            chart_img = Image.open(io.BytesIO(png)).convert("RGB")
            chart_img.thumbnail((610, 240))
            image.paste(chart_img, (x + 9, y + 10))
        else:
            draw.text((x + 22, y + 28), chart.get("title", "Chart"), fill=text, font=section_font)
            draw.text((x + 22, y + 62), "Chart image unavailable for snapshot.", fill=muted, font=small_font)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
