from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field

from backend.api.auth_dependencies import get_current_user_dependency
from backend.api.error_handlers import map_service_exception, raise_api_error
from backend.models.user_models import User
from backend.performance.pagination import paginate
from backend.performance.streaming import chunk_file, stream_bytes
from backend.services import storage_service
from backend.services.storage_service import StorageError

router = APIRouter(prefix="/api/v1/storage", tags=["Storage"])


class StorageUploadForm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_type: str = "temporary_upload"
    organization_id: str = ""
    workspace_id: str = ""
    object_id: str | None = None
    allow_duplicate: bool = True


class StorageRenameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_name: str = Field(..., min_length=1)


class StorageMoveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str | None = None
    organization_id: str | None = None


class StorageRollbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_number: int = Field(..., ge=1)


def _handle(exc: Exception):
    if isinstance(exc, StorageError):
        raise_api_error(exc.status_code, exc.message)
    raise map_service_exception(exc) from exc


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file",
    description="Stores bytes via the storage abstraction. Each upload creates a version.",
)
async def upload_file(
    file: UploadFile = File(...),
    artifact_type: str = Query(default="temporary_upload"),
    organization_id: str = Query(default=""),
    workspace_id: str = Query(default=""),
    object_id: str | None = Query(default=None),
    allow_duplicate: bool = Query(default=True),
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    try:
        content = await file.read()
        obj = storage_service.upload(
            content,
            file.filename or "upload.bin",
            artifact_type=artifact_type,
            owner_id=current_user.user_id,
            organization_id=organization_id,
            workspace_id=workspace_id,
            content_type=file.content_type or "application/octet-stream",
            object_id=object_id,
            created_by=current_user.user_id,
            allow_duplicate=allow_duplicate,
        )
        return {"success": True, "object": obj.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.get(
    "/files",
    summary="List stored files",
    description="Lists storage objects with optional filters.",
)
def list_files(
    artifact_type: str | None = Query(default=None),
    organization_id: str | None = Query(default=None),
    workspace_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    mine: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    objects = storage_service.list_files(
        artifact_type=artifact_type,
        owner_id=current_user.user_id if mine else None,
        organization_id=organization_id,
        workspace_id=workspace_id,
        status=status_filter,
    )
    page_result = paginate(objects, page=page, page_size=page_size)
    return {
        "success": True,
        "count": page_result.total,
        "page": page_result.page,
        "page_size": page_result.page_size,
        "objects": [o.model_dump() for o in page_result.items],
    }


@router.get(
    "/statistics",
    summary="Storage statistics",
    description="Aggregate counts, bytes, and quota usage.",
)
def statistics(current_user: User = Depends(get_current_user_dependency)) -> dict[str, Any]:
    _ = current_user
    return {"success": True, "statistics": storage_service.storage_statistics().model_dump()}


@router.get(
    "/{object_id}",
    summary="Get storage object metadata",
    responses={404: {"description": "Not found"}},
)
def get_object(
    object_id: str,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    obj = storage_service.get_metadata(object_id)
    if obj is None:
        raise_api_error(404, f"Storage object not found: {object_id}")
    return {"success": True, "object": obj.model_dump()}


@router.get(
    "/{object_id}/download",
    summary="Download storage object bytes",
    responses={404: {"description": "Not found"}},
)
def download_object(
    object_id: str,
    version: int | None = Query(default=None),
    stream: bool = Query(default=False),
    current_user: User = Depends(get_current_user_dependency),
):
    _ = current_user
    try:
        content, obj = storage_service.download(object_id, version_number=version)
        if stream:
            return stream_bytes(
                chunk_file(content),
                media_type=obj.content_type or "application/octet-stream",
                filename=obj.name,
            )
        import base64

        return {
            "success": True,
            "object_id": object_id,
            "name": obj.name,
            "version": version or obj.current_version,
            "size_bytes": len(content),
            "content_base64": base64.b64encode(content).decode("ascii"),
        }
    except Exception as exc:
        _handle(exc)


@router.delete(
    "/{object_id}",
    summary="Delete storage object (soft delete)",
)
def delete_object(
    object_id: str,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    try:
        obj = storage_service.delete(object_id)
        return {"success": True, "object": obj.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.post(
    "/{object_id}/archive",
    summary="Archive storage object",
)
def archive_object(
    object_id: str,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    try:
        obj = storage_service.archive(object_id)
        return {"success": True, "object": obj.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.post(
    "/{object_id}/restore",
    summary="Restore archived/deleted storage object",
)
def restore_object(
    object_id: str,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    try:
        obj = storage_service.restore(object_id)
        return {"success": True, "object": obj.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.post(
    "/{object_id}/rollback",
    summary="Rollback to a previous version",
)
def rollback_object(
    object_id: str,
    request: StorageRollbackRequest,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    try:
        obj = storage_service.rollback_version(object_id, request.version_number)
        return {"success": True, "object": obj.model_dump()}
    except Exception as exc:
        _handle(exc)


@router.post(
    "/{object_id}/verify",
    summary="Verify checksum of stored object",
)
def verify_object(
    object_id: str,
    version: int | None = Query(default=None),
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    try:
        ok = storage_service.verify_checksum(object_id, version_number=version)
        return {"success": True, "object_id": object_id, "valid": ok}
    except Exception as exc:
        _handle(exc)
