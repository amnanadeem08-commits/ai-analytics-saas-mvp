from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models.user_models import (
    AuthAuditEvent,
    EmailVerification,
    PasswordResetRequest,
    RefreshToken,
    User,
    UserProfile,
    UserSession,
    UserStatus,
    is_valid_email,
)
from backend.security.jwt_service import (
    JWTError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from backend.security.password_service import (
    generate_token,
    hash_password,
    hash_token,
    validate_password_policy,
    verify_password,
)
from backend.security.security_config import get_security_config


class AuthError(Exception):
    """Raised for authentication/authorization failures with a client-safe message."""

    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ---------------------------------------------------------------------------
# In-memory stores (Sprint 8.0). No DB migration in scope; a persistence
# adapter can replace these later without changing the service API.
# ---------------------------------------------------------------------------
_USERS: dict[str, User] = {}
_EMAIL_INDEX: dict[str, str] = {}  # email -> user_id
_SESSIONS: dict[str, UserSession] = {}
_REFRESH_TOKENS: dict[str, RefreshToken] = {}  # token_id -> record
_PASSWORD_RESETS: dict[str, PasswordResetRequest] = {}
_EMAIL_VERIFICATIONS: dict[str, EmailVerification] = {}
_AUDIT_LOG: list[AuthAuditEvent] = []


def reset_auth_store() -> None:
    """Test helper — clear all in-memory auth state."""
    _USERS.clear()
    _EMAIL_INDEX.clear()
    _SESSIONS.clear()
    _REFRESH_TOKENS.clear()
    _PASSWORD_RESETS.clear()
    _EMAIL_VERIFICATIONS.clear()
    _AUDIT_LOG.clear()
    try:
        from backend.security.brute_force import reset_brute_force_state

        reset_brute_force_state()
    except Exception:
        pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _now_iso() -> str:
    return _iso(_now())


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def list_audit_events(*, limit: int | None = None) -> list[AuthAuditEvent]:
    events = [e.model_copy(deep=True) for e in _AUDIT_LOG]
    if limit is not None:
        return events[-limit:]
    return events


def list_users() -> list[User]:
    return [u.model_copy(deep=True) for u in _USERS.values()]


def _audit(
    event_type: str,
    *,
    user_id: str = "",
    email: str = "",
    success: bool = True,
    ip_address: str = "",
    user_agent: str = "",
    details: dict[str, Any] | None = None,
) -> None:
    _AUDIT_LOG.append(
        AuthAuditEvent(
            event_id=_uid("evt"),
            event_type=event_type,
            user_id=user_id,
            email=email,
            success=success,
            timestamp=_now_iso(),
            ip_address=ip_address,
            user_agent=user_agent,
            details=dict(details or {}),
        )
    )


# ---------------------------------------------------------------------------
# Registration & lookup
# ---------------------------------------------------------------------------


def get_user_by_id(user_id: str) -> User | None:
    user = _USERS.get(user_id)
    return user.model_copy(deep=True) if user else None


def get_user_by_email(email: str) -> User | None:
    user_id = _EMAIL_INDEX.get(str(email or "").strip().lower())
    return get_user_by_id(user_id) if user_id else None


def register_user(
    email: str,
    password: str,
    *,
    full_name: str = "",
    profile: dict[str, Any] | None = None,
    auto_verify: bool = False,
) -> dict[str, Any]:
    """Register a new user. Returns the created user plus an email-verification token."""
    normalized = str(email or "").strip().lower()
    if not is_valid_email(normalized):
        raise AuthError("Invalid email address", status_code=422)
    if normalized in _EMAIL_INDEX:
        raise AuthError("An account with this email already exists", status_code=409)

    policy = validate_password_policy(password)
    if not policy.valid:
        raise AuthError("; ".join(policy.issues), status_code=422)

    now = _now_iso()
    profile_data = dict(profile or {})
    if full_name and "full_name" not in profile_data:
        profile_data["full_name"] = full_name
    user = User(
        user_id=_uid("usr"),
        email=normalized,
        email_verified=auto_verify,
        hashed_password=hash_password(password),
        status=UserStatus.active if auto_verify else UserStatus.pending,
        profile=UserProfile(**profile_data),
        created_at=now,
        updated_at=now,
    )
    _USERS[user.user_id] = user
    _EMAIL_INDEX[normalized] = user.user_id

    verification_token = ""
    if not auto_verify:
        verification_token = _create_email_verification(user)
    _audit("register", user_id=user.user_id, email=normalized, success=True)
    return {
        "user": user.public_dict(),
        "verification_token": verification_token,
    }


def _create_email_verification(user: User) -> str:
    config = get_security_config()
    raw = generate_token()
    record = EmailVerification(
        verification_id=_uid("emv"),
        user_id=user.user_id,
        email=user.email,
        token_hash=hash_token(raw),
        created_at=_now_iso(),
        expires_at=_iso(_now() + timedelta(seconds=config.email_verification_ttl_seconds)),
    )
    _EMAIL_VERIFICATIONS[record.verification_id] = record
    return raw


def verify_email(token: str) -> dict[str, Any]:
    token_hash = hash_token(token)
    for record in _EMAIL_VERIFICATIONS.values():
        if record.token_hash == token_hash and not record.verified:
            if _is_expired(record.expires_at):
                raise AuthError("Verification token has expired", status_code=400)
            record.verified = True
            user = _USERS.get(record.user_id)
            if user:
                user.email_verified = True
                if user.status == UserStatus.pending:
                    user.status = UserStatus.active
                user.updated_at = _now_iso()
            _audit("verify_email", user_id=record.user_id, email=record.email, success=True)
            return {"verified": True, "user_id": record.user_id}
    _audit("verify_email", success=False, details={"reason": "invalid_token"})
    raise AuthError("Invalid verification token", status_code=400)


# ---------------------------------------------------------------------------
# Authentication & tokens
# ---------------------------------------------------------------------------


def _is_expired(iso_ts: str) -> bool:
    if not iso_ts:
        return True
    try:
        parsed = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return True
    return parsed < _now()


def _create_session(
    user: User,
    *,
    ip_address: str = "",
    user_agent: str = "",
) -> UserSession:
    config = get_security_config()
    _enforce_concurrent_session_limit(user.user_id)
    session = UserSession(
        session_id=_uid("ses"),
        user_id=user.user_id,
        created_at=_now_iso(),
        last_seen_at=_now_iso(),
        expires_at=_iso(_now() + timedelta(seconds=config.refresh_token_ttl_seconds)),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    _SESSIONS[session.session_id] = session
    return session


def _enforce_concurrent_session_limit(user_id: str) -> None:
    config = get_security_config()
    active = [
        s
        for s in _SESSIONS.values()
        if s.user_id == user_id and not s.revoked and not _is_expired(s.expires_at)
    ]
    if len(active) < config.max_concurrent_sessions:
        return
    active.sort(key=lambda s: s.created_at)
    # Revoke oldest sessions until under the limit.
    for stale in active[: len(active) - config.max_concurrent_sessions + 1]:
        stale.revoked = True
        _revoke_session_tokens(stale.session_id)


def _issue_tokens(user: User, session: UserSession) -> dict[str, Any]:
    config = get_security_config()
    access_token = create_access_token(user.user_id, extra_claims={"email": user.email, "sid": session.session_id})
    raw_refresh = create_refresh_token(user.user_id, session_id=session.session_id)
    record = RefreshToken(
        token_id=_uid("rft"),
        user_id=user.user_id,
        session_id=session.session_id,
        token_hash=hash_token(raw_refresh),
        issued_at=_now_iso(),
        expires_at=_iso(_now() + timedelta(seconds=config.refresh_token_ttl_seconds)),
    )
    _REFRESH_TOKENS[record.token_id] = record
    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "expires_in": config.access_token_ttl_seconds,
        "session_id": session.session_id,
    }


def authenticate_user(
    email: str,
    password: str,
    *,
    ip_address: str = "",
    user_agent: str = "",
) -> dict[str, Any]:
    from backend.security.brute_force import is_locked, record_failure, record_success

    normalized = str(email or "").strip().lower()
    lock_key = f"{normalized}:{ip_address or 'unknown'}"
    if is_locked(lock_key):
        _audit("login", email=normalized, success=False, ip_address=ip_address, details={"reason": "lockout"})
        raise AuthError("Too many failed login attempts. Try again later.", status_code=429)

    user = _USERS.get(_EMAIL_INDEX.get(normalized, ""))
    if user is None or not verify_password(password, user.hashed_password):
        record_failure(lock_key)
        if user is not None:
            user.failed_login_count += 1
        _audit("login", email=normalized, success=False, ip_address=ip_address, details={"reason": "bad_credentials"})
        raise AuthError("Invalid email or password", status_code=401)
    if user.status == UserStatus.disabled:
        raise AuthError("Account is disabled", status_code=403)
    if user.status == UserStatus.locked:
        raise AuthError("Account is locked", status_code=403)

    user.failed_login_count = 0
    record_success(lock_key)
    user.last_login_at = _now_iso()
    session = _create_session(user, ip_address=ip_address, user_agent=user_agent)
    tokens = _issue_tokens(user, session)
    _audit("login", user_id=user.user_id, email=user.email, success=True, ip_address=ip_address, user_agent=user_agent)
    try:
        from backend.monitoring.metrics import record_auth

        record_auth(event="login", status="ok")
    except Exception:
        pass
    return {"user": user.public_dict(), **tokens}


def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    try:
        claims = decode_token(refresh_token, expected_type="refresh")
    except JWTError as exc:
        _audit("refresh", success=False, details={"reason": str(exc)})
        raise AuthError("Invalid or expired refresh token", status_code=401) from exc

    token_hash = hash_token(refresh_token)
    record = next((r for r in _REFRESH_TOKENS.values() if r.token_hash == token_hash), None)
    if record is None or record.revoked:
        raise AuthError("Refresh token has been revoked", status_code=401)
    if _is_expired(record.expires_at):
        raise AuthError("Refresh token has expired", status_code=401)

    session = _SESSIONS.get(record.session_id)
    if session is None or session.revoked or _is_expired(session.expires_at):
        raise AuthError("Session is no longer valid", status_code=401)

    user = _USERS.get(record.user_id)
    if user is None:
        raise AuthError("User no longer exists", status_code=401)

    # Rotate refresh token (revoke old, issue new).
    record.revoked = True
    session.last_seen_at = _now_iso()
    tokens = _issue_tokens(user, session)
    new_hash = hash_token(tokens["refresh_token"])
    new_record = next((r for r in _REFRESH_TOKENS.values() if r.token_hash == new_hash), None)
    if new_record is not None:
        record.rotated_to = new_record.token_id
    _audit("refresh", user_id=user.user_id, email=user.email, success=True)
    return tokens


def _revoke_session_tokens(session_id: str) -> None:
    for record in _REFRESH_TOKENS.values():
        if record.session_id == session_id:
            record.revoked = True


def logout(*, session_id: str = "", refresh_token: str = "") -> dict[str, Any]:
    target_session = session_id
    if not target_session and refresh_token:
        token_hash = hash_token(refresh_token)
        record = next((r for r in _REFRESH_TOKENS.values() if r.token_hash == token_hash), None)
        if record:
            target_session = record.session_id
    if not target_session:
        raise AuthError("A session_id or refresh_token is required to log out", status_code=400)
    session = _SESSIONS.get(target_session)
    if session is not None:
        session.revoked = True
    _revoke_session_tokens(target_session)
    _audit("logout", user_id=session.user_id if session else "", success=True)
    return {"logged_out": True, "session_id": target_session}


def get_current_user(access_token: str) -> User:
    try:
        claims = decode_token(access_token, expected_type="access")
    except JWTError as exc:
        raise AuthError("Invalid or expired access token", status_code=401) from exc
    user = _USERS.get(str(claims.get("sub", "")))
    if user is None:
        raise AuthError("User not found", status_code=401)
    if user.status in {UserStatus.disabled, UserStatus.locked}:
        raise AuthError("Account is not active", status_code=403)
    session_id = claims.get("sid")
    if session_id:
        session = _SESSIONS.get(str(session_id))
        if session is None or session.revoked or _is_expired(session.expires_at):
            raise AuthError("Session is no longer valid", status_code=401)
        session.last_seen_at = _now_iso()
    return user.model_copy(deep=True)


# ---------------------------------------------------------------------------
# Password lifecycle
# ---------------------------------------------------------------------------


def change_password(user_id: str, current_password: str, new_password: str) -> dict[str, Any]:
    user = _USERS.get(user_id)
    if user is None:
        raise AuthError("User not found", status_code=404)
    if not verify_password(current_password, user.hashed_password):
        _audit("change_password", user_id=user_id, success=False, details={"reason": "bad_current"})
        raise AuthError("Current password is incorrect", status_code=400)
    policy = validate_password_policy(new_password)
    if not policy.valid:
        raise AuthError("; ".join(policy.issues), status_code=422)
    user.hashed_password = hash_password(new_password)
    user.updated_at = _now_iso()
    # Revoke all sessions to force re-login after a password change.
    _revoke_all_user_sessions(user_id)
    _audit("change_password", user_id=user_id, email=user.email, success=True)
    return {"changed": True}


def request_password_reset(email: str) -> dict[str, Any]:
    """Create a reset token. Always returns success to avoid account enumeration."""
    config = get_security_config()
    normalized = str(email or "").strip().lower()
    user = _USERS.get(_EMAIL_INDEX.get(normalized, ""))
    reset_token = ""
    if user is not None:
        raw = generate_token()
        reset_token = raw
        record = PasswordResetRequest(
            request_id=_uid("prq"),
            user_id=user.user_id,
            token_hash=hash_token(raw),
            created_at=_now_iso(),
            expires_at=_iso(_now() + timedelta(seconds=config.password_reset_ttl_seconds)),
        )
        _PASSWORD_RESETS[record.request_id] = record
        _audit("request_password_reset", user_id=user.user_id, email=normalized, success=True)
    else:
        _audit("request_password_reset", email=normalized, success=False, details={"reason": "unknown_email"})
    return {"requested": True, "reset_token": reset_token}


def reset_password(token: str, new_password: str) -> dict[str, Any]:
    token_hash = hash_token(token)
    record = next(
        (r for r in _PASSWORD_RESETS.values() if r.token_hash == token_hash and not r.used),
        None,
    )
    if record is None:
        _audit("reset_password", success=False, details={"reason": "invalid_token"})
        raise AuthError("Invalid password reset token", status_code=400)
    if _is_expired(record.expires_at):
        raise AuthError("Password reset token has expired", status_code=400)
    policy = validate_password_policy(new_password)
    if not policy.valid:
        raise AuthError("; ".join(policy.issues), status_code=422)
    user = _USERS.get(record.user_id)
    if user is None:
        raise AuthError("User not found", status_code=404)
    user.hashed_password = hash_password(new_password)
    user.updated_at = _now_iso()
    record.used = True
    _revoke_all_user_sessions(user.user_id)
    _audit("reset_password", user_id=user.user_id, email=user.email, success=True)
    return {"reset": True}


def _revoke_all_user_sessions(user_id: str) -> None:
    for session in _SESSIONS.values():
        if session.user_id == user_id:
            session.revoked = True
    for record in _REFRESH_TOKENS.values():
        if record.user_id == user_id:
            record.revoked = True


# ---------------------------------------------------------------------------
# Session management helpers
# ---------------------------------------------------------------------------


def get_session(session_id: str) -> UserSession | None:
    session = _SESSIONS.get(session_id)
    return session.model_copy(deep=True) if session else None


def list_user_sessions(user_id: str, *, active_only: bool = True) -> list[UserSession]:
    sessions = []
    for session in _SESSIONS.values():
        if session.user_id != user_id:
            continue
        if active_only and (session.revoked or _is_expired(session.expires_at)):
            continue
        sessions.append(session.model_copy(deep=True))
    sessions.sort(key=lambda s: s.created_at, reverse=True)
    return sessions


def count_active_sessions(user_id: str) -> int:
    return len(list_user_sessions(user_id, active_only=True))


def update_profile(user_id: str, profile: dict[str, Any]) -> User:
    user = _USERS.get(user_id)
    if user is None:
        raise AuthError("User not found", status_code=404)
    merged = {**user.profile.model_dump(), **dict(profile or {})}
    user.profile = UserProfile(**merged)
    user.updated_at = _now_iso()
    return user.model_copy(deep=True)
