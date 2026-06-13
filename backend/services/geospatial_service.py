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
    preferred = ["revenue", "sales", "amount", "profit", "churn", "cases", "score"]
    for hint in preferred:
        for column in numeric:
            if hint in column.lower():
                return column
    return numeric[0] if numeric else None


def _location_dimension(columns: dict[str, str]) -> str | None:
    for role in ["region", "state", "province", "country", "city", "postal_code"]:
        if role in columns:
            return columns[role]
    return None


def regional_analytics(df: pd.DataFrame) -> dict[str, Any]:
    geo = detect_geographic_columns(df)
    if not geo["available"]:
        return {"available": False, "geo_detection": geo, "regional_kpis": [], "regional_insights": []}
    columns = geo["columns"]
    metric = _primary_metric(df)
    dimension = _location_dimension(columns)
    if not dimension:
        return {"available": True, "geo_detection": geo, "regional_kpis": [], "regional_insights": []}

    work = df[[dimension] + ([metric] if metric else [])].copy()
    work["_location"] = work[dimension].map(normalize_location)
    if metric:
        work["_metric"] = pd.to_numeric(work[metric], errors="coerce").fillna(0)
        grouped = work.groupby("_location")["_metric"].sum().sort_values(ascending=False)
    else:
        grouped = work["_location"].value_counts()

    if grouped.empty:
        return {"available": True, "geo_detection": geo, "regional_kpis": [], "regional_insights": []}
    top = grouped.index[0]
    bottom = grouped.index[-1]
    values = [float(value) for value in grouped.values]
    avg = sum(values) / len(values)
    high_risk = grouped[grouped < avg].index[-1] if len(grouped) > 1 else bottom
    regional_rows = [
        {"region": str(index), "value": to_json_safe(round(float(value), 4))}
        for index, value in grouped.items()
    ]
    return {
        "available": True,
        "geo_detection": geo,
        "metric": metric or "record_count",
        "dimension": dimension,
        "regional_kpis": [
            {"label": "Top Performing Region", "region": str(top), "value": to_json_safe(round(float(grouped.iloc[0]), 4))},
            {"label": "Lowest Performing Region", "region": str(bottom), "value": to_json_safe(round(float(grouped.iloc[-1]), 4))},
            {"label": "Highest Risk Region", "region": str(high_risk), "value": to_json_safe(round(float(grouped.loc[high_risk]), 4))},
        ],
        "regional_rows": regional_rows,
        "regional_insights": [
            {
                "title": "Top Performing Region",
                "insight": f"{top} leads regional performance on {metric or 'record count'} with {to_json_safe(round(float(grouped.iloc[0]), 4))}.",
                "recommendation": f"Use {top} as a benchmark for regional performance practices.",
                "evidence": regional_rows[:5],
            },
            {
                "title": "Lowest Performing Region",
                "insight": f"{bottom} is the lowest region on {metric or 'record count'} with {to_json_safe(round(float(grouped.iloc[-1]), 4))}.",
                "recommendation": f"Investigate constraints in {bottom} and compare against {top}.",
                "evidence": regional_rows[-5:],
            },
        ],
    }


def generate_geo_chart_specs(df: pd.DataFrame, theme_name: str | None = None) -> list[dict[str, Any]]:
    theme = theme_manager.get_theme(theme_name)
    geo = detect_geographic_columns(df)
    if not geo["available"]:
        return []
    columns = geo["columns"]
    metric = _primary_metric(df)
    charts: list[dict[str, Any]] = []

    if columns.get("latitude") and columns.get("longitude"):
        lat = columns["latitude"]
        lon = columns["longitude"]
        size = pd.to_numeric(df[metric], errors="coerce").fillna(1).abs().tolist() if metric else [8] * len(df)
        charts.append(
            {
                "chart_id": "geo_bubble_map",
                "title": f"Bubble Map by {metric or 'Records'}",
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
                            "name": metric or "Records",
                        }
                    ],
                    "layout": {
                        **theme_manager.plotly_layout(f"Bubble Map by {metric or 'Records'}", theme_name=theme.name),
                        "geo": {"scope": "world", "showland": True, "landcolor": theme.surface_alt, "countrycolor": theme.border},
                    },
                },
                "metadata": {"theme": theme.name, "drilldown_ready": True, "cross_filter_ready": True, "export_ready": True},
            }
        )

    dimension = _location_dimension(columns)
    if dimension:
        work = df[[dimension] + ([metric] if metric else [])].copy()
        work["_location"] = work[dimension].map(normalize_location)
        if metric:
            work["_metric"] = pd.to_numeric(work[metric], errors="coerce").fillna(0)
            grouped = work.groupby("_location")["_metric"].sum().sort_values(ascending=False).head(25)
        else:
            grouped = work["_location"].value_counts().head(25)
        charts.append(
            {
                "chart_id": "geo_regional_comparison",
                "title": f"{metric or 'Records'} by {dimension}",
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
                            "name": metric or "Records",
                        }
                    ],
                    "layout": theme_manager.plotly_layout(f"{metric or 'Records'} by {dimension}", metric or "Records", dimension, theme.name),
                },
                "metadata": {"theme": theme.name, "drilldown_ready": True, "cross_filter_ready": True, "export_ready": True},
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
                                "colorbar": {"title": metric or "Records"},
                            }
                        ],
                        "layout": {
                            **theme_manager.plotly_layout(f"Filled Map: {metric or 'Records'}", theme_name=theme.name),
                            "geo": {"scope": "world", "showland": True, "landcolor": theme.surface_alt},
                        },
                    },
                    "metadata": {"theme": theme.name, "drilldown_ready": True, "cross_filter_ready": True, "export_ready": True},
                }
            )
    return charts
