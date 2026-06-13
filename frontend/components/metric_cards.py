import streamlit as st


def render_summary_metrics(summary: dict) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Rows", f"{summary.get('row_count', 0):,}")
    col2.metric("Columns", f"{summary.get('column_count', 0):,}")
    col3.metric("Missing Values", f"{summary.get('total_missing_values', 0):,}")
    col4.metric("Duplicate Rows", f"{summary.get('duplicate_rows', 0):,}")
