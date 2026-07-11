from __future__ import annotations

"""Usage tracking service (Sprint 8.6)."""

import uuid
from datetime import datetime, timezone
from typing import Any

from backend.models.billing_models import UsageMetric, UsageRecord


class UsageError(Exception):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


_RATE_BUCKETS: dict[str, list[float]] = {}


def _usage():
    from backend.repositories.commercial_registry import get_commercial_stores

    return get_commercial_stores().usage


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _uid() -> str:
    return f"usage_{uuid.uuid4().hex[:12]}"


def reset_usage() -> None:
    global _RATE_BUCKETS
    _usage().clear()
    _RATE_BUCKETS = {}


def record_usage(
    metric: UsageMetric | str,
    quantity: float = 1.0,
    *,
    organization_id: str,
    workspace_id: str = "",
    user_id: str = "",
    unit: str = "count",
    metadata: dict[str, Any] | None = None,
) -> UsageRecord:
    m = metric if isinstance(metric, UsageMetric) else UsageMetric(str(metric))
    try:
        from backend.services.subscription_service import SubscriptionError, check_quota

        check_quota(organization_id, m, additional=float(quantity))
    except SubscriptionError:
        raise
    except Exception:
        pass
    record = UsageRecord(
        record_id=_uid(),
        organization_id=organization_id,
        workspace_id=workspace_id,
        user_id=user_id,
        metric=m,
        quantity=float(quantity),
        unit=unit,
        recorded_at=_now_iso(),
        metadata=dict(metadata or {}),
    )
    _usage().add(record)
    return record


def list_usage(
    *,
    organization_id: str | None = None,
    workspace_id: str | None = None,
    user_id: str | None = None,
    metric: str | None = None,
) -> list[UsageRecord]:
    return _usage().list(
        organization_id=organization_id,
        workspace_id=workspace_id,
        user_id=user_id,
        metric=metric,
    )


def aggregate_usage(
    *,
    organization_id: str,
    workspace_id: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
) -> dict[str, float]:
    items = list_usage(organization_id=organization_id, workspace_id=workspace_id or None)
    totals: dict[str, float] = {}
    for record in items:
        if period_start and record.recorded_at < period_start:
            continue
        if period_end and record.recorded_at > period_end:
            continue
        key = record.metric.value if hasattr(record.metric, "value") else str(record.metric)
        totals[key] = totals.get(key, 0.0) + record.quantity
    return totals


def usage_summary(organization_id: str, *, workspace_id: str = "") -> dict[str, Any]:
    totals = aggregate_usage(organization_id=organization_id, workspace_id=workspace_id or None)
    return {
        "organization_id": organization_id,
        "workspace_id": workspace_id or None,
        "totals": totals,
        "record_count": len(list_usage(organization_id=organization_id, workspace_id=workspace_id or None)),
    }


def track_ai_request(*, organization_id: str, workspace_id: str = "", user_id: str = "", tokens: int = 0) -> None:
    record_usage(UsageMetric.ai_requests, 1, organization_id=organization_id, workspace_id=workspace_id, user_id=user_id)
    if tokens:
        record_usage(UsageMetric.tokens, tokens, organization_id=organization_id, workspace_id=workspace_id, user_id=user_id, unit="tokens")


def track_workflow(*, organization_id: str, workspace_id: str = "", user_id: str = "") -> None:
    record_usage(UsageMetric.workflow_executions, 1, organization_id=organization_id, workspace_id=workspace_id, user_id=user_id)


def track_storage(*, organization_id: str, bytes_count: float, workspace_id: str = "") -> None:
    record_usage(UsageMetric.storage_bytes, bytes_count, organization_id=organization_id, workspace_id=workspace_id, unit="bytes")


def track_api_request(*, organization_id: str, workspace_id: str = "", user_id: str = "") -> None:
    record_usage(UsageMetric.api_requests, 1, organization_id=organization_id, workspace_id=workspace_id, user_id=user_id)
