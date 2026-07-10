from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from backend.api.auth_dependencies import (
    client_ip,
    client_user_agent,
    get_current_user_dependency,
)
from backend.api.error_handlers import map_service_exception, raise_api_error
from backend.api.models.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    RequestPasswordResetRequest,
    ResetPasswordRequest,
    SessionListResponse,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from backend.models.user_models import User
from backend.services import auth_service
from backend.services.auth_service import AuthError

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def _handle(exc: Exception):
    if isinstance(exc, AuthError):
        raise_api_error(exc.status_code, exc.message)
    raise map_service_exception(exc) from exc


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a user account, enforces the password policy, and issues an email-verification token.",
    responses={
        201: {"description": "User registered"},
        409: {"description": "Email already registered"},
        422: {"description": "Invalid email or weak password"},
    },
)
def register(request: RegisterRequest) -> RegisterResponse:
    try:
        result = auth_service.register_user(
            request.email,
            request.password,
            full_name=request.full_name,
            profile=request.profile,
        )
        return RegisterResponse(success=True, **result)
    except Exception as exc:
        _handle(exc)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive tokens",
    description="Validates credentials and returns an access token, refresh token, and session id.",
    responses={
        200: {"description": "Authenticated"},
        401: {"description": "Invalid credentials"},
        403: {"description": "Account disabled or locked"},
    },
)
def login(request: LoginRequest, http_request: Request) -> TokenResponse:
    try:
        result = auth_service.authenticate_user(
            request.email,
            request.password,
            ip_address=client_ip(http_request),
            user_agent=client_user_agent(http_request),
        )
        return TokenResponse(success=True, **result)
    except Exception as exc:
        _handle(exc)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token and issue new access token",
    description="Exchanges a valid refresh token for a new access/refresh token pair (rotation).",
    responses={
        200: {"description": "Tokens refreshed"},
        401: {"description": "Invalid, expired, or revoked refresh token"},
    },
)
def refresh(request: RefreshRequest) -> TokenResponse:
    try:
        result = auth_service.refresh_access_token(request.refresh_token)
        return TokenResponse(success=True, **result)
    except Exception as exc:
        _handle(exc)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Log out and revoke the session",
    description="Revokes the current session and its refresh tokens.",
    responses={200: {"description": "Logged out"}, 400: {"description": "Missing session identifier"}},
)
def logout(
    request: LogoutRequest,
    current_user: User = Depends(get_current_user_dependency),
) -> MessageResponse:
    try:
        result = auth_service.logout(
            session_id=request.session_id,
            refresh_token=request.refresh_token,
        )
        return MessageResponse(success=True, message="Logged out", details=result)
    except Exception as exc:
        _handle(exc)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change the current user's password",
    description="Verifies the current password, applies the policy, and revokes all sessions.",
    responses={
        200: {"description": "Password changed"},
        400: {"description": "Current password incorrect"},
        422: {"description": "New password fails policy"},
    },
)
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user_dependency),
) -> MessageResponse:
    try:
        auth_service.change_password(
            current_user.user_id,
            request.current_password,
            request.new_password,
        )
        return MessageResponse(success=True, message="Password changed. Please log in again.")
    except Exception as exc:
        _handle(exc)


@router.post(
    "/request-password-reset",
    response_model=RegisterResponse,
    summary="Request a password reset token",
    description="Always returns success to prevent account enumeration; includes a dev reset token.",
    responses={200: {"description": "Reset requested"}},
)
def request_password_reset(request: RequestPasswordResetRequest) -> RegisterResponse:
    try:
        result = auth_service.request_password_reset(request.email)
        return RegisterResponse(success=True, user={}, verification_token=result.get("reset_token", ""))
    except Exception as exc:
        _handle(exc)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset a password with a reset token",
    description="Consumes a valid reset token, applies the policy, and revokes all sessions.",
    responses={
        200: {"description": "Password reset"},
        400: {"description": "Invalid or expired token"},
        422: {"description": "New password fails policy"},
    },
)
def reset_password(request: ResetPasswordRequest) -> MessageResponse:
    try:
        auth_service.reset_password(request.token, request.new_password)
        return MessageResponse(success=True, message="Password reset. Please log in again.")
    except Exception as exc:
        _handle(exc)


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify an email address",
    description="Marks the account email as verified using a verification token.",
    responses={200: {"description": "Email verified"}, 400: {"description": "Invalid or expired token"}},
)
def verify_email(request: VerifyEmailRequest) -> MessageResponse:
    try:
        result = auth_service.verify_email(request.token)
        return MessageResponse(success=True, message="Email verified", details=result)
    except Exception as exc:
        _handle(exc)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the current authenticated user",
    description="Returns the current user's public profile. Requires a valid access token.",
    responses={200: {"description": "Current user"}, 401: {"description": "Authentication required"}},
)
def me(current_user: User = Depends(get_current_user_dependency)) -> UserResponse:
    return UserResponse(success=True, user=current_user.public_dict())


@router.put(
    "/me/profile",
    response_model=UserResponse,
    summary="Update the current user's profile",
    description="Updates profile fields for the authenticated user.",
    responses={200: {"description": "Profile updated"}, 401: {"description": "Authentication required"}},
)
def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user_dependency),
) -> UserResponse:
    try:
        payload = {k: v for k, v in request.model_dump().items() if v is not None}
        user = auth_service.update_profile(current_user.user_id, payload)
        return UserResponse(success=True, user=user.public_dict())
    except Exception as exc:
        _handle(exc)


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    summary="List active sessions for the current user",
    description="Returns active (non-revoked, unexpired) sessions for the authenticated user.",
    responses={200: {"description": "Session list"}, 401: {"description": "Authentication required"}},
)
def list_sessions(current_user: User = Depends(get_current_user_dependency)) -> SessionListResponse:
    sessions = auth_service.list_user_sessions(current_user.user_id, active_only=True)
    return SessionListResponse(
        success=True,
        active_sessions=len(sessions),
        sessions=[s.model_dump() for s in sessions],
    )
