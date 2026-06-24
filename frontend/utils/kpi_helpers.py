from __future__ import annotations

import json
import re

import pandas as pd
import streamlit as st

def build_default_kpis(df: pd.DataFrame, dataset_id: str, domain_context: str | None = None) -> list[dict]:
    numeric, categorical, datetime_cols = local_column_groups(df)
    domain = _infer_domain_context(df, domain_context)
    summary = local_summary(df)
    rows = int(summary.get("row_count", 0) or 0)
    cells = max(rows * int(summary.get("column_count", 0) or 0), 1)
    missing = int(summary.get("total_missing_values", 0) or 0)
    duplicate_rows = int(summary.get("duplicate_rows", 0) or 0)

    def card(kpi_id: str, title: str, value: object, metric_type: str, method: str, status: str, explanation: str, evidence: str) -> dict:
        formatted = _format_kpi_value(value, metric_type)
        return {
            "kpi_id": kpi_id,
            "title": title,
            "label": title,
            "value": formatted,
            "raw_value": value,
            "formatted_value": formatted,
            "metric_type": metric_type,
            "calculation_method": method,
            "sample_size": rows,
            "status": status,
            "short_interpretation": explanation,
            "business_evidence": evidence,
            "description": explanation,
            "business_context": evidence,
            "reason": evidence,
            "action": "Add this KPI to the board when it supports a decision or monitoring threshold.",
            "expected_impact": "Improves executive scan speed and keeps exports useful by default.",
            "add_to_board_enabled": True,
            "icon": "shield" if "quality" in kpi_id or "duplicate" in kpi_id else "chart",
        }

    kpis: list[dict] = [
        card("records_analyzed", "Records Analyzed", rows, "count", "Count of dataset rows", "neutral", "Total evidence base available for this analysis.", f"Calculated from dataframe length for {dataset_id}."),
        card("data_completeness", "Data Completeness", (1 - missing / cells) * 100, "percent", "Non-missing cells divided by total cells", "good" if missing == 0 else "warning" if missing / cells < 0.1 else "risk", "Completeness indicates how reliable charts and KPI comparisons are likely to be.", f"{missing:,} missing cells across {cells:,} total cells."),
        card("duplicate_rate", "Duplicate Rate", (duplicate_rows / max(rows, 1)) * 100, "percent", "Duplicate rows divided by total rows", "good" if duplicate_rows == 0 else "warning" if duplicate_rows / max(rows, 1) < 0.05 else "risk", "Duplicate records can inflate counts, totals, and category shares.", f"{duplicate_rows:,} duplicate rows detected."),
    ]

    preferred = {"insurance": ["charges", "premium", "claim"], "healthcare": ["risk", "score", "bmi", "age", "prevalence"], "ecommerce": ["churn", "revenue", "retention", "spend"], "sales": ["sales", "profit", "conversion", "quantity"]}.get(domain, [])
    ordered_numeric = sorted(numeric, key=lambda col: 0 if any(token in str(col).lower() for token in preferred) else 1)
    for column in ordered_numeric[:3]:
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if series.empty:
            continue
        is_rate = any(token in str(column).lower() for token in ["rate", "pct", "percent", "churn", "risk"])
        value = float(series.mean() * 100) if is_rate and series.max() <= 1 else float(series.mean())
        metric_type = "percent" if is_rate else "number"
        kpis.append(card(f"avg_{_kpi_id_from_label(column)}", f"Average {column}", value, metric_type, f"Mean of numeric column {column}", "neutral", f"The typical {column} value is {_format_kpi_value(value, metric_type)} across valid records.", f"Based on {len(series):,} non-empty values; median is {_format_kpi_value(float(series.median()))}."))

    for column in categorical[:2]:
        counts = df[column].astype("string").fillna("Unknown").value_counts()
        if counts.empty:
            continue
        share = float(counts.iloc[0] / max(rows, 1) * 100)
        kpis.append(card(f"top_{_kpi_id_from_label(column)}", f"Top {column}", str(counts.index[0]), "category", f"Most frequent category in {column}", "warning" if share >= 80 else "neutral", f"{counts.index[0]} is the largest segment at {share:.1f}% of records.", f"{int(counts.iloc[0]):,} of {rows:,} records fall in this segment."))

    if datetime_cols and numeric:
        date_col, metric = datetime_cols[0], numeric[0]
        temp = df[[date_col, metric]].copy()
        temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
        temp[metric] = pd.to_numeric(temp[metric], errors="coerce")
        trend = temp.dropna().sort_values(date_col)
        if len(trend) >= 4:
            first = float(trend[metric].head(max(1, len(trend) // 3)).mean())
            last = float(trend[metric].tail(max(1, len(trend) // 3)).mean())
            change = ((last - first) / abs(first) * 100) if first else 0.0
            kpis.append(card(f"trend_{_kpi_id_from_label(metric)}", f"{metric} Trend", change, "percent", f"Change between early and latest thirds ordered by {date_col}", "good" if change > 5 else "risk" if change < -5 else "neutral", f"Latest period average is associated with a {change:.1f}% directional change.", f"Compared {len(trend):,} dated records from {date_col}."))
    return kpis[:8]
def build_data_anomaly_report(df: pd.DataFrame) -> list[dict]:
    rows = max(len(df), 1)
    anomalies: list[dict] = []

    def add(severity: str, column: str, issue_type: str, affected: int, explanation: str, action: str) -> None:
        if affected <= 0:
            return
        anomalies.append({"anomaly_id": f"{issue_type}_{_kpi_id_from_label(column)}_{len(anomalies)}", "severity": severity, "column": column, "issue_type": issue_type, "records_affected": int(affected), "explanation": explanation, "recommended_cleaning_action": action})

    for column in df.columns:
        missing = int(df[column].isna().sum())
        rate = missing / rows
        add("high" if rate >= 0.25 else "medium" if rate >= 0.05 else "low", column, "missing_values", missing, f"{missing:,} records are blank in {column}.", "Fill, classify as Unknown, or exclude this column from executive KPIs until reviewed.")
        unique = int(df[column].nunique(dropna=True))
        if unique <= 1:
            add("medium", column, "constant_column", rows, f"{column} has one or zero distinct values.", "Remove from visual recommendations unless it is a required identifier.")
        elif unique / rows > 0.8 and not pd.api.types.is_numeric_dtype(df[column]):
            add("low", column, "high_cardinality", unique, f"{column} has {unique:,} distinct values, which may clutter charts.", "Use search/filter views or group smaller values before charting.")
        if not pd.api.types.is_numeric_dtype(df[column]):
            counts = df[column].astype("string").fillna("Unknown").value_counts()
            if not counts.empty and counts.iloc[0] / rows > 0.8:
                add("medium", column, "category_dominance", int(counts.iloc[0]), f"'{counts.index[0]}' represents {counts.iloc[0] / rows * 100:.1f}% of records.", "Check whether this dominance is expected before using the field for segment comparisons.")
            if any(token in str(column).lower() for token in ["date", "time", "dob", "created", "updated"]):
                parsed = pd.to_datetime(df[column], errors="coerce")
                invalid = int(parsed.isna().sum() - df[column].isna().sum())
                add("medium", column, "invalid_dates", invalid, f"{invalid:,} non-empty values could not be parsed as dates.", "Standardize date formats or keep this field out of trend charts.")

    duplicate_rows = int(df.duplicated().sum())
    add("high" if duplicate_rows / rows >= 0.1 else "medium", "Dataset", "duplicate_rows", duplicate_rows, f"{duplicate_rows:,} repeated rows were detected.", "Remove exact duplicates before publishing totals or frequency charts.")

    unusual = ("age", "price", "charge", "revenue", "sales", "profit", "quantity", "cost", "premium")
    for column in df.select_dtypes(include="number").columns:
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if len(series) >= 4:
            q1, q3 = series.quantile(0.25), series.quantile(0.75)
            iqr = q3 - q1
            if pd.notna(iqr) and iqr > 0:
                lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                count = int(((series < lower) | (series > upper)).sum())
                add("high" if count / rows >= 0.05 else "medium", column, "iqr_outliers", count, f"{count:,} values sit outside the IQR expected range.", "Review, cap, or keep with a clear note depending on business validity.")
            std = float(series.std())
            if std > 0 and len(series) >= 8:
                z_count = int((((series - float(series.mean())) / std).abs() > 3).sum())
                add("medium", column, "zscore_outliers", z_count, f"{z_count:,} values are more than 3 standard deviations from the mean.", "Inspect these records before relying on averages.")
        if any(token in str(column).lower() for token in unusual):
            neg = int((series < 0).sum())
            add("medium", column, "unexpected_negative_values", neg, f"{neg:,} negative values appear in a field that is usually non-negative.", "Confirm whether negatives are valid adjustments, refunds, or data-entry errors.")
    severity_order = {"high": 0, "medium": 1, "low": 2}
    return sorted(anomalies, key=lambda item: (severity_order.get(item["severity"], 9), -int(item["records_affected"])))[:30]

def build_storyboard_kpis(schema: dict) -> list[dict]:
    """Build simple KPI cards from visual builder schema metrics."""
    kpis = []
    row_count = 0
    semantic = schema.get("semantic_layer", [])
    measures = schema.get("measures", [])
    for field in semantic:
        if field.get("semantic_role") in {"revenue_currency_column"}:
            kpis.append({"label": f"Total {field['name']}", "value": "-", "icon": "chart"})
        elif field.get("semantic_role") in {"percentage_ratio_column"}:
            kpis.append({"label": field["name"].replace("_", " ").title(), "value": "-", "icon": "metric"})
    if not kpis:
        if measures:
            for measure in measures[:2]:
                kpis.append({"label": measure["name"].replace("_", " ").title(), "value": "-", "icon": "metric"})
        else:
            kpis.append({"label": "Records", "value": f"{row_count:,}" if row_count else "-", "icon": "table"})
    return kpis[:4]

def local_summary(df: pd.DataFrame) -> dict:
    missing = int(df.isna().sum().sum())
    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "total_missing_values": missing,
        "duplicate_rows": int(df.duplicated().sum()),
        "column_types": {column: str(dtype) for column, dtype in df.dtypes.items()},
        "missing_values_by_column": df.isna().sum().astype(int).to_dict(),
    }
def local_column_groups(df: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
    numeric = df.select_dtypes(include="number").columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()
    date_tokens = ("date", "time", "year", "month", "created", "updated", "dob")
    for column in df.columns:
        if column in numeric or column in datetime_cols:
            continue
        if not any(token in str(column).lower() for token in date_tokens):
            continue
        parsed = pd.to_datetime(df[column], errors="coerce")
        if parsed.notna().mean() >= 0.8:
            datetime_cols.append(column)
    categorical = [column for column in df.columns if column not in numeric and column not in datetime_cols]
    return numeric, categorical, datetime_cols
def quality_score(summary: dict) -> tuple[int, str, list[str]]:
    rows = int(summary.get("row_count", 0) or 0)
    cols = int(summary.get("column_count", 0) or 0)
    missing = int(summary.get("total_missing_values", 0) or 0)
    duplicates = int(summary.get("duplicate_rows", 0) or 0)
    cells = max(rows * cols, 1)
    completeness = max(0, 100 - (missing / cells * 100))
    duplicate_penalty = min(20, (duplicates / max(rows, 1)) * 100)
    usability_penalty = 8 if cols < 2 else 0
    score = int(max(0, min(100, round(completeness - duplicate_penalty - usability_penalty))))
    grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D"
    reasons = [f"Completeness is {completeness:.1f}% across {cols:,} columns."]
    reasons.append("No duplicate rows detected." if duplicates == 0 else f"{duplicates:,} duplicate rows may need review.")
    if missing:
        reasons.append(f"{missing:,} missing cells can reduce confidence in segmented charts.")
    else:
        reasons.append("No missing cells detected in this dataset.")
    return score, grade, reasons[:3]
_build_storyboard_kpis = build_storyboard_kpis
_local_summary = local_summary
_local_column_groups = local_column_groups
_quality_score = quality_score


def _format_kpi_value(value: object, metric_type: str = "number") -> str:
    if isinstance(value, (int, float)) and pd.notna(value):
        if metric_type == "percent":
            return f"{float(value):.1f}%"
        if abs(float(value)) >= 1000:
            return f"{float(value):,.2f}".rstrip("0").rstrip(".")
        return f"{float(value):.2f}".rstrip("0").rstrip(".")
    return str(value)
def _infer_domain_context(df: pd.DataFrame, explicit: str | None = None) -> str:
    if explicit:
        return explicit.lower()
    tokens = " ".join(str(col).lower() for col in df.columns)
    if any(token in tokens for token in ["charges", "smoker", "claim", "premium", "policy"]):
        return "insurance"
    if any(token in tokens for token in ["bmi", "blood", "medical", "diagnosis", "risk", "health", "patient"]):
        return "healthcare"
    if any(token in tokens for token in ["churn", "retention", "customer", "revenue"]):
        return "ecommerce"
    if any(token in tokens for token in ["sales", "profit", "product", "conversion", "order"]):
        return "sales"
    return "general"
def _local_kpi_cards(df: pd.DataFrame) -> list[dict]:
    dataset_id = str(st.session_state.get("active_dataset_id") or st.session_state.get("selected_dataset_id") or "local_dataset")
    return build_default_kpis(df, dataset_id)
def _sparkline_html(values: list) -> str:
    numeric = [float(value) for value in values if isinstance(value, (int, float))]
    if not numeric:
        return ""
    max_value = max(abs(value) for value in numeric) or 1
    bars = []
    for value in numeric[-8:]:
        height = max(14, int(abs(value) / max_value * 34))
        bars.append(f'<span class="spark-bar" style="height:{height}px"></span>')
    return f'<div class="sparkline">{"".join(bars)}</div>'
def _kpi_icon_svg(icon: str) -> str:
    paths = {
        "table": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 4v16"/>',
        "shield": '<path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6l7-3z"/><path d="M9 12l2 2 4-5"/>',
        "chart": '<path d="M4 19h16"/><rect x="6" y="10" width="3" height="7"/><rect x="11" y="6" width="3" height="11"/><rect x="16" y="12" width="3" height="5"/>',
        "users": '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2"/><path d="M3 19c1-4 4-6 6-6s5 2 6 6"/><path d="M14 15c2 0 4 1 5 4"/>',
        "metric": '<path d="M4 17l5-5 3 3 7-8"/><path d="M15 7h4v4"/>',
    }
    path = paths.get(icon, paths["metric"])
    return f'<svg class="kpi-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">{path}</svg>'
def _safe_trend_text(value: str | None) -> str:
    candidate = (value or "").strip()
    if candidate.startswith("_") or candidate.startswith(":material"):
        return ""
    return candidate
def _kpi_id_from_label(label: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_]+", "_", str(label or "metric").strip().lower())
    return re.sub(r"_+", "_", normalized).strip("_") or "metric"
