from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field

from backend.api.auth_dependencies import get_current_user_dependency
from backend.api.error_handlers import map_service_exception, raise_api_error
from backend.models.user_models import User
from backend.services import api_key_service
from backend.services.api_key_service import ApiKeyError

router = APIRouter(prefix="/api/v1/api-keys", tags=["API Keys"])


class CreateApiKeyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    organization_id: str
    workspace_id: str = ""
    scopes: list[str] = Field(default_factory=lambda: ["read"])
    rate_limit_per_minute: int = Field(default=60, ge=1, le=10000)
    expires_in_days: int | None = None


def _handle(exc: Exception):
    if isinstance(exc, ApiKeyError):
        raise_api_error(exc.status_code, exc.message)
    raise map_service_exception(exc) from exc


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create API key",
    description="Returns the raw key once — store it securely.",
)
def create_key(
    request: CreateApiKeyRequest,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    try:
        key, raw = api_key_service.create_key(
            name=request.name,
            organization_id=request.organization_id,
            created_by=current_user.user_id,
            workspace_id=request.workspace_id,
            scopes=request.scopes,
            rate_limit_per_minute=request.rate_limit_per_minute,
            expires_in_days=request.expires_in_days,
        )
        return {"success": True, "key": key.public_dict(), "secret": raw}
    except Exception as exc:
        _handle(exc)


@router.get("", summary="List API keys")
def list_keys(
    organization_id: str | None = Query(default=None),
    workspace_id: str | None = Query(default=None),
    mine: bool = Query(default=False),
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    keys = api_key_service.list_keys(
        organization_id=organization_id,
        workspace_id=workspace_id,
        created_by=current_user.user_id if mine else None,
    )
    return {"success": True, "count": len(keys), "keys": [k.public_dict() for k in keys]}


@router.get("/{key_id}", summary="Get API key metadata")
def get_key(
    key_id: str,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    key = api_key_service.get_key(key_id)
    if key is None:
        raise_api_error(404, f"API key not found: {key_id}")
    return {"success": True, "key": key.public_dict()}


@router.delete("/{key_id}", summary="Revoke API key")
def revoke_key(
    key_id: str,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    _ = current_user
    try:
        key = api_key_service.revoke_key(key_id)
        return {"success": True, "key": key.public_dict()}
    except Exception as exc:
        _handle(exc)


@router.post("/{key_id}/rotate", summary="Rotate API key")
def rotate_key(
    key_id: str,
    current_user: User = Depends(get_current_user_dependency),
) -> dict[str, Any]:
    try:
        key, raw = api_key_service.rotate_key(key_id, rotated_by=current_user.user_id)
        return {"success": True, "key": key.public_dict(), "secret": raw}
    except Exception as exc:
        _handle(exc)
