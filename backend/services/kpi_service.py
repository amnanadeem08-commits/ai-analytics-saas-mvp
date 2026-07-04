from __future__ import annotations

from typing import Any

import pandas as pd

from backend.core.theme_manager import theme_manager
from backend.processing.column_detector import detect_column_types
from backend.services.metric_suitability_service import aggregate_label, aggregate_series, metric_suitability, select_primary_metric
from backend.services.statistical_explanation_service import build_kpi_explanation
from backend.utils.response_utils import to_json_safe


FINANCIAL_HINTS = (
    "revenue",
    "sales",
    "amount",
    "price",
    "cost",
    "profit",
    "income",
    "margin",
    "spend",
    "expense",
)


def _kpi_id(label: str) -> str:
    return label.lower().replace(" ", "_").replace("/", "_")


def _pretty_name(column: str) -> str:
    return column.replace("_", " ").replace("-", " ").strip().title()


def _is_financial_column(column: str) -> bool:
    lowered = column.lower().replace(" ", "_").replace("-", "_")
    return any(hint in lowered for hint in FINANCIAL_HINTS)


def _unit_for_column(column: str) -> str:
    lowered = column.lower().replace(" ", "_").replace("-", "_")
    if lowered == "age" or lowered.endswith("_age"):
        return "years"
    if "daily_social_media_hours" in lowered:
        return "h/day"
    if "sleep" in lowered and "hour" in lowered:
        return "h"
    if "screen_time_before_sleep" in lowered:
        return "h"
    if "hour" in lowered or "duration" in lowered:
        return "h"
    return ""


def _format_value_with_unit(value: Any, value_format: str = "number", unit: str = "") -> str:
    if isinstance(value, (int, float)) and pd.notna(value):
        if value_format == "percent":
            formatted = f"{float(value):.1f}%"
        elif value_format == "integer":
            formatted = f"{int(round(float(value))):,}"
        elif abs(float(value)) >= 1000:
            formatted = f"{float(value):,.2f}".rstrip("0").rstrip(".")
        else:
            formatted = f"{float(value):.2f}".rstrip("0").rstrip(".")
        return f"{formatted} {unit}".strip()
    return str(value)


def _apply_aggregation(series: pd.Series, aggregation: str) -> float:
    return round(float(aggregate_series(series, aggregation)), 4)


def _format_card(
    label: str,
    value: Any,
    *,
    category: str = "summary",
    value_format: str = "number",
    description: str = "",
    current_value: Any = None,
    previous_value: Any = None,
    delta_percentage: float | None = None,
    trend: str = "neutral",
    status: str = "neutral",
    business_context: str = "",
    aggregation: str | None = None,
    unit: str = "",
) -> dict[str, Any]:
    theme = theme_manager.get_theme()
    status_colors = {
        "positive": theme.success,
        "negative": theme.danger,
        "warning": theme.warning,
        "neutral": theme.neutral,
    }
    trend_arrows = {"up": "^", "down": "v", "neutral": "->"}
    icon_map = {
        "dataset": "table",
        "quality": "shield",
        "business": "chart",
        "segment": "users",
        "summary": "metric",
    }
    risk_indicator = "risk" if status in {"negative", "warning"} else "normal"
    confidence_score = 0.9 if previous_value is not None or category in {"dataset", "quality"} else 0.75
    formatted_value = _format_value_with_unit(value, value_format, unit)
    return {
        "kpi_id": _kpi_id(label),
        "label": label,
        "value": to_json_safe(value),
        "formatted_value": formatted_value,
        "unit": unit,
        "format": value_format,
        "aggregation": aggregation,
        "aggregation_options": ["Auto", "Average", "Sum", "Median", "Min", "Max", "Count"],
        "category": category,
        "description": description,
        "current_value": to_json_safe(current_value if current_value is not None else value),
        "previous_value": to_json_safe(previous_value),
        "delta_percentage": to_json_safe(delta_percentage),
        "trend": trend,
        "trend_arrow": trend_arrows.get(trend, "->"),
        "status": status,
        "status_color": status_colors.get(status, theme.neutral),
        "business_context": business_context or description,
        "icon": icon_map.get(category, "metric"),
        "risk_indicator": risk_indicator,
        "confidence_score": confidence_score,
    }


def _series_delta(series: pd.Series) -> tuple[float | None, float | None, float | None, str, str]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if len(clean) < 2:
        return None, None, None, "neutral", "neutral"
    midpoint = max(len(clean) // 2, 1)
    previous = float(clean.iloc[:midpoint].sum())
    current = float(clean.iloc[midpoint:].sum())
    delta = None if previous == 0 else round((current - previous) / abs(previous) * 100, 2)
    if delta is None or delta == 0:
        return current, previous, delta, "neutral", "neutral"
    if delta > 0:
        return current, previous, delta, "up", "positive"
    return current, previous, delta, "down", "negative"


def _series_delta_for_metric(series: pd.Series, aggregation: str) -> tuple[float | None, float | None, float | None, str, str]:
    clean = series.dropna() if aggregation in {"count", "unique_count"} else pd.to_numeric(series, errors="coerce").dropna()
    if len(clean) < 2:
        return None, None, None, "neutral", "neutral"
    midpoint = max(len(clean) // 2, 1)
    previous = aggregate_series(clean.iloc[:midpoint], aggregation)
    current = aggregate_series(clean.iloc[midpoint:], aggregation)
    delta = None if previous == 0 else round((current - previous) / abs(previous) * 100, 2)
    if delta is None or delta == 0:
        return current, previous, delta, "neutral", "neutral"
    if delta > 0:
        return current, previous, delta, "up", "positive"
    return current, previous, delta, "down", "negative"


def _sparkline(series: pd.Series, buckets: int = 8, aggregation: str = "sum") -> list[float]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return []
    if len(clean) <= buckets:
        return [to_json_safe(round(float(value), 4)) for value in clean.tolist()]

    ranked = clean.reset_index(drop=True)
    groups = pd.cut(ranked.index, bins=buckets, labels=False)
    grouped = ranked.groupby(groups)
    if aggregation == "sum":
        values = grouped.sum().round(4).tolist()
    elif aggregation == "median":
        values = grouped.median().round(4).tolist()
    elif aggregation == "min":
        values = grouped.min().round(4).tolist()
    elif aggregation == "max":
        values = grouped.max().round(4).tolist()
    else:
        values = grouped.mean().round(4).tolist()
    return [to_json_safe(float(value)) for value in values]


def _top_segment_context(
    df: pd.DataFrame,
    metric_column: str,
    categorical_columns: list[str],
    aggregation: str = "sum",
) -> dict[str, Any] | None:
    if not categorical_columns:
        return None
    dimension = categorical_columns[0]
    groupby = df.groupby(dimension, dropna=False)[metric_column]
    if aggregation == "sum":
        grouped = groupby.sum().sort_values(ascending=False)
    elif aggregation == "median":
        grouped = groupby.median().sort_values(ascending=False)
    elif aggregation == "min":
        grouped = groupby.min().sort_values(ascending=False)
    elif aggregation == "max":
        grouped = groupby.max().sort_values(ascending=False)
    elif aggregation == "count":
        grouped = groupby.count().sort_values(ascending=False)
    else:
        grouped = groupby.mean().sort_values(ascending=False)
    if grouped.empty:
        return None
    top_value = float(grouped.iloc[0])
    share = round(top_value / float(grouped.sum()) * 100, 2) if aggregation == "sum" and float(grouped.sum()) else None
    return {
        "dimension": dimension,
        "segment": str(grouped.index[0]),
        "value": to_json_safe(round(top_value, 4)),
        "share_pct": share,
        "aggregation": aggregation,
    }


def _impact_from_delta(delta: float | None) -> str:
    if delta is None:
        return "Impact estimate requires at least two comparable periods."
    magnitude = abs(delta)
    if delta > 0:
        return f"If momentum holds, the next period could add roughly {round(magnitude * 0.4, 1)}%-{round(magnitude * 0.8, 1)}% uplift."
    if delta < 0:
        return f"If not corrected, the next period may remain {round(magnitude * 0.4, 1)}%-{round(magnitude * 0.8, 1)}% below prior run-rate."
    return "Expected impact is stable unless the current operating pattern changes."


def compute_kpi_cards(df: pd.DataFrame) -> list[dict[str, Any]]:
    column_types = detect_column_types(df)
    numeric_columns = column_types["numeric_columns"]
    categorical_columns = column_types["categorical_columns"]
    missing_cells = int(df.isna().sum().sum())
    total_cells = max(int(df.size), 1)

    cards: list[dict[str, Any]] = [
        _format_card("Total rows", int(len(df)), category="dataset", value_format="integer"),
        _format_card("Total columns", int(len(df.columns)), category="dataset", value_format="integer"),
        _format_card(
            "Data completeness",
            round((1 - missing_cells / total_cells) * 100, 2),
            category="quality",
            value_format="percent",
            status="positive" if missing_cells == 0 else "warning",
            business_context="Share of populated cells after cleaning.",
        ),
    ]
    cards[0]["statistical_explanation"] = build_kpi_explanation(
        label="Total rows",
        formula="a count of records",
        sample_size=int(len(df)),
    )
    cards[1]["statistical_explanation"] = build_kpi_explanation(
        label="Total columns",
        formula="a count of variables",
        sample_size=int(len(df.columns)),
    )
    cards[2]["statistical_explanation"] = build_kpi_explanation(
        label="Data completeness",
        formula="non-missing cells ÷ total cells",
        sample_size=int(total_cells),
        is_rate=True,
    )

    metric_candidates = [
        column for column in numeric_columns if metric_suitability(column, df[column])["is_valid_metric"]
    ]
    financial_columns = [col for col in metric_candidates if _is_financial_column(col)]
    nonfinancial_columns = [col for col in metric_candidates if col not in financial_columns]
    metric_columns = (financial_columns + nonfinancial_columns)[:4]

    for column in metric_columns[:4]:
        raw_series = df[column].dropna()
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        suitability = metric_suitability(column, raw_series)
        aggregation = suitability["recommended_aggregation"]
        if aggregation not in {"count", "unique_count"} and series.empty:
            continue
        pretty = _pretty_name(column)
        aggregate_name = aggregate_label(aggregation)
        unit = _unit_for_column(column)
        value_format = "integer" if aggregation in {"count", "unique_count"} else "number"
        total = round(float(series.sum()), 4) if not series.empty else None
        average = round(float(series.mean()), 4) if not series.empty else None
        primary_value = _apply_aggregation(raw_series if aggregation in {"count", "unique_count"} else series, aggregation)
        current, previous, delta, trend, status = _series_delta_for_metric(raw_series if aggregation in {"count", "unique_count"} else series, aggregation)
        driver = None if aggregation in {"unique_count"} else _top_segment_context(df, column, categorical_columns, aggregation)
        if driver and aggregation == "sum" and driver.get("share_pct") is not None:
            reason = f"{driver['segment']} contributes {driver['share_pct']}% of total {pretty} across {driver['dimension']}."
        elif driver and aggregation == "average":
            reason = f"{driver['segment']} has the highest average {pretty} across {driver['dimension']}."
        elif aggregation == "unique_count":
            reason = f"{pretty} is counted as {int(primary_value):,} unique non-empty values, not summed."
        elif aggregation == "count":
            reason = f"{pretty} is counted across {int(primary_value):,} non-empty records."
        else:
            reason = f"{pretty} is calculated from {int(series.count())} usable numeric records using {aggregate_name}."
        action = (
            f"Prioritize the drivers behind {driver['segment']} and compare them against weaker {driver['dimension']} segments."
            if driver
            else f"Review segments or filters to explain what is driving {pretty}."
        )
        display_aggregate_name = "Avg" if aggregation == "average" else aggregate_name.title()
        label = f"{display_aggregate_name} {pretty}"
        cards.append(
            _format_card(
                label,
                primary_value,
                category="business",
                value_format=value_format,
                current_value=current,
                previous_value=previous,
                delta_percentage=delta,
                trend=trend,
                status=status,
                business_context=f"{label}; selected because {suitability['reason']}",
                description=reason,
                aggregation=aggregation,
                unit=unit,
            )
        )
        cards[-1]["sparkline"] = [] if aggregation in {"count", "unique_count"} else _sparkline(series, aggregation=aggregation)
        cards[-1]["reason"] = reason
        cards[-1]["recommended_action"] = action
        cards[-1]["expected_impact"] = _impact_from_delta(delta) if delta is not None else "No benchmark or prior comparison is available for directional impact."
        cards[-1]["metric_suitability"] = suitability
        cards[-1]["data_confidence"] = cards[-1]["confidence_score"]
        cards[-1]["business_confidence"] = suitability["business_confidence"]
        cards[-1]["business_relevance"] = suitability["business_relevance"]
        cards[-1]["evidence"] = {
            "records": int(raw_series.count()),
            "current_period": to_json_safe(round(current, 4)) if current is not None else None,
            "previous_period": to_json_safe(round(previous, 4)) if previous is not None else None,
            "top_segment": driver,
            "aggregation": aggregation,
            "total": to_json_safe(total),
            "average": to_json_safe(average),
            "unit": unit,
        }
        cards[-1]["statistical_explanation"] = build_kpi_explanation(
            label=label,
            formula=f"{aggregate_name} of {pretty}",
            sample_size=int(raw_series.count()),
            is_rate=cards[-1]["format"] == "percent",
            series=series if not series.empty else None,
        )

    for column in categorical_columns[:2]:
        counts = df[column].value_counts(dropna=True)
        if counts.empty:
            continue
        top_value = str(counts.index[0])
        cards.append(
            _format_card(
                f"Top {_pretty_name(column)}",
                top_value,
                category="segment",
                value_format="text",
                description=f"{int(counts.iloc[0])} records",
                business_context=f"Most frequent segment in {column}.",
            )
        )
        cards[-1]["sparkline"] = []
        cards[-1]["reason"] = f"{top_value} appears in {int(counts.iloc[0])} records."
        cards[-1]["recommended_action"] = f"Use {top_value} as the baseline segment for comparison."
        cards[-1]["expected_impact"] = "Segment baselines help leadership focus follow-up analysis on meaningful differences."
        cards[-1]["evidence"] = {"segment": top_value, "records": int(counts.iloc[0])}
        cards[-1]["statistical_explanation"] = build_kpi_explanation(
            label=f"Top {_pretty_name(column)}",
            formula=f"mode of {column}",
            sample_size=int(counts.sum()),
        )

    return cards[:10]


def compute_business_metrics(df: pd.DataFrame) -> dict[str, Any]:
    column_types = detect_column_types(df)
    numeric_columns = column_types["numeric_columns"]
    categorical_columns = column_types["categorical_columns"]
    financial_columns = [col for col in numeric_columns if _is_financial_column(col)]

    primary_metric, suitability = select_primary_metric(df, numeric_columns)
    primary_segment = categorical_columns[0] if categorical_columns else None
    segment_leader = None

    if primary_metric and primary_segment:
        aggregation = suitability["recommended_aggregation"] if suitability else "sum"
        groupby = df.groupby(primary_segment)[primary_metric]
        if aggregation == "sum":
            grouped = groupby.sum(numeric_only=True).sort_values(ascending=False).head(1)
        elif aggregation == "median":
            grouped = groupby.median(numeric_only=True).sort_values(ascending=False).head(1)
        elif aggregation == "min":
            grouped = groupby.min(numeric_only=True).sort_values(ascending=False).head(1)
        elif aggregation == "max":
            grouped = groupby.max(numeric_only=True).sort_values(ascending=False).head(1)
        elif aggregation == "count":
            grouped = groupby.count().sort_values(ascending=False).head(1)
        else:
            grouped = groupby.mean(numeric_only=True).sort_values(ascending=False).head(1)
        if not grouped.empty:
            segment_leader = {
                "dimension": primary_segment,
                "metric": primary_metric,
                "segment": str(grouped.index[0]),
                "value": to_json_safe(round(float(grouped.iloc[0]), 4)),
                "aggregation": aggregation,
                "business_relevance": suitability.get("business_relevance") if suitability else "medium",
            }

    return {
        "primary_metric": primary_metric,
        "primary_segment": primary_segment,
        "financial_columns": financial_columns,
        "segment_leader": segment_leader,
        "metric_suitability": suitability,
    }
