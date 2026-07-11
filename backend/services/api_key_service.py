from __future__ import annotations

"""API key service (Sprint 8.6) — commercial ApiKeyStore backed."""

import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models.api_key_models import API_KEY_PREFIX, ApiKey, ApiKeyScope, ApiKeyStatus
from backend.security.password_service import hash_token

API_KEY_RAW_LENGTH = 32

_RATE_LIMIT_STORE: dict[str, list[float]] = {}


class ApiKeyError(Exception):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _keys():
    from backend.repositories.commercial_registry import get_commercial_stores

    return get_commercial_stores().api_keys


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _uid() -> str:
    return f"key_{uuid.uuid4().hex[:12]}"


def reset_api_keys() -> None:
    global _RATE_LIMIT_STORE
    _keys().clear()
    _RATE_LIMIT_STORE = {}


def _generate_raw_key() -> str:
    return API_KEY_PREFIX + secrets.token_urlsafe(API_KEY_RAW_LENGTH)


def create_key(
    *,
    name: str,
    organization_id: str,
    created_by: str,
    workspace_id: str = "",
    scopes: list[str] | None = None,
    rate_limit_per_minute: int = 60,
    expires_in_days: int | None = None,
) -> tuple[ApiKey, str]:
    raw = _generate_raw_key()
    key_hash = hash_token(raw)
    prefix = raw[: len(API_KEY_PREFIX) + 8]
    expires_at = ""
    if expires_in_days:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_in_days)).isoformat().replace("+00:00", "Z")

    normalized_scopes = [str(s) for s in (scopes or [ApiKeyScope.read.value])]
    key = ApiKey(
        key_id=_uid(),
        name=name.strip(),
        key_prefix=prefix,
        key_hash=key_hash,
        organization_id=organization_id,
        workspace_id=workspace_id,
        created_by=created_by,
        scopes=normalized_scopes,
        rate_limit_per_minute=max(1, int(rate_limit_per_minute)),
        expires_at=expires_at,
        created_at=_now_iso(),
    )
    _keys().save(key)
    return key.model_copy(deep=True), raw


def list_keys(
    *,
    organization_id: str | None = None,
    workspace_id: str | None = None,
    created_by: str | None = None,
) -> list[ApiKey]:
    items = _keys().list(organization_id=organization_id)
    if workspace_id:
        items = [k for k in items if k.workspace_id == workspace_id]
    if created_by:
        items = [k for k in items if k.created_by == created_by]
    return items


def get_key(key_id: str) -> ApiKey | None:
    return _keys().get(key_id)


def revoke_key(key_id: str) -> ApiKey:
    key = _keys().get(key_id)
    if key is None:
        raise ApiKeyError(f"API key not found: {key_id}", status_code=404)
    key.status = ApiKeyStatus.revoked
    key.revoked_at = _now_iso()
    _keys().save(key)
    return key.model_copy(deep=True)


def rotate_key(key_id: str, *, rotated_by: str) -> tuple[ApiKey, str]:
    old = _keys().get(key_id)
    if old is None:
        raise ApiKeyError(f"API key not found: {key_id}", status_code=404)
    revoke_key(key_id)
    new_key, raw = create_key(
        name=old.name,
        organization_id=old.organization_id,
        created_by=rotated_by,
        workspace_id=old.workspace_id,
        scopes=list(old.scopes),
        rate_limit_per_minute=old.rate_limit_per_minute,
    )
    new = _keys().get(new_key.key_id)
    assert new is not None
    new.rotated_from = key_id
    _keys().save(new)
    return new.model_copy(deep=True), raw


def authenticate_key(raw_key: str) -> ApiKey:
    if not raw_key or not raw_key.startswith(API_KEY_PREFIX):
        raise ApiKeyError("Invalid API key", status_code=401)
    key_hash = hash_token(raw_key)
    key = _keys().get_by_hash(key_hash)
    if key is None:
        raise ApiKeyError("Invalid API key", status_code=401)
    if key.status != ApiKeyStatus.active:
        raise ApiKeyError("API key revoked or inactive", status_code=401)
    if key.expires_at and key.expires_at < _now_iso():
        key.status = ApiKeyStatus.expired
        _keys().save(key)
        raise ApiKeyError("API key expired", status_code=401)
    _enforce_rate_limit(key)
    key.last_used_at = _now_iso()
    _keys().save(key)
    return key.model_copy(deep=True)


def _enforce_rate_limit(key: ApiKey) -> None:
    now = time.time()
    bucket_key = key.key_id
    window = _RATE_LIMIT_STORE.get(bucket_key, [])
    window = [t for t in window if now - t < 60]
    if len(window) >= key.rate_limit_per_minute:
        raise ApiKeyError("Rate limit exceeded", status_code=429)
    window.append(now)
    _RATE_LIMIT_STORE[bucket_key] = window


def has_scope(key: ApiKey, scope: str) -> bool:
    if ApiKeyScope.admin.value in key.scopes:
        return True
    return scope in key.scopes
