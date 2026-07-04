from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from PIL import Image, ImageDraw, ImageFont

from backend.utils.plotly_kaleido_compat import disable_kaleido_headers


logger = logging.getLogger(__name__)
disable_kaleido_headers()
@dataclass(frozen=True)
class ExportChart:
    chart: dict[str, Any]
    png: bytes

    @property
    def chart_id(self) -> str:
        return str(self.chart.get("chart_id") or "")

    @property
    def title(self) -> str:
        return str(self.chart.get("title") or "Chart")

    @property
    def chart_type(self) -> str:
        return str(self.chart.get("chart_type") or "chart")


@dataclass(frozen=True)
class ExportBundle:
    report: dict[str, Any]
    charts: list[ExportChart]
    requested_chart_count: int
    chart_ids: list[str] | None = None

    @property
    def rendered_chart_count(self) -> int:
        return len(self.charts)

    @property
    def validation(self) -> dict[str, Any]:
        return {
            "requested_chart_count": self.requested_chart_count,
            "rendered_chart_count": self.rendered_chart_count,
            "missing_chart_count": max(self.requested_chart_count - self.rendered_chart_count, 0),
            "chart_ids": [chart.chart_id for chart in self.charts if chart.chart_id],
        }

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


def _coerce_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _valid_png_bytes(png: bytes | None, min_width: int = 120, min_height: int = 80) -> bool:
    if not png or not png.startswith(b"\x89PNG\r\n\x1a\n"):
        return False
    try:
        with Image.open(io.BytesIO(png)) as image:
            image.verify()
        with Image.open(io.BytesIO(png)) as image:
            if image.width < min_width or image.height < min_height:
                return False
            extrema = image.convert("L").getextrema()
            return bool(extrema and extrema[0] != extrema[1])
    except Exception:
        return False


def _save_matplotlib_png(fig) -> bytes | None:
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight", facecolor=fig.get_facecolor())
    png = buf.getvalue()
    return png if _valid_png_bytes(png) else None


def _sequence(values: Any) -> list[Any]:
    if values is None:
        return []
    if isinstance(values, (list, tuple)):
        return list(values)
    try:
        return list(values)
    except Exception:
        return []


def _plotly_trace_data(chart: dict[str, Any]) -> tuple[str, list[Any], list[float]]:
    traces = chart.get("plotly", {}).get("data", [])
    if not traces:
        return "", [], []
    trace = traces[0] or {}
    trace_type = str(trace.get("type") or chart.get("chart_type") or "").lower()
    orientation = str(trace.get("orientation") or "").lower()

    if trace_type == "pie":
        labels = [str(label) for label in _sequence(trace.get("labels"))]
        values = [_coerce_float(value) for value in _sequence(trace.get("values"))]
        pairs = [(label, value) for label, value in zip(labels, values) if value is not None]
        return "pie", [label for label, _ in pairs], [value for _, value in pairs]

    if trace_type in {"scatter", "line"} or chart.get("chart_type") == "line":
        x_values = [str(value) for value in _sequence(trace.get("x"))]
        y_values = [_coerce_float(value) for value in _sequence(trace.get("y"))]
        pairs = [(label, value) for label, value in zip(x_values, y_values) if value is not None]
        return "line", [label for label, _ in pairs], [value for _, value in pairs]

    if trace_type == "histogram" or chart.get("chart_type") == "histogram":
        values = [_coerce_float(value) for value in _sequence(trace.get("x"))]
        return "histogram", [], [value for value in values if value is not None]

    if trace_type == "bar" or chart.get("chart_type") in {"bar", "horizontal_bar"}:
        if orientation == "h" or chart.get("chart_type") == "horizontal_bar":
            labels = [str(label) for label in _sequence(trace.get("y"))]
            values = [_coerce_float(value) for value in _sequence(trace.get("x"))]
        else:
            labels = [str(label) for label in _sequence(trace.get("x"))]
            values = [_coerce_float(value) for value in _sequence(trace.get("y"))]
        pairs = [(label, value) for label, value in zip(labels, values) if value is not None]
        return "bar", [label for label, _ in pairs], [value for _, value in pairs]

    return "", [], []


def _render_plotly_trace_with_matplotlib(chart: dict[str, Any], ax) -> bool:
    plot_type, labels, values = _plotly_trace_data(chart)
    if plot_type == "pie" and len(labels) >= 2 and len(values) >= 2 and sum(values) != 0:
        ax.pie(values[:12], labels=labels[:12], autopct="%1.0f%%", startangle=90)
        ax.axis("equal")
        return True
    if plot_type == "line" and len(labels) >= 2 and len(values) >= 2:
        ax.plot(labels[:40], values[:40], marker="o", color="#118DFF", linewidth=2.2)
        ax.tick_params(axis="x", rotation=35)
        ax.set_ylabel("Value")
        return True
    if plot_type == "histogram" and len(values) >= 2:
        ax.hist(values, bins=min(20, max(5, len(values) // 3)), color="#118DFF", edgecolor="white")
        ax.set_ylabel("Count")
        return True
    if plot_type == "bar" and len(labels) >= 2 and len(values) >= 2:
        bars = ax.barh(labels[:20], values[:20], color=plt.cm.Blues(np.linspace(0.45, 0.85, min(len(labels), 20))))
        ax.set_xlabel("Value")
        ax.invert_yaxis()
        max_value = max(abs(value) for value in values[:20]) or 1
        for bar, value in zip(bars, values[:20]):
            ax.text(bar.get_width() + max_value * 0.01, bar.get_y() + bar.get_height() / 2, f"{value:,.0f}", va="center", fontsize=8)
        return True

    traces = chart.get("plotly", {}).get("data", [])
    if traces and str((traces[0] or {}).get("type") or "").lower() == "table":
        header = ((traces[0] or {}).get("header") or {}).get("values") or []
        cells = ((traces[0] or {}).get("cells") or {}).get("values") or []
        if header and cells:
            rows = list(zip(*[_sequence(col)[:10] for col in cells]))
            ax.axis("off")
            table = ax.table(
                cellText=[[str(value) for value in row] for row in rows],
                colLabels=[str(value) for value in header],
                loc="center",
                cellLoc="left",
            )
            table.auto_set_font_size(False)
            table.set_fontsize(8)
            table.scale(1, 1.25)
            return True
    return False

def _fallback_matplotlib_chart(chart: dict[str, Any], width: int, height: int) -> bytes | None:
    """Render a real fallback chart using matplotlib when Plotly/Kaleido fails."""
    try:
        metadata = chart.get("metadata", {})
        title = chart.get("title", "Chart")

        dpi = 100
        fig_w = width / dpi
        fig_h = height / dpi

        fig, ax = plt.subplots(figsize=(fig_w, fig_h), facecolor="#F8FAFC")
        ax.set_facecolor("#FFFFFF")
        ax.set_title(title, fontsize=14, fontweight="bold", color="#1E293B", pad=12)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        if _render_plotly_trace_with_matplotlib(chart, ax):
            png = _save_matplotlib_png(fig)
            plt.close(fig)
            return png

        top_cats = metadata.get("top_categories", {})
        if top_cats and isinstance(top_cats, dict):
            cat_name = list(top_cats.keys())[0]
            cat_data = top_cats[cat_name]
            if isinstance(cat_data, list) and len(cat_data) > 0:
                labels = []
                values = []
                for item in cat_data[:10]:
                    if isinstance(item, dict):
                        lbl = item.get("label", item.get("value", ""))
                        val = item.get("value", item.get("count", 0))
                        numeric = _coerce_float(val)
                        if lbl is not None and numeric is not None:
                            labels.append(str(lbl)[:20])
                            values.append(numeric)
                if len(labels) >= 2 and len(values) >= 2:
                    colors = plt.cm.Blues(np.linspace(0.4, 0.85, len(labels)))
                    bars = ax.barh(labels, values, color=colors, edgecolor="white", height=0.65)
                    ax.set_xlabel("Value", fontsize=10, color="#475569")
                    max_value = max(abs(value) for value in values) or 1
                    for bar, value in zip(bars, values):
                        ax.text(bar.get_width() + max_value * 0.01, bar.get_y() + bar.get_height() / 2,
                                f"{value:,.0f}", va="center", fontsize=8, color="#475569")
                    ax.invert_yaxis()
                    png = _save_matplotlib_png(fig)
                    plt.close(fig)
                    return png

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
                png = _save_matplotlib_png(fig)
                plt.close(fig)
                return png

        plt.close(fig)
        logger.warning("No plottable fallback data for chart %s", chart.get("chart_id", "unknown"))
        return None
    except Exception:
        logger.exception("Matplotlib fallback failed for chart %s", chart.get("chart_id", "unknown"))
        return None

def chart_to_png_bytes(chart: dict[str, Any], width: int = 980, height: int = 520) -> bytes | None:
    """Render a chart spec to PNG bytes.

    Export requirements:
    - Prefer Plotly + Kaleido when it works.
    - If Kaleido/Chromium fails, always fall back to a matplotlib renderer so export never silently drops charts.
    """
    figure = _plotly_figure(chart)

    if figure is not None:
        try:
            # NOTE: Kaleido can fail in some CI/VM setups due to missing/invalid Chromium args.
            png = pio.to_image(figure, format="png", width=width, height=height, scale=1)
            if _valid_png_bytes(png):
                return png
            logger.warning("Plotly->PNG produced invalid PNG for chart %s", chart.get("chart_id", "unknown"))
        except Exception as exc:
            logger.warning(
                "Plotly->PNG render failed for chart %s; falling back to matplotlib. Error=%s",
                chart.get("chart_id", "unknown"),
                str(exc)[:300],
            )

    # Fallback to matplotlib (best-effort)
    try:
        png = _fallback_matplotlib_chart(chart, width, height)
        return png if _valid_png_bytes(png) else None
    except Exception:
        logger.exception("Matplotlib fallback failed for chart %s", chart.get("chart_id", "unknown"))
        return None



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
def build_export_bundle(
    report: dict[str, Any],
    chart_ids: list[str] | None = None,
    width: int = 980,
    height: int = 520,
) -> ExportBundle:
    """Create a validated export bundle shared by PDF, PPTX, Excel, and snapshots."""
    selected_charts = filter_charts(report, chart_ids)
    rendered: list[ExportChart] = []
    for chart in selected_charts:
        png = chart_to_png_bytes(chart, width=width, height=height)
        if png and _valid_png_bytes(png):
            rendered.append(ExportChart(chart=chart, png=png))
        else:
            logger.warning("Chart %s was selected for export but could not be rendered", chart.get("chart_id", "unknown"))
    return ExportBundle(
        report=report,
        charts=rendered,
        requested_chart_count=len(selected_charts),
        chart_ids=chart_ids,
    )


def validate_export_bundle(bundle: ExportBundle) -> dict[str, Any]:
    validation = bundle.validation
    validation["is_valid"] = bundle.requested_chart_count == 0 or bundle.rendered_chart_count > 0
    validation["has_visuals"] = bundle.rendered_chart_count > 0
    return validation