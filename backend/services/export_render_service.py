from __future__ import annotations

import io
import logging
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from PIL import Image, ImageDraw, ImageFont


logger = logging.getLogger(__name__)


def filter_charts(report: dict[str, Any], chart_ids: list[str] | None = None) -> list[dict[str, Any]]:
    charts = report.get("chart_specs", [])
    if not chart_ids:
        return charts
    selected = set(chart_ids)
    return [chart for chart in charts if chart.get("chart_id") in selected]


# ── Chart rendering ──────────────────────────────────────────────────────

def _plotly_figure(chart: dict[str, Any]) -> go.Figure | None:
    """Return a Plotly Figure from chart spec, or None if empty."""
    spec = chart.get("plotly", {})
    data = spec.get("data", [])
    layout = spec.get("layout", {})
    if not data and not layout:
        return None
    try:
        return go.Figure(data=data, layout=layout)
    except Exception:
        logger.exception("Could not build Plotly figure for chart %s", chart.get("chart_id", "unknown"))
        return None


def _fallback_matplotlib_chart(chart: dict[str, Any], width: int, height: int) -> bytes | None:
    """Render a simple fallback chart using matplotlib when Plotly fails."""
    try:
        chart_type = chart.get("chart_type", "bar")
        columns = chart.get("columns", [])
        metadata = chart.get("metadata", {})
        title = chart.get("title", "Chart")
        short_insight = metadata.get("short_ai_insight", "")

        dpi = 100
        fig_w = width / dpi
        fig_h = height / dpi

        fig, ax = plt.subplots(figsize=(fig_w, fig_h), facecolor="#F8FAFC")
        ax.set_facecolor("#FFFFFF")
        ax.set_title(title, fontsize=14, fontweight="bold", color="#1E293B", pad=12)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        # Try to find categorical and numeric data from top_categories in metadata
        top_cats = metadata.get("top_categories", {})

        if top_cats and isinstance(top_cats, dict):
            # Use first category found
            cat_name = list(top_cats.keys())[0]
            cat_data = top_cats[cat_name]
            if isinstance(cat_data, list) and len(cat_data) > 0:
                labels = []
                values = []
                for item in cat_data[:10]:
                    if isinstance(item, dict):
                        lbl = item.get("label", item.get("value", ""))
                        val = item.get("value", item.get("count", 0))
                        if lbl is not None:
                            labels.append(str(lbl)[:20])
                            values.append(float(val) if val else 0)
                if labels and values:
                    colors = plt.cm.Blues(np.linspace(0.4, 0.85, len(labels)))
                    bars = ax.barh(labels, values, color=colors, edgecolor="white", height=0.65)
                    ax.set_xlabel("Value", fontsize=10, color="#475569")
                    for bar, value in zip(bars, values):
                        ax.text(bar.get_width() + max(values) * 0.01, bar.get_y() + bar.get_height() / 2,
                                f"{value:,.0f}", va="center", fontsize=8, color="#475569")
                    ax.invert_yaxis()
                    fig.tight_layout()
                    buf = io.BytesIO()
                    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
                    plt.close(fig)
                    return buf.getvalue()

        # Fallback: use numeric data from correlations or just show a summary card
        corr = metadata.get("correlations", {})
        if corr and isinstance(corr, dict):
            pairs = []
            for col_a, inner in corr.items():
                if isinstance(inner, dict):
                    for col_b, val in inner.items():
                        if isinstance(val, (int, float)) and col_a != col_b:
                            pairs.append((col_a, col_b, val))
            if pairs:
                pairs = pairs[:10]
                labels = [f"{a} vs {b}"[:25] for a, b, _ in pairs]
                values = [v for _, _, v in pairs]
                colors = ["#10B981" if v > 0 else "#EF4444" for v in values]
                bars = ax.barh(labels, values, color=colors, edgecolor="white", height=0.6)
                ax.axvline(0, color="#CBD5E1", linewidth=0.8)
                ax.set_xlabel("Correlation", fontsize=10, color="#475569")
                ax.set_xlim(-1.1, 1.1)
                for bar, val in zip(bars, values):
                    ax.text(bar.get_width() + 0.02 if val > 0 else bar.get_width() - 0.15,
                            bar.get_y() + bar.get_height() / 2, f"{val:.2f}",
                            va="center", fontsize=8, color="#475569")
                ax.invert_yaxis()
                fig.tight_layout()
                buf = io.BytesIO()
                fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
                plt.close(fig)
                return buf.getvalue()

        if columns and len(columns) >= 2:
            ax.text(0.5, 0.5, f"{title}\n\n{short_insight}\n\n(Business insight summary)",
                    transform=ax.transAxes, ha="center", va="center", fontsize=11,
                    color="#64748B", fontstyle="italic", wrap=True)
        else:
            ax.text(0.5, 0.5, f"{title}\n\n{short_insight}",
                    transform=ax.transAxes, ha="center", va="center", fontsize=11,
                    color="#64748B", fontstyle="italic")
        ax.set_xticks([])
        ax.set_yticks([])
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        return buf.getvalue()
    except Exception:
        logger.exception("Matplotlib fallback failed for chart %s", chart.get("chart_id", "unknown"))
        return None


def chart_to_png_bytes(chart: dict[str, Any], width: int = 980, height: int = 520) -> bytes | None:
    """Render a chart spec to PNG bytes. Tries Plotly first, falls back to matplotlib."""
    figure = _plotly_figure(chart)
    if figure is not None:
        try:
            return pio.to_image(figure, format="png", width=width, height=height, scale=1)
        except Exception:
            logger.exception("Plotly image render failed for chart %s", chart.get("chart_id", "unknown"))
    # Fallback to matplotlib
    return _fallback_matplotlib_chart(chart, width, height)


# ── PNG dashboard snapshot ──────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    try:
        return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))
    except Exception:
        return (17, 141, 255)


def _draw_rounded_rect(draw: ImageDraw, x1: int, y1: int, x2: int, y2: int, fill: str, radius: int = 12) -> None:
    draw.rounded_rectangle((x1, y1, x2, y2), radius=radius, fill=fill)


def build_dashboard_snapshot(report: dict[str, Any], chart_ids: list[str] | None = None) -> bytes:
    branding = report.get("branding", {})
    theme = report.get("theme", {})
    charts = [c for c in report.get("chart_specs", []) if not chart_ids or c.get("chart_id") in chart_ids]
    charts = charts[:4]
    width = 1400
    height = 1600  # taller to accommodate more content
    bg = theme.get("background", "#F1F5F9")
    surface = "#FFFFFF"
    primary_hex = branding.get("primary_color") or theme.get("primary", "#118DFF")
    primary_rgb = _hex_to_rgb(primary_hex)
    text_color = "#0F172A"
    muted = "#64748B"

    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype("arial.ttf", 36)
        heading_font = ImageFont.truetype("arial.ttf", 22)
        section_font = ImageFont.truetype("arial.ttf", 18)
        body_font = ImageFont.truetype("arial.ttf", 14)
        small_font = ImageFont.truetype("arial.ttf", 12)
    except Exception:
        title_font = ImageFont.load_default()
        heading_font = ImageFont.load_default()
        section_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    y_pos = 20

    # ── Header ──
    _draw_rounded_rect(draw, 30, y_pos, width - 30, y_pos + 100, surface, radius=16)
    draw.text((55, y_pos + 18), branding.get("company_name", "AI Analytics"), fill=primary_hex, font=title_font)
    draw.text((55, y_pos + 62), branding.get("report_title", "Executive Dashboard Snapshot"), fill=muted, font=body_font)
    y_pos += 120

    exec_summary = report.get("executive_summary", {})
    quality = report.get("data_quality_score", {})

    # ── KPI Cards ──
    kpis = report.get("kpi_cards", [])
    if kpis:
        draw.text((40, y_pos), "KPI Overview", fill=primary_hex, font=heading_font)
        y_pos += 35
        card_w = (width - 80 - 36) // 4
        for i, card in enumerate(kpis[:4]):
            x = 40 + i * (card_w + 12)
            _draw_rounded_rect(draw, x, y_pos, x + card_w, y_pos + 110, surface, radius=12)
            draw.text((x + 14, y_pos + 12), str(card.get("label", "KPI"))[:30], fill=muted, font=small_font)
            val = str(card.get("value", ""))
            draw.text((x + 14, y_pos + 36), val[:22], fill=text_color, font=section_font)
            reason = str(card.get("reason", card.get("description", "")))[:80]
            draw.text((x + 14, y_pos + 68), reason[:60], fill=muted, font=small_font)
        y_pos += 130

    # ── Data Quality Badge ──
    if quality:
        draw.text((40, y_pos), "Data Quality", fill=primary_hex, font=heading_font)
        y_pos += 35
        _draw_rounded_rect(draw, 40, y_pos, width - 40, y_pos + 90, surface, radius=14)
        grade = str(quality.get("grade", "N/A"))
        grade_color = "#059669" if grade == "A" else "#2563EB" if grade == "B" else "#D97706" if grade == "C" else "#DC2626"
        # Grade circle
        draw.ellipse((65, y_pos + 16, 115, y_pos + 66), fill=grade_color)
        draw.text((75, y_pos + 28), grade, fill="white", font=heading_font)
        # Score
        draw.text((135, y_pos + 14), f"Score: {quality.get('score', 'N/A')}", fill=text_color, font=body_font)
        draw.text((135, y_pos + 40), f"Completeness: {quality.get('completeness_pct', 'N/A')}%  |  Duplicates: {quality.get('duplicate_pct', 'N/A')}%", fill=muted, font=small_font)
        draw.text((135, y_pos + 60), quality.get("explanation", ""), fill=muted, font=small_font)
        y_pos += 110

    # ── Insight Summary ──
    if exec_summary:
        draw.text((40, y_pos), "AI Insight Summary", fill=primary_hex, font=heading_font)
        y_pos += 35
        _draw_rounded_rect(draw, 40, y_pos, width - 40, y_pos + 95, surface, radius=14)
        draw.text((60, y_pos + 12), f"What happened: {exec_summary.get('insight', '')[:120]}", fill=text_color, font=body_font)
        draw.text((60, y_pos + 36), f"Why it matters: {exec_summary.get('reason', '')[:120]}", fill=muted, font=body_font)
        draw.text((60, y_pos + 60), f"Recommended action: {exec_summary.get('action', '')[:120]}", fill=primary_hex, font=body_font)
        y_pos += 115

    # ── Recommendations ──
    recs = exec_summary.get("recommendations", [])
    if recs:
        draw.text((40, y_pos), "Recommendations", fill=primary_hex, font=heading_font)
        y_pos += 35
        _draw_rounded_rect(draw, 40, y_pos, width - 40, y_pos + 50 + 30 * min(len(recs), 4), surface, radius=14)
        for i, rec in enumerate(recs[:4]):
            draw.text((60, y_pos + 12 + i * 30), f"• {rec.get('recommendation', '')[:130]}", fill=text_color, font=small_font)
        y_pos += 70 + 30 * min(len(recs), 4)

    # ── Charts ──
    if charts:
        draw.text((40, y_pos), "Dashboard Visuals", fill=primary_hex, font=heading_font)
        y_pos += 35
        for chart in charts:
            chart_title = chart.get("title", "Chart")
            short_insight = chart.get("metadata", {}).get("short_ai_insight", "")
            _draw_rounded_rect(draw, 40, y_pos, width - 40, y_pos + 260, surface, radius=14)
            draw.text((60, y_pos + 10), chart_title[:60], fill=text_color, font=section_font)
            png = chart_to_png_bytes(chart, width=620, height=220)
            if png:
                try:
                    chart_img = Image.open(io.BytesIO(png)).convert("RGB")
                    chart_img.thumbnail((620, 200))
                    cx = 60
                    cy = y_pos + 40
                    image.paste(chart_img, (cx, cy))
                except Exception:
                    draw.text((60, y_pos + 50), f"{short_insight}", fill=muted, font=body_font)
            else:
                draw.text((60, y_pos + 50), f"{short_insight}", fill=muted, font=body_font)
            y_pos += 275

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()