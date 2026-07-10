from __future__ import annotations

"""Authentication pages: Login, Register, Profile, Change Password.

Uses the FastAPI `/api/v1/auth` endpoints only — no backend imports.
"""

import streamlit as st

from frontend.api.base import ApiError, friendly_api_error
from frontend.utils.auth_state import (
    clear_tokens,
    current_user,
    get_access_token,
    get_auth_client,
    hydrate_current_user,
    is_authenticated,
    store_tokens,
    with_auto_refresh,
)
from frontend.utils.session_state import navigate_to


def _show_error(exc: Exception) -> None:
    st.error(friendly_api_error(exc))


def render_login(client=None) -> None:
    st.header("Sign In")
    if is_authenticated():
        user = current_user()
        st.success(f"Signed in as {user.get('email', 'user')}.")
        if st.button("Go to AI Analyst"):
            navigate_to("AI Analyst")
            st.rerun()
        return

    auth = get_auth_client()
    tab_login, tab_reset = st.tabs(["Login", "Forgot password"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", type="primary")
        if submitted:
            try:
                payload = auth.login(email.strip(), password)
                store_tokens(payload)
                st.success("Signed in successfully.")
                navigate_to("Home")
                st.rerun()
            except Exception as exc:
                _show_error(exc)
        st.caption("Don't have an account?")
        if st.button("Create an account"):
            navigate_to("Register")
            st.rerun()

    with tab_reset:
        with st.form("reset_request_form"):
            reset_email = st.text_input("Account email", key="reset_email")
            reset_submit = st.form_submit_button("Request reset token")
        if reset_submit:
            try:
                result = auth.request_password_reset(reset_email.strip())
                st.success("If the email exists, a reset token has been generated.")
                token = result.get("verification_token")
                if token:
                    st.info("Development reset token (no email provider configured):")
                    st.code(token)
                    st.session_state["pending_reset_token"] = token
            except Exception as exc:
                _show_error(exc)

        with st.form("reset_apply_form"):
            token = st.text_input("Reset token", value=st.session_state.get("pending_reset_token", ""))
            new_password = st.text_input("New password", type="password", key="reset_new_pw")
            apply_submit = st.form_submit_button("Reset password")
        if apply_submit:
            try:
                auth.reset_password(token.strip(), new_password)
                st.success("Password reset. You can now sign in.")
                st.session_state.pop("pending_reset_token", None)
            except Exception as exc:
                _show_error(exc)


def render_register(client=None) -> None:
    st.header("Create Account")
    if is_authenticated():
        st.info("You are already signed in.")
        return

    auth = get_auth_client()
    with st.form("register_form"):
        full_name = st.text_input("Full name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Register", type="primary")
    st.caption("Password must be at least 8 characters with upper, lower, and a digit.")

    if submitted:
        if password != confirm:
            st.error("Passwords do not match.")
            return
        try:
            result = auth.register(email.strip(), password, full_name=full_name.strip())
            st.success("Account created. You can sign in now.")
            token = result.get("verification_token")
            if token:
                st.info("Development email-verification token:")
                st.code(token)
                if st.button("Verify email now"):
                    try:
                        auth.verify_email(token)
                        st.success("Email verified.")
                    except Exception as exc:
                        _show_error(exc)
            if st.button("Go to login"):
                navigate_to("Login")
                st.rerun()
        except Exception as exc:
            _show_error(exc)


def _require_auth() -> bool:
    if not is_authenticated():
        st.warning("Please sign in to view this page.")
        if st.button("Go to Login"):
            navigate_to("Login")
            st.rerun()
        return False
    return True


def render_profile(client=None) -> None:
    st.header("Profile")
    if not _require_auth():
        return

    auth = get_auth_client()
    user = hydrate_current_user() or current_user()
    if not user:
        st.error("Could not load profile. Your session may have expired.")
        return

    st.markdown(f"**Email:** {user.get('email', '')}")
    st.markdown(f"**Status:** {user.get('status', '')}")
    st.markdown(f"**Email verified:** {user.get('email_verified', False)}")
    profile = user.get("profile", {}) or {}

    with st.form("profile_form"):
        full_name = st.text_input("Full name", value=profile.get("full_name", ""))
        display_name = st.text_input("Display name", value=profile.get("display_name", ""))
        company = st.text_input("Company", value=profile.get("company", ""))
        job_title = st.text_input("Job title", value=profile.get("job_title", ""))
        timezone = st.text_input("Timezone", value=profile.get("timezone", "UTC"))
        submitted = st.form_submit_button("Save profile", type="primary")
    if submitted:
        try:
            payload = {
                "full_name": full_name,
                "display_name": display_name,
                "company": company,
                "job_title": job_title,
                "timezone": timezone,
            }
            result = with_auto_refresh(lambda token: auth.update_profile(token, payload))
            st.session_state["auth_user"] = result.get("user", user)
            st.success("Profile updated.")
        except Exception as exc:
            _show_error(exc)

    st.divider()
    st.subheader("Active sessions")
    try:
        sessions = with_auto_refresh(lambda token: auth.list_sessions(token))
        st.write(f"{sessions.get('active_sessions', 0)} active session(s)")
        st.json(sessions.get("sessions", []))
    except Exception as exc:
        _show_error(exc)

    st.divider()
    if st.button("Sign out", type="secondary"):
        try:
            with_auto_refresh(
                lambda token: auth.logout(
                    access_token=token,
                    refresh_token=st.session_state.get("auth_refresh_token", ""),
                    session_id=st.session_state.get("auth_session_id", ""),
                )
            )
        except Exception:
            pass
        clear_tokens()
        st.success("Signed out.")
        navigate_to("Login")
        st.rerun()


def render_change_password(client=None) -> None:
    st.header("Change Password")
    if not _require_auth():
        return
    auth = get_auth_client()
    with st.form("change_password_form"):
        current_password = st.text_input("Current password", type="password")
        new_password = st.text_input("New password", type="password")
        confirm = st.text_input("Confirm new password", type="password")
        submitted = st.form_submit_button("Change password", type="primary")
    if submitted:
        if new_password != confirm:
            st.error("New passwords do not match.")
            return
        try:
            with_auto_refresh(
                lambda token: auth.change_password(token, current_password, new_password)
            )
            st.success("Password changed. Please sign in again.")
            clear_tokens()
            navigate_to("Login")
            st.rerun()
        except Exception as exc:
            _show_error(exc)
