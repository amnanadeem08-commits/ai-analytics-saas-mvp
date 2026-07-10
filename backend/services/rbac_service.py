from __future__ import annotations

"""RBAC service (Sprint 8.1).

Role/permission management + a layered permission-evaluation engine supporting
role inheritance, explicit deny, least privilege, workspace overrides, and
organization defaults. Depends only on repository interfaces.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from backend.models.rbac_models import (
    AccessDecision,
    Permission,
    PermissionEvaluation,
    PermissionScope,
    Role,
    RoleAssignment,
)
from backend.models.user_models import AuthAuditEvent


class RBACError(Exception):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Built-in permission + role catalog
# ---------------------------------------------------------------------------

# Permission ids follow ``<resource>:<action>``.
DEFAULT_PERMISSIONS: tuple[tuple[str, PermissionScope, str], ...] = (
    ("organization:read", PermissionScope.organization, "View organization"),
    ("organization:update", PermissionScope.organization, "Update organization"),
    ("organization:delete", PermissionScope.organization, "Archive/delete organization"),
    ("organization:transfer", PermissionScope.organization, "Transfer ownership"),
    ("member:invite", PermissionScope.organization, "Invite members"),
    ("member:read", PermissionScope.organization, "List members"),
    ("member:remove", PermissionScope.organization, "Remove members"),
    ("workspace:create", PermissionScope.organization, "Create workspaces"),
    ("workspace:read", PermissionScope.workspace, "View workspace"),
    ("workspace:update", PermissionScope.workspace, "Update workspace"),
    ("workspace:delete", PermissionScope.workspace, "Archive/delete workspace"),
    ("rbac:read", PermissionScope.organization, "View roles and permissions"),
    ("rbac:assign", PermissionScope.organization, "Assign or remove roles"),
    ("analyst:run", PermissionScope.workspace, "Run AI Analyst in workspace"),
)

# role_id -> (name, scope, granted, denied, inherits)
DEFAULT_ROLES: tuple[dict[str, Any], ...] = (
    {
        "role_id": "viewer",
        "name": "Viewer",
        "scope": PermissionScope.organization,
        "permissions": ["organization:read", "workspace:read", "member:read", "rbac:read"],
        "inherits": [],
        "priority": 10,
    },
    {
        "role_id": "member",
        "name": "Member",
        "scope": PermissionScope.organization,
        "permissions": ["workspace:create", "analyst:run"],
        "inherits": ["viewer"],
        "priority": 20,
    },
    {
        "role_id": "admin",
        "name": "Admin",
        "scope": PermissionScope.organization,
        "permissions": [
            "organization:update",
            "member:invite",
            "member:remove",
            "workspace:update",
            "workspace:delete",
            "rbac:assign",
        ],
        "inherits": ["member"],
        "priority": 30,
    },
    {
        "role_id": "owner",
        "name": "Owner",
        "scope": PermissionScope.organization,
        "permissions": ["organization:delete", "organization:transfer"],
        "inherits": ["admin"],
        "priority": 40,
    },
)

BUILTIN_ROLE_IDS: tuple[str, ...] = tuple(r["role_id"] for r in DEFAULT_ROLES)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def seed_default_roles_and_permissions(registry) -> None:
    """Populate a registry with the built-in permission + role catalog."""
    for pid, scope, desc in DEFAULT_PERMISSIONS:
        if registry.permissions.get(pid) is None:
            registry.permissions.add(
                Permission(
                    permission_id=pid,
                    name=pid,
                    description=desc,
                    scope=scope,
                    category=pid.split(":", 1)[0],
                )
            )
    now = _now_iso()
    for spec in DEFAULT_ROLES:
        if registry.roles.get(spec["role_id"]) is None:
            registry.roles.add(
                Role(
                    role_id=spec["role_id"],
                    name=spec["name"],
                    description=spec.get("description", spec["name"]),
                    scope=spec["scope"],
                    permissions=list(spec.get("permissions", [])),
                    denied_permissions=list(spec.get("denied_permissions", [])),
                    inherits=list(spec.get("inherits", [])),
                    is_system=True,
                    priority=spec.get("priority", 0),
                    created_at=now,
                    updated_at=now,
                )
            )


def _repos():
    from backend.repositories.registry import get_repositories

    return get_repositories()


def _audit(event_type: str, *, user_id: str = "", success: bool = True, details: dict[str, Any] | None = None) -> None:
    _repos().audit.add(
        AuthAuditEvent(
            event_id=_uid("evt"),
            event_type=event_type,
            user_id=user_id,
            success=success,
            timestamp=_now_iso(),
            details=dict(details or {}),
        )
    )


# ---------------------------------------------------------------------------
# Role / permission listing
# ---------------------------------------------------------------------------


def list_roles() -> list[Role]:
    return _repos().roles.list()


def list_permissions() -> list[Permission]:
    return _repos().permissions.list()


def get_role(role_id: str) -> Role | None:
    return _repos().roles.get(role_id)


def _expand_role_permissions(role_id: str, *, _seen: set[str] | None = None) -> tuple[set[str], set[str], list[str]]:
    """Resolve a role's effective granted + denied permissions via inheritance.

    Returns (granted, denied, roles_considered).
    """
    seen = _seen if _seen is not None else set()
    if role_id in seen:
        return set(), set(), []
    seen.add(role_id)
    role = _repos().roles.get(role_id)
    if role is None:
        return set(), set(), []
    granted: set[str] = set(role.permissions)
    denied: set[str] = set(role.denied_permissions)
    considered: list[str] = [role_id]
    for parent in role.inherits:
        p_granted, p_denied, p_considered = _expand_role_permissions(parent, _seen=seen)
        granted |= p_granted
        denied |= p_denied
        considered.extend(p_considered)
    return granted, denied, considered


# ---------------------------------------------------------------------------
# Role assignment
# ---------------------------------------------------------------------------


def assign_role(
    *,
    user_id: str,
    role_id: str,
    scope: PermissionScope | str = PermissionScope.organization,
    organization_id: str = "",
    workspace_id: str = "",
    granted_by: str = "",
) -> RoleAssignment:
    repos = _repos()
    if repos.roles.get(role_id) is None:
        raise RBACError(f"Unknown role: {role_id}", status_code=404)
    scope_enum = scope if isinstance(scope, PermissionScope) else PermissionScope(str(scope))
    if scope_enum == PermissionScope.workspace and not workspace_id:
        raise RBACError("workspace_id is required for workspace-scoped assignments", status_code=422)
    if scope_enum == PermissionScope.organization and not organization_id:
        raise RBACError("organization_id is required for organization-scoped assignments", status_code=422)

    # Replace an existing identical-scope assignment for this user+role.
    for existing in repos.role_assignments.list(user_id=user_id):
        if (
            existing.role_id == role_id
            and existing.scope == scope_enum
            and existing.organization_id == organization_id
            and existing.workspace_id == workspace_id
        ):
            return existing

    assignment = RoleAssignment(
        assignment_id=_uid("rasg"),
        user_id=user_id,
        role_id=role_id,
        scope=scope_enum,
        organization_id=organization_id,
        workspace_id=workspace_id,
        granted_by=granted_by,
        created_at=_now_iso(),
    )
    repos.role_assignments.add(assignment)
    _audit(
        "role_assigned",
        user_id=granted_by,
        details={"target_user": user_id, "role_id": role_id, "scope": scope_enum.value, "organization_id": organization_id, "workspace_id": workspace_id},
    )
    return assignment


def remove_role(assignment_id: str, *, removed_by: str = "") -> bool:
    repos = _repos()
    existing = repos.role_assignments.get(assignment_id)
    removed = repos.role_assignments.delete(assignment_id)
    if removed and existing is not None:
        _audit(
            "role_removed",
            user_id=removed_by,
            details={"target_user": existing.user_id, "role_id": existing.role_id},
        )
    return removed


def list_role_assignments(
    *,
    user_id: str | None = None,
    organization_id: str | None = None,
    workspace_id: str | None = None,
) -> list[RoleAssignment]:
    return _repos().role_assignments.list(
        user_id=user_id, organization_id=organization_id, workspace_id=workspace_id
    )


# ---------------------------------------------------------------------------
# Evaluation engine
# ---------------------------------------------------------------------------


def _scope_decision(
    assignments: list[RoleAssignment],
    permission: str,
) -> tuple[str, str, list[str]]:
    """Return (decision, matched_role, roles_considered) for one scope layer.

    Within a scope, explicit deny wins over allow (explicit-deny principle).
    """
    granted: set[str] = set()
    denied: set[str] = set()
    matched_role = ""
    considered: list[str] = []
    for assignment in assignments:
        g, d, c = _expand_role_permissions(assignment.role_id)
        considered.extend(c)
        if permission in d:
            denied.add(permission)
        if permission in g:
            granted.add(permission)
            if not matched_role:
                matched_role = assignment.role_id
    if permission in denied:
        return "deny", matched_role, considered
    if permission in granted:
        return "allow", matched_role, considered
    return "none", matched_role, considered


def evaluate_access(
    *,
    user_id: str,
    permission: str,
    organization_id: str = "",
    workspace_id: str = "",
) -> PermissionEvaluation:
    """Layered evaluation: workspace > organization > system; explicit deny + least privilege.

    Organization owners implicitly hold all permissions within their org.
    """
    repos = _repos()

    # Owner short-circuit (organization-level implicit superuser).
    if organization_id:
        org = repos.organizations.get(organization_id)
        if org is not None and org.owner_id == user_id:
            decision = AccessDecision(
                allowed=True,
                permission=permission,
                user_id=user_id,
                organization_id=organization_id,
                workspace_id=workspace_id,
                reason="Organization owner has full access",
                matched_role="owner",
                decisive_scope="organization",
            )
            return PermissionEvaluation(
                permission=permission,
                user_id=user_id,
                allowed=True,
                reason="owner_override",
                organization_decision="allow",
                roles_considered=["owner"],
                decision=decision,
            )

    all_assignments = repos.role_assignments.list(user_id=user_id)
    system_assignments = [a for a in all_assignments if a.scope == PermissionScope.system]
    org_assignments = [
        a
        for a in all_assignments
        if a.scope == PermissionScope.organization
        and (not organization_id or a.organization_id == organization_id)
    ]
    ws_assignments = [
        a
        for a in all_assignments
        if a.scope == PermissionScope.workspace
        and (not workspace_id or a.workspace_id == workspace_id)
    ]

    ws_dec, ws_role, ws_considered = _scope_decision(ws_assignments, permission)
    org_dec, org_role, org_considered = _scope_decision(org_assignments, permission)
    sys_dec, sys_role, sys_considered = _scope_decision(system_assignments, permission)

    # Most specific scope with an opinion wins (workspace overrides org overrides system).
    decisive_scope = ""
    final = "none"
    matched_role = ""
    for name, dec, role in (
        ("workspace", ws_dec, ws_role),
        ("organization", org_dec, org_role),
        ("system", sys_dec, sys_role),
    ):
        if dec != "none":
            decisive_scope = name
            final = dec
            matched_role = role
            break

    allowed = final == "allow"
    if final == "deny":
        reason = f"Explicit deny at {decisive_scope} scope"
    elif final == "allow":
        reason = f"Granted at {decisive_scope} scope"
    else:
        reason = "No matching grant (least privilege default deny)"

    decision = AccessDecision(
        allowed=allowed,
        permission=permission,
        user_id=user_id,
        organization_id=organization_id,
        workspace_id=workspace_id,
        reason=reason,
        matched_role=matched_role,
        decisive_scope=decisive_scope,
    )
    return PermissionEvaluation(
        permission=permission,
        user_id=user_id,
        allowed=allowed,
        reason=reason,
        workspace_decision=ws_dec,
        organization_decision=org_dec,
        system_decision=sys_dec,
        roles_considered=sorted(set(ws_considered + org_considered + sys_considered)),
        decision=decision,
    )


def has_permission(
    user_id: str,
    permission: str,
    *,
    organization_id: str = "",
    workspace_id: str = "",
) -> bool:
    return evaluate_access(
        user_id=user_id,
        permission=permission,
        organization_id=organization_id,
        workspace_id=workspace_id,
    ).allowed


def authorize(
    user_id: str,
    permission: str,
    *,
    organization_id: str = "",
    workspace_id: str = "",
) -> AccessDecision:
    """Return an AccessDecision, raising RBACError(403) when not allowed."""
    evaluation = evaluate_access(
        user_id=user_id,
        permission=permission,
        organization_id=organization_id,
        workspace_id=workspace_id,
    )
    if not evaluation.allowed:
        raise RBACError(
            f"Permission denied: {permission} ({evaluation.reason})",
            status_code=403,
        )
    return evaluation.decision  # type: ignore[return-value]
