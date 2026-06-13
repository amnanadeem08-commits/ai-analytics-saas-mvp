from __future__ import annotations

from backend.processing.analytics_engine import build_dashboard_stats, build_summary
from backend.services.dashboard_service import build_dashboard_view
from backend.services.dataset_service import load_dataset_dataframe


def get_data_summary(dataset_id: str) -> dict:
    df = load_dataset_dataframe(dataset_id)
    summary = build_summary(df)
    return {"dataset_id": dataset_id, **summary}


def get_dashboard_stats(dataset_id: str) -> dict:
    return build_dashboard_view(dataset_id)


def get_filtered_dashboard_stats(dataset_id: str, filters: dict) -> dict:
    return build_dashboard_view(dataset_id, filters=filters)
