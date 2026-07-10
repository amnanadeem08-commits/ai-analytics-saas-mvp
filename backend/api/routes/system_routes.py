from __future__ import annotations

from fastapi import APIRouter

from backend.api.dependencies import (
    get_evaluation_service,
    get_knowledge_ingestion,
    get_llm_service,
    get_memory_service,
    get_workflow_engine,
)
from backend.api.models.system import CapabilitiesResponse, HealthResponse, VersionResponse
from backend.core.config import settings

router = APIRouter(prefix="/api/v1", tags=["System"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="API health check",
    description="Returns API status, version, and lightweight service availability probes.",
    responses={200: {"description": "Healthy"}},
)
def health() -> HealthResponse:
    services: dict[str, str] = {}
    try:
        get_workflow_engine()
        services["workflow_engine"] = "available"
    except Exception:
        services["workflow_engine"] = "unavailable"
    try:
        get_llm_service().get_llm_provider()
        services["llm"] = "available"
    except Exception:
        services["llm"] = "unavailable"
    try:
        get_memory_service().get_memory_store()
        services["memory"] = "available"
    except Exception:
        services["memory"] = "unavailable"
    try:
        get_knowledge_ingestion().knowledge_summary()
        services["knowledge"] = "available"
    except Exception:
        services["knowledge"] = "unavailable"
    try:
        get_evaluation_service()
        services["evaluation"] = "available"
    except Exception:
        services["evaluation"] = "unavailable"
    # Sprint 8.2 — report database health only when a persistent backend is configured.
    try:
        from backend.database.config import get_database_config

        if get_database_config().uses_database:
            from backend.database.database import health_check as db_health

            services["database"] = "available" if db_health().get("connected") else "unavailable"
    except Exception:
        services["database"] = "unavailable"

    overall = "ok" if all(v == "available" for v in services.values()) else "degraded"
    return HealthResponse(
        status=overall,
        app=settings.APP_NAME,
        version=settings.API_VERSION,
        api_gateway="v1",
        services=services,
    )


@router.get(
    "/version",
    response_model=VersionResponse,
    summary="API version",
    description="Returns application and schema version metadata.",
    responses={200: {"description": "Version info"}},
)
def version() -> VersionResponse:
    schema_versions: dict[str, str] = {}
    try:
        from backend.models.analyst_models import ANALYST_RUNTIME_SCHEMA_VERSION

        schema_versions["analyst_runtime"] = ANALYST_RUNTIME_SCHEMA_VERSION
    except Exception:
        pass
    try:
        from backend.models.evaluation_models import EVALUATION_SCHEMA_VERSION

        schema_versions["evaluation"] = EVALUATION_SCHEMA_VERSION
    except Exception:
        pass
    try:
        from backend.models.workflow_models import WORKFLOW_SCHEMA_VERSION

        schema_versions["workflow"] = WORKFLOW_SCHEMA_VERSION
    except Exception:
        pass
    try:
        from backend.models.rag_models import RAG_SCHEMA_VERSION

        schema_versions["rag"] = RAG_SCHEMA_VERSION
    except Exception:
        pass
    return VersionResponse(
        app=settings.APP_NAME,
        version=settings.API_VERSION,
        api_gateway="v1",
        schema_versions=schema_versions,
    )


@router.get(
    "/capabilities",
    response_model=CapabilitiesResponse,
    summary="List AI Analyst capabilities",
    description="Enumerates supported AI Analyst / intelligence capabilities from the current backend.",
    responses={200: {"description": "Capabilities list"}},
)
def capabilities() -> CapabilitiesResponse:
    engine = get_workflow_engine()
    llm = get_llm_service()
    runners = sorted(engine.DEFAULT_STAGE_RUNNERS.keys())
    providers = ["mock", *list(getattr(llm, "FUTURE_LLM_PROVIDERS", ()))]
    caps = [
        "ai_analyst_runtime",
        "workflow_execution",
        "agent_planning",
        "tool_calling",
        "memory_context",
        "rag_retrieval",
        "knowledge_ingestion",
        "llm_providers",
        "structured_generation",
        "evaluation_framework",
        "forecast_governance",
        "session_management",
        "authentication",
    ]
    return CapabilitiesResponse(
        success=True,
        capabilities=caps,
        workflow_runners=runners,
        llm_providers=providers,
        details={
            "api_gateway": "v1",
            "auth": False,
            "streaming": False,
            "websockets": False,
        },
    )
