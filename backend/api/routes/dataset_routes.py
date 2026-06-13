from fastapi import APIRouter, Query

from backend.api.deps import map_app_error
from backend.models.dataset_models import (
    DatasetMetadata,
    DatasetOverviewResponse,
    DatasetPreviewResponse,
    DatasetStatusResponse,
)
from backend.services.dataset_service import (
    get_all_datasets,
    get_dataset_metadata,
    get_dataset_overview,
    get_dataset_preview,
    get_dataset_status,
)

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.get("", response_model=list[DatasetMetadata])
def list_datasets():
    return get_all_datasets()


@router.get("/{dataset_id}", response_model=DatasetMetadata)
def retrieve_dataset(dataset_id: str):
    try:
        return get_dataset_metadata(dataset_id)
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.get("/{dataset_id}/status", response_model=DatasetStatusResponse)
def dataset_status(dataset_id: str):
    try:
        return get_dataset_status(dataset_id)
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.get("/{dataset_id}/overview", response_model=DatasetOverviewResponse)
def dataset_overview(dataset_id: str):
    try:
        return get_dataset_overview(dataset_id)
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.get("/{dataset_id}/preview", response_model=DatasetPreviewResponse)
def preview_dataset(dataset_id: str, rows: int = Query(default=10, ge=1, le=100)):
    try:
        return get_dataset_preview(dataset_id, rows=rows)
    except Exception as exc:
        raise map_app_error(exc) from exc
