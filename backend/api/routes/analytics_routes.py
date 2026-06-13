from fastapi import APIRouter

from backend.api.deps import map_app_error
from backend.models.analytics_models import DashboardFilterRequest, DashboardResponse, DataSummaryResponse
from backend.services.analytics_service import (
    get_dashboard_stats,
    get_data_summary,
    get_filtered_dashboard_stats,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/{dataset_id}/summary", response_model=DataSummaryResponse)
def dataset_summary(dataset_id: str):
    try:
        return get_data_summary(dataset_id)
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.get("/{dataset_id}/dashboard", response_model=DashboardResponse)
def dataset_dashboard(dataset_id: str):
    try:
        return get_dashboard_stats(dataset_id)
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.post("/{dataset_id}/dashboard/filter", response_model=DashboardResponse)
def filtered_dataset_dashboard(dataset_id: str, payload: DashboardFilterRequest):
    try:
        return get_filtered_dashboard_stats(dataset_id, payload.filters)
    except Exception as exc:
        raise map_app_error(exc) from exc
