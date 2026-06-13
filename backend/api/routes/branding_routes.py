from pathlib import Path

from fastapi import APIRouter, UploadFile
from fastapi.responses import FileResponse

from backend.api.deps import map_app_error
from backend.core.branding_manager import branding_manager
from backend.models.branding_models import BrandingResponse, BrandingUpdate

router = APIRouter(prefix="/branding", tags=["Branding"])


@router.get("", response_model=BrandingResponse)
def get_branding():
    return branding_manager.get().to_dict()


@router.put("", response_model=BrandingResponse)
def update_branding(payload: BrandingUpdate):
    try:
        return branding_manager.update(payload.model_dump(exclude_unset=True)).to_dict()
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.post("/logo", response_model=BrandingResponse)
async def upload_logo(file: UploadFile):
    try:
        return branding_manager.save_logo(file.filename or "logo.png", await file.read()).to_dict()
    except Exception as exc:
        raise map_app_error(exc) from exc


@router.get("/logo/current")
def current_logo():
    branding = branding_manager.get()
    if not branding.logo_path:
        raise map_app_error(FileNotFoundError("No logo has been uploaded."))
    path = Path(branding.logo_path)
    if not path.exists():
        raise map_app_error(FileNotFoundError("Logo file does not exist."))
    return FileResponse(path)
