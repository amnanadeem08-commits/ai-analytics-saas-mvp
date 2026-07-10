from __future__ import annotations

import pytest

from backend.security.security_config import reset_security_config
from backend.services import auth_service
from backend.services.auth_service import AuthError, reset_auth_store

STRONG = "Str0ngPass"


def setup_function():
    reset_security_config()
    reset_auth_store()


def _register(email: str = "user@example.com", password: str = STRONG):
    return auth_service.register_user(email, password, full_name="Test User")


def test_register_user_creates_pending_account():
    result = _register()
    user = result["user"]
    assert user["email"] == "user@example.com"
    assert user["status"] == "pending"
    assert "hashed_password" not in user
    assert result["verification_token"]


def test_register_duplicate_email_rejected():
    _register()
    with pytest.raises(AuthError) as exc:
        _register()
    assert exc.value.status_code == 409


def test_register_weak_password_rejected():
    with pytest.raises(AuthError) as exc:
        auth_service.register_user("weak@example.com", "weak")
    assert exc.value.status_code == 422


def test_authenticate_and_get_current_user():
    _register()
    result = auth_service.authenticate_user("user@example.com", STRONG)
    assert result["access_token"]
    assert result["refresh_token"]
    user = auth_service.get_current_user(result["access_token"])
    assert user.email == "user@example.com"


def test_authenticate_bad_password():
    _register()
    with pytest.raises(AuthError) as exc:
        auth_service.authenticate_user("user@example.com", "WrongPass1")
    assert exc.value.status_code == 401


def test_refresh_rotates_token():
    _register()
    login = auth_service.authenticate_user("user@example.com", STRONG)
    refreshed = auth_service.refresh_access_token(login["refresh_token"])
    assert refreshed["access_token"]
    # Old refresh token is revoked after rotation
    with pytest.raises(AuthError):
        auth_service.refresh_access_token(login["refresh_token"])


def test_logout_revokes_session():
    _register()
    login = auth_service.authenticate_user("user@example.com", STRONG)
    auth_service.logout(session_id=login["session_id"])
    with pytest.raises(AuthError):
        auth_service.get_current_user(login["access_token"])


def test_verify_email_flow():
    result = _register()
    verified = auth_service.verify_email(result["verification_token"])
    assert verified["verified"] is True
    user = auth_service.get_user_by_email("user@example.com")
    assert user.email_verified is True
    assert user.status.value == "active"


def test_change_password_revokes_sessions():
    _register()
    login = auth_service.authenticate_user("user@example.com", STRONG)
    auth_service.change_password(
        auth_service.get_user_by_email("user@example.com").user_id,
        STRONG,
        "NewStr0ngPass",
    )
    # Old session is revoked
    with pytest.raises(AuthError):
        auth_service.get_current_user(login["access_token"])
    # New password works
    assert auth_service.authenticate_user("user@example.com", "NewStr0ngPass")["access_token"]


def test_password_reset_flow():
    _register()
    req = auth_service.request_password_reset("user@example.com")
    assert req["reset_token"]
    auth_service.reset_password(req["reset_token"], "ResetStr0ng1")
    assert auth_service.authenticate_user("user@example.com", "ResetStr0ng1")["access_token"]


def test_password_reset_unknown_email_no_enumeration():
    result = auth_service.request_password_reset("nobody@example.com")
    assert result["requested"] is True
    assert result["reset_token"] == ""


def test_concurrent_session_limit_enforced(monkeypatch):
    from backend.security import security_config

    cfg = security_config.get_security_config()
    monkeypatch.setattr(cfg, "max_concurrent_sessions", 2)
    _register()
    s1 = auth_service.authenticate_user("user@example.com", STRONG)
    s2 = auth_service.authenticate_user("user@example.com", STRONG)
    s3 = auth_service.authenticate_user("user@example.com", STRONG)
    active = auth_service.count_active_sessions(
        auth_service.get_user_by_email("user@example.com").user_id
    )
    assert active <= 2
    # Oldest session was revoked
    with pytest.raises(AuthError):
        auth_service.get_current_user(s1["access_token"])
    assert auth_service.get_current_user(s3["access_token"])


def test_audit_events_recorded():
    _register()
    auth_service.authenticate_user("user@example.com", STRONG)
    events = auth_service.list_audit_events()
    types = {e.event_type for e in events}
    assert "register" in types
    assert "login" in types
