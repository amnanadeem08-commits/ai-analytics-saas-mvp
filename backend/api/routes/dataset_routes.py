from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from backend.api.deps import map_app_error
from backend.core.config import settings
from backend.models.dataset_models import (
    CleaningOptions,
    DatasetMetadata,
    DatasetCleaningResponse,
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
from backend.services.data_cleaning_service import clean_dataset

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


@router.post("/{dataset_id}/clean", response_model=DatasetCleaningResponse)
def clean_dataset_preview(dataset_id: str, options: CleaningOptions):
    try:
        return clean_dataset(dataset_id, options, settings.DATASETS_DIR)
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.get("/{dataset_id}/clean/download")
def download_cleaned_dataset(dataset_id: str, filename: str):
    try:
        safe_name = Path(filename).name
        target = settings.DATASETS_DIR / dataset_id / "cleaned" / safe_name
        if not target.exists():
            raise FileNotFoundError(f"Cleaned file '{safe_name}' was not found for dataset '{dataset_id}'.")
        media_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if target.suffix.lower() == ".xlsx"
            else "text/csv"
        )
        return FileResponse(path=target, media_type=media_type, filename=safe_name)
    except Exception as exc:
        raise map_app_error(exc) from exc
