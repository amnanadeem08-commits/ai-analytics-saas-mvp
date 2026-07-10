from __future__ import annotations

import pytest

from backend.services import api_key_service
from backend.services.api_key_service import ApiKeyError


ORG = "org_keys"


def setup_function():
    api_key_service.reset_api_keys()


def test_create_list_revoke():
    key, raw = api_key_service.create_key(name="Test", organization_id=ORG, created_by="usr_1")
    assert raw.startswith("databot_sk_")
    listed = api_key_service.list_keys(organization_id=ORG)
    assert len(listed) == 1
    revoked = api_key_service.revoke_key(key.key_id)
    assert revoked.status.value == "revoked"


def test_authenticate_and_rate_limit():
    _, raw = api_key_service.create_key(
        name="Auth",
        organization_id=ORG,
        created_by="usr_1",
        rate_limit_per_minute=2,
    )
    api_key_service.authenticate_key(raw)
    api_key_service.authenticate_key(raw)
    with pytest.raises(ApiKeyError) as exc:
        api_key_service.authenticate_key(raw)
    assert exc.value.status_code == 429


def test_rotate_key():
    key, raw = api_key_service.create_key(name="Rotate", organization_id=ORG, created_by="usr_1")
    api_key_service.authenticate_key(raw)
    new_key, new_raw = api_key_service.rotate_key(key.key_id, rotated_by="usr_1")
    assert new_key.key_id != key.key_id
    with pytest.raises(ApiKeyError):
        api_key_service.authenticate_key(raw)
    api_key_service.authenticate_key(new_raw)


def test_scopes():
    key, raw = api_key_service.create_key(
        name="Scoped",
        organization_id=ORG,
        created_by="usr_1",
        scopes=["read", "ai_analyst"],
    )
    authed = api_key_service.authenticate_key(raw)
    assert api_key_service.has_scope(authed, "read")
    assert api_key_service.has_scope(authed, "ai_analyst")
    assert not api_key_service.has_scope(authed, "admin")
