import streamlit as st


def _format_pct(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.1f}%"


def render_summary_metrics(summary: dict) -> None:
    missing = int(summary.get("total_missing_values", 0) or 0)
    duplicates = int(summary.get("duplicate_rows", 0) or 0)
    total_cells = max(int(summary.get("row_count", 0) or 0) * int(summary.get("column_count", 0) or 0), 1)
    completeness = round((1 - missing / total_cells) * 100, 2)
    quality_label = "Ready" if missing == 0 and duplicates == 0 else "Review"

    st.markdown(
        """
        <style>
        .summary-strip {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 12px;
            margin: 8px 0 18px;
        }
        .summary-tile {
            border: 1px solid rgba(148, 163, 184, 0.26);
            border-radius: 8px;
            padding: 12px 14px;
            background: rgba(255, 255, 255, 0.06);
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.045);
        }
        .summary-label {
            font-size: 0.72rem;
            color: #64748B;
            font-weight: 700;
            text-transform: uppercase;
        }
        .summary-value {
            font-size: 1.35rem;
            color: var(--text-color);
            font-weight: 800;
            margin-top: 4px;
        }
        @media (max-width: 900px) {
            .summary-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    tiles = [
        ("Rows", f"{summary.get('row_count', 0):,}"),
        ("Columns", f"{summary.get('column_count', 0):,}"),
        ("Completeness", _format_pct(completeness)),
        ("Missing", f"{missing:,}"),
        ("Quality", quality_label),
    ]
    html = "".join(
        f'<div class="summary-tile"><div class="summary-label">{label}</div><div class="summary-value">{value}</div></div>'
        for label, value in tiles
    )
    st.markdown(f'<div class="summary-strip">{html}</div>', unsafe_allow_html=True)
