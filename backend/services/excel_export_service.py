from __future__ import annotations

import io
from typing import Any

import pandas as pd
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Font, PatternFill


def _safe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{key: str(value) if isinstance(value, (dict, list)) else value for key, value in row.items()} for row in rows]


def _chart_rows_from_spec(chart: dict[str, Any]) -> list[tuple[str, float]]:
    traces = chart.get("plotly", {}).get("data", [])
    if not traces:
        return []
    trace = traces[0]
    labels = trace.get("x", [])
    values = trace.get("y", [])
    if chart.get("chart_type") == "pie":
        labels = trace.get("labels", [])
        values = trace.get("values", [])
    rows: list[tuple[str, float]] = []
    for label, value in zip(labels, values):
        try:
            rows.append((str(label), float(value)))
        except Exception:
            continue
    return rows[:20]


def _add_excel_chart(sheet, start_row: int, title: str, chart_type: str) -> int:
    category_ref = Reference(sheet, min_col=1, min_row=start_row + 1, max_row=start_row + 20)
    value_ref = Reference(sheet, min_col=2, min_row=start_row, max_row=start_row + 20)
    if chart_type in {"line"}:
        chart = LineChart()
    elif chart_type in {"pie"}:
        chart = PieChart()
    else:
        chart = BarChart()
    chart.title = title[:80]
    chart.height = 7
    chart.width = 13
    chart.add_data(value_ref, titles_from_data=True)
    chart.set_categories(category_ref)
    sheet.add_chart(chart, f"E{start_row}")
    return start_row + 24


def build_executive_excel(
    report: dict[str, Any],
    raw_df: pd.DataFrame,
    summary: dict[str, Any],
    chart_ids: list[str] | None = None,
    package: str = "executive",
) -> bytes:
    buffer = io.BytesIO()
    selected = set(chart_ids or [])
    charts = [chart for chart in report.get("chart_specs", []) if not selected or chart.get("chart_id") in selected]
    kpis = report.get("kpi_cards", [])

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        wb = writer.book
        ws = wb.create_sheet("Dashboard Summary")
        ws["A1"] = report.get("branding", {}).get("report_title", "Executive Dashboard Summary")
        ws["A1"].font = Font(size=16, bold=True)
        ws["A2"] = f"Dataset: {report.get('dataset_id', '')}"
        ws["A3"] = f"Package: {package.title()}"

        ws["A5"] = "KPI"
        ws["B5"] = "Value"
        ws["C5"] = "Delta %"
        ws["D5"] = "Status"
        for c in ("A5", "B5", "C5", "D5"):
            ws[c].font = Font(bold=True, color="FFFFFF")
            ws[c].fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")

        row = 6
        for card in kpis[:12]:
            ws[f"A{row}"] = card.get("label", "")
            ws[f"B{row}"] = card.get("value", "")
            ws[f"C{row}"] = card.get("delta_percentage")
            ws[f"D{row}"] = card.get("status", "")
            row += 1
        ws.conditional_formatting.add(
            f"C6:C{max(row - 1, 6)}",
            CellIsRule(operator="greaterThan", formula=["0"], fill=PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")),
        )
        ws.conditional_formatting.add(
            f"C6:C{max(row - 1, 6)}",
            CellIsRule(operator="lessThan", formula=["0"], fill=PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")),
        )

        start = max(row + 2, 20)
        for chart in charts[:4]:
            points = _chart_rows_from_spec(chart)
            if len(points) < 2:
                continue
            ws[f"A{start}"] = "Label"
            ws[f"B{start}"] = chart.get("title", "Value")
            ws[f"A{start}"].font = Font(bold=True)
            ws[f"B{start}"].font = Font(bold=True)
            for idx, (label, value) in enumerate(points, start=start + 1):
                ws[f"A{idx}"] = label
                ws[f"B{idx}"] = value
            start = _add_excel_chart(ws, start, chart.get("title", "Chart"), chart.get("chart_type", "bar"))

        raw_df.to_excel(writer, sheet_name="Raw Data", index=False)
        missing_by_column = summary.get("missing_values_by_column", {})
        dtypes = summary.get("dtypes", {})
        schema_rows = [
            {
                "column": column,
                "dtype": dtypes.get(column, str(raw_df[column].dtype)),
                "missing_count": int(missing_by_column.get(column, 0)),
                "unique_count": int(raw_df[column].nunique(dropna=True)),
                "completeness_pct": round((1 - int(missing_by_column.get(column, 0)) / max(len(raw_df), 1)) * 100, 2),
            }
            for column in raw_df.columns
        ]
        pd.DataFrame(schema_rows).to_excel(writer, sheet_name="Column Schema", index=False)

        for worksheet in writer.book.worksheets:
            worksheet.freeze_panes = "A2"
            for column_cells in worksheet.columns:
                max_length = max(len(str(cell.value or "")) for cell in column_cells)
                worksheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, 12), 48)

    return buffer.getvalue()
