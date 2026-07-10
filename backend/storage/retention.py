from __future__ import annotations

"""Retention policy evaluation (Sprint 8.4)."""

from datetime import datetime, timezone

from backend.models.storage_models import RetentionPolicy, StorageObject, StorageObjectStatus


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _days_since(iso_timestamp: str) -> float | None:
    dt = _parse_iso(iso_timestamp)
    if dt is None:
        return None
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).total_seconds() / 86400.0


def evaluate_retention(obj: StorageObject, policy: RetentionPolicy | None = None) -> dict[str, object]:
    """Evaluate retention policy and return recommended actions."""
    pol = policy or obj.retention_policy
    actions: list[str] = []
    reasons: list[str] = []

    if obj.status == StorageObjectStatus.deleted:
        return {"object_id": obj.object_id, "actions": actions, "reasons": reasons, "eligible": False}

    if pol.ttl_days is not None:
        age = _days_since(obj.created_at)
        if age is not None and age > pol.ttl_days:
            actions.append("delete")
            reasons.append(f"Object age {age:.1f}d exceeds ttl_days={pol.ttl_days}")

    if pol.archive_after_days is not None and obj.status == StorageObjectStatus.active:
        age = _days_since(obj.created_at)
        if age is not None and age > pol.archive_after_days:
            actions.append("archive")
            reasons.append(f"Object age {age:.1f}d exceeds archive_after_days={pol.archive_after_days}")

    if pol.delete_archived_after_days is not None and obj.status == StorageObjectStatus.archived:
        age = _days_since(obj.archived_at or obj.updated_at)
        if age is not None and age > pol.delete_archived_after_days:
            actions.append("delete")
            reasons.append(
                f"Archived object age {age:.1f}d exceeds delete_archived_after_days={pol.delete_archived_after_days}"
            )

    version_count = len(obj.versions)
    if pol.max_versions and version_count > pol.max_versions:
        actions.append("trim_versions")
        reasons.append(f"Version count {version_count} exceeds max_versions={pol.max_versions}")

    return {
        "object_id": obj.object_id,
        "actions": actions,
        "reasons": reasons,
        "eligible": bool(actions),
        "version_count": version_count,
        "max_versions": pol.max_versions,
    }


def validate_metadata(
    *,
    name: str,
    artifact_type: str,
    owner_id: str = "",
    organization_id: str = "",
    workspace_id: str = "",
) -> dict[str, object]:
    """Validate required metadata fields."""
    issues: list[str] = []
    if not str(name or "").strip():
        issues.append("Missing name")
    if not str(artifact_type or "").strip():
        issues.append("Missing artifact_type")
    # Owner/org/workspace are optional in MVP but tracked when provided.
    _ = owner_id, organization_id, workspace_id
    return {"valid": not issues, "issues": issues}
