from fastapi import APIRouter, File, UploadFile

from backend.api.deps import map_app_error
from backend.models.dataset_models import UploadResponse
from backend.services.upload_service import upload_dataset

router = APIRouter(tags=["Upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload_csv(file: UploadFile = File(...)):
    try:
        metadata = await upload_dataset(file)
        return UploadResponse(
            dataset_id=metadata["dataset_id"],
            filename=metadata["original_filename"],
            message="Dataset uploaded successfully.",
        )
    except Exception as exc:  # Route boundary converts predictable errors to HTTP errors.
        raise map_app_error(exc) from exc
