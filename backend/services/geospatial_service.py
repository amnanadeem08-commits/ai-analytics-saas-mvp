from __future__ import annotations

from typing import Any

import pandas as pd

from backend.core.theme_manager import theme_manager
from backend.processing.column_detector import detect_column_types
from backend.utils.response_utils import to_json_safe


LOCATION_HINTS = {
    "country": ["country", "nation"],
    "state": ["state", "province"],
    "region": ["region", "territory", "area", "zone"],
    "city": ["city", "town"],
    "postal_code": ["postal", "zip"],
    "latitude": ["latitude", "lat"],
    "longitude": ["longitude", "lon", "lng"],
}

LOCATION_NORMALIZATION = {
    "usa": "United States",
    "us": "United States",
    "u.s.": "United States",
    "uk": "United Kingdom",
    "uae": "United Arab Emirates",
    "ny": "New York",
    "ca": "California",
    "tx": "Texas",
}

PREFERRED_METRIC_HINTS = [
    "charges",
    "charge",
    "cost",
    "revenue",
    "sales",
    "profit",
    "amount",
    "price",
    "premium",
    "claim",
    "claims",
    "total",
    "value",
]

DEPRIORITIZED_METRIC_HINTS = [
    "age",
    "id",
    "index",
    "row_id",
    "customer_id",
    "patient_id",
    "user_id",
]


def _find_location_columns(df: pd.DataFrame) -> dict[str, str]:
    found = {}
    for column in df.columns:
        lowered = str(column).lower().replace("_", " ")
        for role, hints in LOCATION_HINTS.items():
            if role not in found and any(hint in lowered for hint in hints):
                found[role] = column
    return found


def normalize_location(value: Any) -> str:
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return "Unknown"
    return LOCATION_NORMALIZATION.get(text.lower(), text.title() if text.isupper() else text)


def detect_geographic_columns(df: pd.DataFrame) -> dict[str, Any]:
    columns = _find_location_columns(df)
    available = bool(columns.get("latitude") and columns.get("longitude")) or any(
        key in columns for key in ["country", "state", "region", "city", "postal_code"]
    )
    return {
        "available": available,
        "columns": columns,
        "message": ""
        if available
        else "No geographic fields detected. Add country, state, province, region, city, postal code, latitude, or longitude for map analytics.",
    }


def _primary_metric(df: pd.DataFrame) -> str | None:
    numeric = detect_column_types(df)["numeric_columns"]
    if not numeric:
        return None
    lowered = {column: column.lower() for column in numeric}
    preferred = [column for column in numeric if any(hint in lowered[column] for hint in PREFERRED_METRIC_HINTS)]
    if preferred:
        for hint in PREFERRED_METRIC_HINTS:
            for column in preferred:
                if hint in lowered[column]:
                    return column
    viable = [column for column in numeric if not any(hint in lowered[column] for hint in DEPRIORITIZED_METRIC_HINTS)]
    if viable:
        return viable[0]
    return numeric[0]


def _location_dimension(columns: dict[str, str]) -> str | None:
    for role in ["region", "state", "province", "country", "city", "postal_code"]:
        if role in columns:
            return columns[role]
    return None


def _metric_category(metric: str | None) -> str:
    lowered = (metric or "").lower()
    if any(token in lowered for token in ["charges", "charge", "cost", "claim", "claims", "premium"]):
        return "cost"
    if any(token in lowered for token in ["sales", "revenue", "profit", "amount", "price", "total", "value"]):
        return "performance"
    return "general"


def _default_aggregation(metric: str | None) -> str:
    category = _metric_category(metric)
    if category == "cost":
        return "average"
    if category == "performance":
        return "sum"
    return "sum"


def _aggregation_label(aggregation: str, metric: str | None) -> str:
    metric_label = (metric or "records").replace("_", " ").title()
    if aggregation == "average":
        return f"Average {metric_label}"
    if aggregation == "median":
        return f"Median {metric_label}"
    if aggregation == "count":
        return "Customer Count" if metric else "Record Count"
    return f"Total {metric_label}"


def _aggregate_series(series: pd.Series, aggregation: str) -> pd.Series:
    if aggregation == "average":
        return series.mean()
    if aggregation == "median":
        return series.median()
    if aggregation == "count":
        return series.count()
    return series.sum()


def regional_analytics(df: pd.DataFrame, metric: str | None = None, aggregation: str | None = None) -> dict[str, Any]:
    geo = detect_geographic_columns(df)
    if not geo["available"]:
        return {"available": False, "geo_detection": geo, "regional_kpis": [], "regional_insights": []}
    columns = geo["columns"]
    dimension = _location_dimension(columns)
    if not dimension:
        return {"available": True, "geo_detection": geo, "regional_kpis": [], "regional_insights": []}
    available_metrics = detect_column_types(df)["numeric_columns"]
    selected_metric = metric if metric in available_metrics else _primary_metric(df)
    selected_aggregation = (aggregation or _default_aggregation(selected_metric)).lower()
    if selected_aggregation not in {"average", "sum", "count", "median"}:
        selected_aggregation = _default_aggregation(selected_metric)
    category = _metric_category(selected_metric)
    metric_label = (selected_metric or "records").replace("_", " ").title()

    work = df[[dimension] + ([selected_metric] if selected_metric else [])].copy()
    work["_location"] = work[dimension].map(normalize_location)
    if selected_metric:
        work["_metric"] = pd.to_numeric(work[selected_metric], errors="coerce")
        grouped = work.groupby("_location")["_metric"].apply(lambda s: _aggregate_series(s, selected_aggregation)).sort_values(ascending=False)
    else:
        grouped = work["_location"].value_counts()
        selected_aggregation = "count"

    if grouped.empty:
        return {"available": True, "geo_detection": geo, "regional_kpis": [], "regional_insights": []}
    top = grouped.index[0]
    bottom = grouped.index[-1]
    high_risk = top if category == "cost" else bottom
    kpi_labels = {
        "cost": ("Highest Cost Region", "Lowest Cost Region", "Highest Risk Region"),
        "performance": ("Top Performing Region", "Lowest Performing Region", "Highest Opportunity Region"),
        "general": ("Top Region", "Lowest Region", "Highest Risk Region"),
    }
    top_label, low_label, risk_label = kpi_labels[category]
    title_label = _aggregation_label(selected_aggregation, selected_metric)
    regional_rows = [
        {"region": str(index), "value": to_json_safe(round(float(value), 4))}
        for index, value in grouped.items()
    ]
    if category == "cost":
        top_insight = (
            f"For insurance {metric_label.lower()}, {top} has the highest {selected_aggregation} {metric_label.lower()}. "
            "This may indicate higher cost exposure, claim risk, or a different customer mix. "
            "Compare smoking rate, BMI, claim mix, and policy count against other regions."
        )
        low_insight = (
            f"{bottom} has the lowest {selected_aggregation} {metric_label.lower()}. "
            "Review whether this reflects healthier customer mix, lower claim exposure, pricing differences, or smaller policy volume."
        )
    elif category == "performance":
        top_insight = (
            f"{top} is the strongest region for {title_label.lower()}. "
            "Use it as a benchmark for pricing, retention, and channel strategy."
        )
        low_insight = (
            f"{bottom} is currently weakest for {title_label.lower()}. "
            "Compare product mix, conversion, and customer concentration versus top regions."
        )
    else:
        top_insight = f"{top} has the highest {title_label.lower()}."
        low_insight = f"{bottom} has the lowest {title_label.lower()}."
    return {
        "available": True,
        "geo_detection": geo,
        "metric": selected_metric or "record_count",
        "metric_label": metric_label,
        "available_metrics": available_metrics,
        "aggregation": selected_aggregation,
        "aggregation_options": ["Average", "Sum", "Count", "Median"],
        "regional_title": f"{title_label} by {dimension.replace('_', ' ').title()}",
        "dimension": dimension,
        "regional_kpis": [
            {"label": top_label, "region": str(top), "value": to_json_safe(round(float(grouped.iloc[0]), 4))},
            {"label": low_label, "region": str(bottom), "value": to_json_safe(round(float(grouped.iloc[-1]), 4))},
            {"label": risk_label, "region": str(high_risk), "value": to_json_safe(round(float(grouped.loc[high_risk]), 4))},
        ],
        "regional_rows": regional_rows,
        "regional_insights": [
            {
                "title": top_label,
                "insight": top_insight,
                "recommendation": f"Benchmark {top} against peer regions using the same {title_label.lower()} definition.",
                "evidence": {
                    "top_region": str(top),
                    "top_value": to_json_safe(round(float(grouped.iloc[0]), 4)),
                    "aggregation": selected_aggregation,
                    "metric": selected_metric or "record_count",
                },
            },
            {
                "title": low_label,
                "insight": low_insight,
                "recommendation": f"Investigate structural drivers in {bottom} and compare against {top}.",
                "evidence": {
                    "low_region": str(bottom),
                    "low_value": to_json_safe(round(float(grouped.iloc[-1]), 4)),
                    "aggregation": selected_aggregation,
                    "metric": selected_metric or "record_count",
                },
            },
        ],
    }


def generate_geo_chart_specs(
    df: pd.DataFrame,
    theme_name: str | None = None,
    metric: str | None = None,
    aggregation: str | None = None,
) -> list[dict[str, Any]]:
    theme = theme_manager.get_theme(theme_name)
    geo = detect_geographic_columns(df)
    if not geo["available"]:
        return []
    columns = geo["columns"]
    available_metrics = detect_column_types(df)["numeric_columns"]
    metric = metric if metric in available_metrics else _primary_metric(df)
    aggregation = (aggregation or _default_aggregation(metric)).lower()
    if aggregation not in {"average", "sum", "count", "median"}:
        aggregation = _default_aggregation(metric)
    charts: list[dict[str, Any]] = []

    if columns.get("latitude") and columns.get("longitude"):
        lat = columns["latitude"]
        lon = columns["longitude"]
        size = pd.to_numeric(df[metric], errors="coerce").fillna(1).abs().tolist() if metric else [8] * len(df)
        charts.append(
            {
                "chart_id": "geo_bubble_map",
                "title": f"{_aggregation_label(aggregation, metric)} - Geographic Coordinates",
                "chart_type": "bubble_map",
                "section": "geographic",
                "columns": [lat, lon] + ([metric] if metric else []),
                "plotly": {
                    "data": [
                        {
                            "type": "scattergeo",
                            "lat": pd.to_numeric(df[lat], errors="coerce").tolist(),
                            "lon": pd.to_numeric(df[lon], errors="coerce").tolist(),
                            "mode": "markers",
                            "marker": {"size": [max(6, min(38, float(v) ** 0.5)) for v in size], "color": theme.primary, "opacity": 0.72},
                            "name": _aggregation_label(aggregation, metric),
                        }
                    ],
                    "layout": {
                        **theme_manager.plotly_layout(f"Bubble Map by {metric or 'Records'}", theme_name=theme.name),
                        "geo": {"scope": "world", "showland": True, "landcolor": theme.surface_alt, "countrycolor": theme.border},
                    },
                },
                "metadata": {"theme": theme.name, "drilldown_ready": True, "cross_filter_ready": True, "export_ready": True, "precise_map": True},
            }
        )

    dimension = _location_dimension(columns)
    if dimension:
        work = df[[dimension] + ([metric] if metric else [])].copy()
        work["_location"] = work[dimension].map(normalize_location)
        if metric:
            work["_metric"] = pd.to_numeric(work[metric], errors="coerce")
            grouped = work.groupby("_location")["_metric"].apply(lambda s: _aggregate_series(s, aggregation)).sort_values(ascending=False).head(25)
        else:
            grouped = work["_location"].value_counts().head(25)
        charts.append(
            {
                "chart_id": "geo_regional_comparison",
                "title": f"{_aggregation_label(aggregation, metric)} by {dimension.replace('_', ' ').title()}",
                "chart_type": "regional_comparison_map",
                "section": "geographic",
                "columns": [dimension] + ([metric] if metric else []),
                "plotly": {
                    "data": [
                        {
                            "type": "bar",
                            "orientation": "h",
                            "y": [str(index) for index in grouped.index][::-1],
                            "x": [to_json_safe(value) for value in grouped.values][::-1],
                            "marker": {"color": theme.palette[: len(grouped)]},
                            "name": _aggregation_label(aggregation, metric),
                        }
                    ],
                    "layout": theme_manager.plotly_layout(
                        f"{_aggregation_label(aggregation, metric)} by {dimension.replace('_', ' ').title()}",
                        _aggregation_label(aggregation, metric),
                        dimension.replace("_", " ").title(),
                        theme.name,
                    ),
                },
                "metadata": {"theme": theme.name, "drilldown_ready": True, "cross_filter_ready": True, "export_ready": True, "precise_map": bool(columns.get("latitude") and columns.get("longitude"))},
            }
        )
        region_set = {str(value).strip().lower() for value in grouped.index}
        approx_map = {
            "northwest": (-122.5, 47.0),
            "northeast": (-73.5, 42.5),
            "southwest": (-112.0, 34.0),
            "southeast": (-84.0, 33.0),
        }
        if not (columns.get("latitude") and columns.get("longitude")) and region_set.issubset(set(approx_map.keys())):
            ordered = [name for name in grouped.index if str(name).strip().lower() in approx_map]
            charts.append(
                {
                    "chart_id": "geo_approximate_region_grid",
                    "title": f"Approximate Regional Grid ({_aggregation_label(aggregation, metric)})",
                    "chart_type": "approximate_region_map",
                    "section": "geographic",
                    "columns": [dimension] + ([metric] if metric else []),
                    "plotly": {
                        "data": [
                            {
                               "type": "scattergeo",
                               "lat": [approx_map[str(region).strip().lower()][1] for region in ordered],
                               "lon": [approx_map[str(region).strip().lower()][0] for region in ordered],
                               "mode": "markers+text",
                               "text": [str(region) for region in ordered],
                               "textposition": "top center",
                               "marker": {
                                   "size": [max(12, min(42, float(grouped.loc[region]) ** 0.5)) for region in ordered],
                                   "color": theme.primary,
                                   "opacity": 0.75,
                               },
                               "name": "Approximate map",
                            }
                        ],
                        "layout": {
                            **theme_manager.plotly_layout("Approximate Region Map", theme_name=theme.name),
                            "geo": {"scope": "usa", "showland": True, "landcolor": theme.surface_alt, "countrycolor": theme.border},
                        },
                    },
                    "metadata": {
                        "theme": theme.name,
                        "drilldown_ready": False,
                        "cross_filter_ready": True,
                        "export_ready": True,
                        "precise_map": False,
                        "approximate_map": True,
                        "note": "Approximate placement based on region labels, not precise coordinates.",
                    },
                }
            )
        if "country" in columns:
            charts.append(
                {
                    "chart_id": "geo_filled_map",
                    "title": f"Filled Map: {metric or 'Records'} by Country",
                    "chart_type": "choropleth",
                    "section": "geographic",
                    "columns": [columns["country"]] + ([metric] if metric else []),
                    "plotly": {
                        "data": [
                            {
                                "type": "choropleth",
                                "locations": [str(index) for index in grouped.index],
                                "locationmode": "country names",
                                "z": [to_json_safe(value) for value in grouped.values],
                                "colorscale": [[0, theme.surface_alt], [1, theme.primary]],
                                "colorbar": {"title": _aggregation_label(aggregation, metric)},
                            }
                        ],
                        "layout": {
                            **theme_manager.plotly_layout(f"Filled Map: {metric or 'Records'}", theme_name=theme.name),
                            "geo": {"scope": "world", "showland": True, "landcolor": theme.surface_alt},
                        },
                    },
                    "metadata": {"theme": theme.name, "drilldown_ready": True, "cross_filter_ready": True, "export_ready": True, "precise_map": False},
                }
            )
    return charts
