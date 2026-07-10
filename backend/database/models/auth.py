from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base, JSONType


class UserORM(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    role: Mapped[str] = mapped_column(String(32), default="user")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    hashed_password: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[str] = mapped_column(String(40), default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class UserProfileORM(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class UserSessionORM(Base):
    __tablename__ = "user_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    expires_at: Mapped[str] = mapped_column(String(40), default="")
    created_at: Mapped[str] = mapped_column(String(40), default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class RefreshTokenORM(Base):
    __tablename__ = "refresh_tokens"

    token_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), index=True, default="")
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    expires_at: Mapped[str] = mapped_column(String(40), default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class PasswordResetRequestORM(Base):
    __tablename__ = "password_reset_requests"

    request_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), index=True, default="")
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[str] = mapped_column(String(40), default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)


class EmailVerificationORM(Base):
    __tablename__ = "email_verifications"

    verification_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), index=True, default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[str] = mapped_column(String(40), default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
