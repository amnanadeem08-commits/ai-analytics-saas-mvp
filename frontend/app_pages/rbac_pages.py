from __future__ import annotations

"""Organization / Workspace / RBAC admin pages (Sprint 8.1).

All data flows through the FastAPI `/api/v1` gateway. No backend imports.
"""

import streamlit as st

from frontend.api.base import friendly_api_error
from frontend.api.organization_client import OrganizationClient
from frontend.api.rbac_client import RBACClient
from frontend.api.workspace_client import WorkspaceClient
from frontend.utils.auth_state import get_access_token, is_authenticated, with_auto_refresh
from frontend.utils.session_state import navigate_to
from frontend.utils.workspace_api import get_api_client


def _clients():
    api = get_api_client()
    return OrganizationClient(api), WorkspaceClient(api), RBACClient(api)


def _require_login() -> bool:
    if not is_authenticated():
        st.warning("Please sign in to manage organizations.")
        if st.button("Go to Login", key="rbac_go_login"):
            navigate_to("Login")
            st.rerun()
        return False
    return True


def _error(exc: Exception) -> None:
    st.error(friendly_api_error(exc))


def _active_org_selector(org_client: OrganizationClient) -> str | None:
    token = get_access_token()
    try:
        result = with_auto_refresh(lambda t: org_client.list(t))
    except Exception as exc:
        _error(exc)
        return None
    orgs = result.get("organizations", [])
    if not orgs:
        st.info("No organizations yet. Create one on the Organizations page.")
        return None
    labels = [f"{o['name']} ({o['organization_id']})" for o in orgs]
    default = st.session_state.get("active_organization_id")
    index = 0
    for i, o in enumerate(orgs):
        if o["organization_id"] == default:
            index = i
            break
    choice = st.selectbox("Organization", labels, index=index, key="rbac_org_select")
    selected = orgs[labels.index(choice)]
    st.session_state["active_organization_id"] = selected["organization_id"]
    return selected["organization_id"]


def render_organizations(client=None) -> None:
    st.header("Organizations")
    if not _require_login():
        return
    org_client, _ws, _rbac = _clients()
    token = get_access_token()

    with st.expander("Create organization", expanded=False):
        with st.form("create_org_form"):
            name = st.text_input("Name")
            submitted = st.form_submit_button("Create", type="primary")
        if submitted and name.strip():
            try:
                result = with_auto_refresh(lambda t: org_client.create(t, name.strip()))
                st.success(f"Created organization {result['organization']['organization_id']}")
                st.rerun()
            except Exception as exc:
                _error(exc)

    try:
        result = with_auto_refresh(lambda t: org_client.list(t))
    except Exception as exc:
        _error(exc)
        return
    orgs = result.get("organizations", [])
    st.write(f"{len(orgs)} organization(s)")
    for org in orgs:
        with st.expander(f"{org['name']} — {org['status']}"):
            st.json(org)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Set active", key=f"activate_{org['organization_id']}"):
                    st.session_state["active_organization_id"] = org["organization_id"]
                    st.success("Active organization set.")
            with c2:
                if org["status"] != "archived" and st.button("Archive", key=f"archive_{org['organization_id']}"):
                    try:
                        with_auto_refresh(lambda t: org_client.archive(t, org["organization_id"]))
                        st.rerun()
                    except Exception as exc:
                        _error(exc)


def render_workspace_manager(client=None) -> None:
    st.header("Workspace Manager")
    if not _require_login():
        return
    org_client, ws_client, _rbac = _clients()
    organization_id = _active_org_selector(org_client)
    if not organization_id:
        return

    with st.expander("Create workspace", expanded=False):
        with st.form("create_ws_form"):
            name = st.text_input("Workspace name")
            submitted = st.form_submit_button("Create", type="primary")
        if submitted and name.strip():
            try:
                with_auto_refresh(lambda t: ws_client.create(t, organization_id, name.strip()))
                st.success("Workspace created.")
                st.rerun()
            except Exception as exc:
                _error(exc)

    try:
        result = with_auto_refresh(lambda t: ws_client.list(t, organization_id))
    except Exception as exc:
        _error(exc)
        return
    workspaces = result.get("workspaces", [])
    st.write(f"{len(workspaces)} workspace(s)")
    for ws in workspaces:
        with st.expander(f"{ws['name']} — {ws['status']}"):
            st.json(ws)
            c1, c2 = st.columns(2)
            with c1:
                if ws["status"] != "archived" and st.button("Archive", key=f"ws_arch_{ws['workspace_id']}"):
                    try:
                        with_auto_refresh(lambda t: ws_client.archive(t, ws["workspace_id"]))
                        st.rerun()
                    except Exception as exc:
                        _error(exc)
            with c2:
                if ws["status"] == "archived" and st.button("Restore", key=f"ws_rest_{ws['workspace_id']}"):
                    try:
                        with_auto_refresh(lambda t: ws_client.restore(t, ws["workspace_id"]))
                        st.rerun()
                    except Exception as exc:
                        _error(exc)


def render_members(client=None) -> None:
    st.header("Members")
    if not _require_login():
        return
    org_client, _ws, _rbac = _clients()
    organization_id = _active_org_selector(org_client)
    if not organization_id:
        return
    try:
        result = with_auto_refresh(lambda t: org_client.list_members(t, organization_id))
        members = result.get("members", [])
        st.write(f"{len(members)} member(s)")
        st.dataframe(members, use_container_width=True) if members else st.info("No members.")
    except Exception as exc:
        _error(exc)

    with st.form("remove_member_form"):
        member_user_id = st.text_input("Remove member by user_id")
        submitted = st.form_submit_button("Remove member")
    if submitted and member_user_id.strip():
        try:
            with_auto_refresh(lambda t: org_client.remove_member(t, organization_id, member_user_id.strip()))
            st.success("Member removed.")
            st.rerun()
        except Exception as exc:
            _error(exc)


def render_invitations(client=None) -> None:
    st.header("Invitations")
    if not _require_login():
        return
    org_client, _ws, _rbac = _clients()
    organization_id = _active_org_selector(org_client)

    st.subheader("Send invitation")
    if organization_id:
        with st.form("invite_form"):
            email = st.text_input("Invitee email")
            role_id = st.selectbox("Role", ["viewer", "member", "admin"], index=1)
            submitted = st.form_submit_button("Send invite", type="primary")
        if submitted and email.strip():
            try:
                result = with_auto_refresh(
                    lambda t: org_client.invite(t, organization_id, email.strip(), role_id=role_id)
                )
                st.success("Invitation created.")
                st.info("Development invitation token (no email provider):")
                st.code(result.get("invitation_token", ""))
            except Exception as exc:
                _error(exc)

    st.divider()
    st.subheader("Respond to an invitation")
    token_value = st.text_input("Invitation token")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Accept", type="primary") and token_value.strip():
            try:
                with_auto_refresh(lambda t: org_client.accept_invitation(t, token_value.strip()))
                st.success("Invitation accepted.")
            except Exception as exc:
                _error(exc)
    with c2:
        if st.button("Decline") and token_value.strip():
            try:
                with_auto_refresh(lambda t: org_client.decline_invitation(t, token_value.strip()))
                st.success("Invitation declined.")
            except Exception as exc:
                _error(exc)


def render_roles(client=None) -> None:
    st.header("Roles")
    if not _require_login():
        return
    _org, ws_client, rbac_client = _clients()
    try:
        result = with_auto_refresh(lambda t: rbac_client.list_roles(t))
        st.write(f"{result.get('count', 0)} role(s)")
        for role in result.get("roles", []):
            with st.expander(f"{role['name']} ({role['role_id']})"):
                st.json(role)
    except Exception as exc:
        _error(exc)

    st.divider()
    st.subheader("Assign a role")
    org_client, _ws2, _rbac2 = _clients()
    organization_id = st.session_state.get("active_organization_id", "")
    with st.form("assign_role_form"):
        user_id = st.text_input("User id")
        role_id = st.selectbox("Role", ["viewer", "member", "admin", "owner"], index=1)
        scope = st.selectbox("Scope", ["organization", "workspace"], index=0)
        organization_id = st.text_input("Organization id", value=organization_id)
        workspace_id = st.text_input("Workspace id", value="")
        submitted = st.form_submit_button("Assign role", type="primary")
    if submitted and user_id.strip():
        try:
            with_auto_refresh(
                lambda t: rbac_client.assign_role(
                    t,
                    user_id=user_id.strip(),
                    role_id=role_id,
                    scope=scope,
                    organization_id=organization_id.strip(),
                    workspace_id=workspace_id.strip(),
                )
            )
            st.success("Role assigned.")
        except Exception as exc:
            _error(exc)


def render_permissions(client=None) -> None:
    st.header("Permissions")
    if not _require_login():
        return
    _org, _ws, rbac_client = _clients()
    try:
        result = with_auto_refresh(lambda t: rbac_client.list_permissions(t))
        st.write(f"{result.get('count', 0)} permission(s)")
        st.dataframe(result.get("permissions", []), use_container_width=True)
    except Exception as exc:
        _error(exc)

    st.divider()
    st.subheader("Check access")
    with st.form("check_access_form"):
        permission = st.text_input("Permission", value="workspace:create")
        organization_id = st.text_input("Organization id", value=st.session_state.get("active_organization_id", ""))
        workspace_id = st.text_input("Workspace id", value="")
        submitted = st.form_submit_button("Evaluate")
    if submitted and permission.strip():
        try:
            result = with_auto_refresh(
                lambda t: rbac_client.check_access(
                    t,
                    permission=permission.strip(),
                    organization_id=organization_id.strip(),
                    workspace_id=workspace_id.strip(),
                )
            )
            evaluation = result.get("evaluation", {})
            if evaluation.get("allowed"):
                st.success(f"Allowed — {evaluation.get('reason')}")
            else:
                st.warning(f"Denied — {evaluation.get('reason')}")
            st.json(evaluation)
        except Exception as exc:
            _error(exc)
