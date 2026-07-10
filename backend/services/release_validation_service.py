from __future__ import annotations

"""Production validation checks (Sprint 8.7)."""

from typing import Any

from backend.security.cors_policy import validate_cors_config
from backend.security.dependency_audit import audit_dependencies
from backend.security.secrets_validation import validate_secrets


def _check(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "ok": ok, "detail": detail}


def validate_production_readiness() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    # Authentication
    try:
        from backend.services import auth_service

        checks.append(_check("authentication", hasattr(auth_service, "authenticate_user")))
    except Exception as exc:
        checks.append(_check("authentication", False, str(exc)))

    # RBAC
    try:
        from backend.services import rbac_service

        checks.append(_check("rbac", hasattr(rbac_service, "has_permission")))
    except Exception as exc:
        checks.append(_check("rbac", False, str(exc)))

    # Organizations
    try:
        from backend.services import organization_service

        checks.append(_check("organizations", hasattr(organization_service, "create_organization")))
    except Exception as exc:
        checks.append(_check("organizations", False, str(exc)))

    # Storage
    try:
        from backend.services import storage_service

        checks.append(_check("storage", hasattr(storage_service, "upload")))
    except Exception as exc:
        checks.append(_check("storage", False, str(exc)))

    # Workflow / AI runtime
    try:
        from backend.services import workflow_engine_service

        checks.append(_check("workflow", hasattr(workflow_engine_service, "execute_workflow")))
    except Exception as exc:
        checks.append(_check("workflow", False, str(exc)))

    try:
        from backend.services import evaluation_service

        checks.append(_check("evaluation", hasattr(evaluation_service, "evaluate_session")))
    except Exception as exc:
        checks.append(_check("evaluation", False, str(exc)))

    # Jobs
    try:
        from backend.services import job_service

        checks.append(_check("jobs", hasattr(job_service, "submit_job")))
    except Exception as exc:
        checks.append(_check("jobs", False, str(exc)))

    # Monitoring
    try:
        from backend.monitoring.health import health_report

        report = health_report()
        checks.append(_check("monitoring", report.get("status") in ("ok", "degraded", "healthy")))
    except Exception as exc:
        checks.append(_check("monitoring", False, str(exc)))

    # Billing
    try:
        from backend.services import billing_service, subscription_service

        checks.append(
            _check(
                "billing",
                hasattr(billing_service, "generate_invoice")
                and hasattr(subscription_service, "list_plans"),
            )
        )
    except Exception as exc:
        checks.append(_check("billing", False, str(exc)))

    # API keys
    try:
        from backend.services import api_key_service

        checks.append(_check("api_keys", hasattr(api_key_service, "create_key")))
    except Exception as exc:
        checks.append(_check("api_keys", False, str(exc)))

    secrets = validate_secrets()
    checks.append(_check("secrets", secrets["ok"], "; ".join(secrets["issues"])))

    cors_issues = validate_cors_config()
    checks.append(_check("cors_policy", len(cors_issues) == 0, "; ".join(cors_issues)))

    dep = audit_dependencies()
    checks.append(
        _check(
            "dependency_audit",
            len(dep["issues"]) == 0,
            "; ".join(dep["issues"]),
        )
    )

    passed = sum(1 for c in checks if c["ok"])
    return {
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "ok": passed == len(checks),
    }
