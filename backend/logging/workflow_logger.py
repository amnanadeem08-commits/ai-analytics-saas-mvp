from __future__ import annotations

from backend.logging.logger import bind_context, get_logger

_log = get_logger("ai_analytics.workflow")


def log_workflow_event(event: str, *, workflow_id: str = "", execution_id: str = "", **fields) -> None:
    bind_context(workflow_id=workflow_id or None)
    _log.info(event, extra={"event": event, "execution_id": execution_id, **fields})


def log_workflow_started(workflow_id: str, execution_id: str = "", **fields) -> None:
    log_workflow_event("workflow_started", workflow_id=workflow_id, execution_id=execution_id, **fields)


def log_workflow_completed(workflow_id: str, execution_id: str = "", status: str = "", **fields) -> None:
    log_workflow_event("workflow_completed", workflow_id=workflow_id, execution_id=execution_id, status=status, **fields)
