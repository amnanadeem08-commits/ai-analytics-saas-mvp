from __future__ import annotations

"""Authentication FastAPI dependencies (Sprint 8.0).

Provides current-user injection via bearer token. No RBAC enforcement.
"""

from typing import Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.api.error_handlers import raise_api_error
from backend.models.user_models import User
from backend.services.auth_service import AuthError, get_current_user

# auto_error=False so we can return a structured 401 payload ourselves.
_bearer_scheme = HTTPBearer(auto_error=False, description="Bearer access token")


def _extract_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> str:
    if credentials and credentials.scheme.lower() == "bearer" and credentials.credentials:
        return credentials.credentials
    # Optional secure-cookie fallback.
    cookie_token = request.cookies.get("access_token")
    return cookie_token or ""


def get_current_user_dependency(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> User:
    """Require a valid access token; inject the current user or raise 401."""
    token = _extract_token(request, credentials)
    if not token:
        raise_api_error(401, "Authentication required")
    try:
        return get_current_user(token)
    except AuthError as exc:
        raise_api_error(exc.status_code, exc.message)


def get_optional_user_dependency(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[User]:
    """Return the current user when a valid token is present, else None."""
    token = _extract_token(request, credentials)
    if not token:
        return None
    try:
        return get_current_user(token)
    except AuthError:
        return None


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


def client_user_agent(request: Request) -> str:
    return request.headers.get("user-agent", "")


# ---------------------------------------------------------------------------
# Sprint 8.1 — Authorization dependencies (organizations, workspaces, RBAC)
# Routes request *permissions*, not roles.
# ---------------------------------------------------------------------------


def current_organization(
    request: Request,
    organization_id: Optional[str] = None,
) -> str:
    """Resolve the active organization id from path/query/header.

    Order: explicit arg → path param → query param → ``X-Organization-Id`` header.
    """
    org_id = (
        organization_id
        or request.path_params.get("organization_id")
        or request.query_params.get("organization_id")
        or request.headers.get("x-organization-id")
        or ""
    )
    return str(org_id)


def current_workspace(
    request: Request,
    workspace_id: Optional[str] = None,
) -> str:
    """Resolve the active workspace id from path/query/header."""
    ws_id = (
        workspace_id
        or request.path_params.get("workspace_id")
        or request.query_params.get("workspace_id")
        or request.headers.get("x-workspace-id")
        or ""
    )
    return str(ws_id)


def require_permission(permission: str):
    """Dependency factory enforcing a permission for the current user.

    Resolves organization/workspace scope from the request automatically.
    """

    def _dependency(
        request: Request,
        current_user: User = Depends(get_current_user_dependency),
    ) -> User:
        from backend.services.rbac_service import has_permission

        org_id = current_organization(request)
        ws_id = current_workspace(request)
        allowed = has_permission(
            current_user.user_id,
            permission,
            organization_id=org_id,
            workspace_id=ws_id,
        )
        if not allowed:
            raise_api_error(403, f"Permission denied: {permission}")
        return current_user

    return _dependency


def require_role(role_id: str):
    """Dependency factory enforcing that the user holds a specific role in scope."""

    def _dependency(
        request: Request,
        current_user: User = Depends(get_current_user_dependency),
    ) -> User:
        from backend.services.rbac_service import list_role_assignments

        org_id = current_organization(request)
        ws_id = current_workspace(request)
        assignments = list_role_assignments(user_id=current_user.user_id)
        for assignment in assignments:
            if assignment.role_id != role_id:
                continue
            if org_id and assignment.organization_id and assignment.organization_id != org_id:
                continue
            if ws_id and assignment.workspace_id and assignment.workspace_id != ws_id:
                continue
            return current_user
        raise_api_error(403, f"Role required: {role_id}")

    return _dependency
