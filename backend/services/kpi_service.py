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
    return {
        "kpi_id": _kpi_id(label),
        "label": label,
        "value": to_json_safe(value),
        "format": value_format,
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
    clean = pd.to_numeric(series, errors="coerce").dropna()
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
    values = (grouped.sum() if aggregation == "sum" else grouped.mean()).round(4).tolist()
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
    grouped = (groupby.sum() if aggregation == "sum" else groupby.mean()).sort_values(ascending=False)
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
    metric_columns = financial_columns or metric_candidates[:3]

    for column in metric_columns[:4]:
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if series.empty:
            continue
        pretty = _pretty_name(column)
        suitability = metric_suitability(column, series)
        aggregation = suitability["recommended_aggregation"]
        aggregate_name = aggregate_label(aggregation)
        total = round(float(series.sum()), 4)
        average = round(float(series.mean()), 4)
        primary_value = round(aggregate_series(series, aggregation), 4)
        current, previous, delta, trend, status = _series_delta_for_metric(series, aggregation)
        driver = _top_segment_context(df, column, categorical_columns, aggregation)
        reason = (
            f"{driver['segment']} contributes {driver['share_pct']}% of total {pretty} across {driver['dimension']}."
            if driver and aggregation == "sum" and driver.get("share_pct") is not None
            else f"{driver['segment']} has the highest average {pretty} across {driver['dimension']}."
            if driver and aggregation == "average"
            else f"{pretty} is calculated from {int(series.count())} usable numeric records."
        )
        action = (
            f"Prioritize the drivers behind {driver['segment']} and compare them against weaker {driver['dimension']} segments."
            if driver
            else f"Add a segment field to explain what is driving {pretty}."
        )
        cards.append(
            _format_card(
                f"{aggregate_name.title()} {pretty}",
                primary_value,
                category="business",
                current_value=current,
                previous_value=previous,
                delta_percentage=delta,
                trend=trend,
                status=status,
                business_context=f"{aggregate_name.title()} {pretty}; selected because {suitability['reason']}",
                description=reason,
            )
        )
        cards[-1]["sparkline"] = _sparkline(series, aggregation=aggregation)
        cards[-1]["reason"] = reason
        cards[-1]["recommended_action"] = action
        cards[-1]["expected_impact"] = _impact_from_delta(delta)
        cards[-1]["metric_suitability"] = suitability
        cards[-1]["data_confidence"] = cards[-1]["confidence_score"]
        cards[-1]["business_confidence"] = suitability["business_confidence"]
        cards[-1]["business_relevance"] = suitability["business_relevance"]
        cards[-1]["evidence"] = {
            "records": int(series.count()),
            "current_period": to_json_safe(round(current, 4)) if current is not None else None,
            "previous_period": to_json_safe(round(previous, 4)) if previous is not None else None,
            "top_segment": driver,
            "aggregation": aggregation,
            "total": to_json_safe(total),
            "average": to_json_safe(average),
        }
        cards[-1]["statistical_explanation"] = build_kpi_explanation(
            label=f"{aggregate_name.title()} {pretty}",
            formula=f"{aggregate_name} of {pretty}",
            sample_size=int(series.count()),
            is_rate=cards[-1]["format"] == "percent",
            series=series,
        )
        cards.append(
            _format_card(
                f"Average {pretty}",
                average,
                category="business",
                business_context=f"Average value across usable {pretty} records.",
            )
        )
        cards[-1]["sparkline"] = _sparkline(series, aggregation="average")
        cards[-1]["reason"] = f"Average {pretty} is based on {int(series.count())} non-empty records."
        cards[-1]["recommended_action"] = f"Monitor outliers and segment-level variance before using average {pretty} for targets."
        cards[-1]["expected_impact"] = "Better segment targeting can improve planning accuracy and reduce blended-average bias."
        cards[-1]["evidence"] = {"records": int(series.count()), "min": to_json_safe(series.min()), "max": to_json_safe(series.max())}
        cards[-1]["statistical_explanation"] = build_kpi_explanation(
            label=f"Average {pretty}",
            formula=f"mean of {pretty}",
            sample_size=int(series.count()),
            series=series,
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
        grouped = (groupby.sum(numeric_only=True) if aggregation == "sum" else groupby.mean(numeric_only=True)).sort_values(ascending=False).head(1)
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
