from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="Plaintext password (validated by policy)")
    full_name: str = ""
    profile: dict[str, Any] = Field(default_factory=dict)


class RegisterResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool = True
    user: dict[str, Any] = Field(default_factory=dict)
    # Returned in dev to enable verification without an email provider.
    verification_token: str = ""


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str


class TokenResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool = True
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0
    session_id: str = ""
    user: dict[str, Any] = Field(default_factory=dict)


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str


class LogoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = ""
    session_id: str = ""


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str
    new_password: str


class RequestPasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str
    new_password: str


class VerifyEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str


class MessageResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool = True
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class UserResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool = True
    user: dict[str, Any] = Field(default_factory=dict)


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    full_name: str | None = None
    display_name: str | None = None
    company: str | None = None
    job_title: str | None = None
    timezone: str | None = None
    locale: str | None = None
    preferences: dict[str, Any] | None = None


class SessionListResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    success: bool = True
    active_sessions: int = 0
    sessions: list[dict[str, Any]] = Field(default_factory=list)
