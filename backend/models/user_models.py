from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

USER_SCHEMA_VERSION = "1.0.0"

# Lightweight email pattern — avoids the optional `email-validator` dependency.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(str(email or "").strip()))

# Reserved buckets for later Sprint 8.x growth (RBAC, orgs, billing). Placeholders only.
USER_FUTURE_EXTENSION_KEYS: tuple[str, ...] = (
    "rbac",
    "organizations",
    "multi_tenancy",
    "billing",
    "oauth",
    "sso",
    "mfa",
)


def empty_user_future_extensions() -> dict[str, dict[str, Any]]:
    return {key: {} for key in USER_FUTURE_EXTENSION_KEYS}


class UserStatus(str, Enum):
    active = "active"
    pending = "pending"
    disabled = "disabled"
    locked = "locked"


class UserRole(str, Enum):
    # No RBAC enforcement in Sprint 8.0 — field reserved for later use.
    user = "user"
    admin = "admin"


class UserProfile(BaseModel):
    model_config = ConfigDict(extra="allow")

    full_name: str = ""
    display_name: str = ""
    company: str = ""
    job_title: str = ""
    avatar_url: str = ""
    timezone: str = "UTC"
    locale: str = "en-US"
    preferences: dict[str, Any] = Field(default_factory=dict)


class User(BaseModel):
    """Core user identity record. Password hash is never serialized to clients."""

    model_config = ConfigDict(extra="allow")

    user_id: str
    email: str
    email_verified: bool = False

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if not is_valid_email(normalized):
            raise ValueError("Invalid email address")
        return normalized
    hashed_password: str = Field(default="", repr=False, exclude=True)
    status: UserStatus = UserStatus.pending
    role: UserRole = UserRole.user
    profile: UserProfile = Field(default_factory=UserProfile)
    created_at: str = ""
    updated_at: str = ""
    last_login_at: str = ""
    failed_login_count: int = 0
    schema_version: str = USER_SCHEMA_VERSION
    metadata: dict[str, Any] = Field(default_factory=dict)

    def public_dict(self) -> dict[str, Any]:
        """Serialize without any sensitive fields."""
        data = self.model_dump(exclude={"hashed_password"})
        data.pop("hashed_password", None)
        return data


class UserSession(BaseModel):
    """A login session. Tracks refresh-token lifecycle and revocation."""

    model_config = ConfigDict(extra="allow")

    session_id: str
    user_id: str
    created_at: str = ""
    last_seen_at: str = ""
    expires_at: str = ""
    revoked: bool = False
    ip_address: str = ""
    user_agent: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class RefreshToken(BaseModel):
    """Persisted refresh-token record (hash only, never the raw token)."""

    model_config = ConfigDict(extra="allow")

    token_id: str
    user_id: str
    session_id: str
    token_hash: str = Field(default="", repr=False)
    issued_at: str = ""
    expires_at: str = ""
    revoked: bool = False
    rotated_to: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    request_id: str
    user_id: str
    token_hash: str = Field(default="", repr=False)
    created_at: str = ""
    expires_at: str = ""
    used: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class EmailVerification(BaseModel):
    model_config = ConfigDict(extra="allow")

    verification_id: str
    user_id: str
    email: str
    token_hash: str = Field(default="", repr=False)
    created_at: str = ""
    expires_at: str = ""
    verified: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuthAuditEvent(BaseModel):
    """Basic audit record for authentication events."""

    model_config = ConfigDict(extra="allow")

    event_id: str
    event_type: str
    user_id: str = ""
    email: str = ""
    success: bool = True
    timestamp: str = ""
    ip_address: str = ""
    user_agent: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
