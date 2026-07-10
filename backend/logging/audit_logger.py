from __future__ import annotations

from backend.logging.logger import bind_context, get_logger

_log = get_logger("ai_analytics.audit")


def audit(event: str, *, user_id: str = "", organization_id: str = "", workspace_id: str = "", **fields) -> None:
    bind_context(user_id=user_id or None, organization_id=organization_id or None, workspace_id=workspace_id or None)
    _log.info(event, extra={"event": event, "audit": True, **fields})
