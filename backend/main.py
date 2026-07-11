import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from backend.api.auth_middleware import AuthContextMiddleware
from backend.api.error_handlers import register_error_handlers
from backend.api.monitoring_middleware import MonitoringMiddleware
from backend.api.routes.admin_routes import router as admin_router
from backend.api.routes.analytics_routes import router as analytics_router
from backend.api.routes.analyst_routes import router as analyst_router
from backend.api.routes.apikey_routes import router as apikey_router
from backend.api.routes.auth_routes import router as auth_router
from backend.api.routes.billing_routes import router as billing_router
from backend.api.routes.branding_routes import router as branding_router
from backend.api.routes.dax_routes import router as dax_router
from backend.api.routes.dataset_routes import router as dataset_router
from backend.api.routes.evaluation_routes import router as evaluation_router
from backend.api.routes.insight_routes import router as insight_router
from backend.api.routes.intelligence_routes import router as intelligence_router
from backend.api.routes.job_routes import router as job_router
from backend.api.routes.knowledge_routes import router as knowledge_router
from backend.api.routes.monitoring_routes import router as monitoring_router
from backend.api.routes.organization_routes import router as organization_router
from backend.api.routes.rbac_routes import router as rbac_router
from backend.api.routes.release_routes import router as release_router
from backend.api.routes.report_routes import router as report_router
from backend.api.routes.sql_lab_routes import router as sql_lab_router
from backend.api.routes.storage_routes import router as storage_router
from backend.api.routes.system_routes import router as system_router
from backend.api.routes.theme_routes import router as theme_router
from backend.api.routes.upload_routes import router as upload_router
from backend.api.routes.visual_builder_routes import router as visual_builder_router
from backend.api.routes.workflow_routes import router as workflow_router
from backend.api.routes.workspace_routes import router as workspace_router
from backend.core.config import ensure_data_directories, settings
from backend.logging import setup_logging
from backend.reliability.shutdown import register_shutdown_hook, run_shutdown
from backend.security.cors_policy import cors_allow_credentials, cors_headers, cors_methods, cors_origins
from backend.security.csrf import CSRFMiddleware
from backend.security.headers_middleware import SecurityHeadersMiddleware
from backend.security.rate_limiter import RateLimitMiddleware


setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # KI-007 — refuse production boot with missing/weak JWT signing secrets
    # KI-006 — refuse production boot with wildcard / missing CORS origins
    from backend.security.cors_policy import assert_production_cors
    from backend.security.secrets_validation import assert_production_secrets

    assert_production_secrets()
    assert_production_cors()
    logger.info("Starting %s v%s", settings.APP_NAME, settings.API_VERSION)
    register_shutdown_hook(lambda: logger.info("Application shutdown hook invoked"))
    yield
    await run_shutdown()


def create_app() -> FastAPI:
    ensure_data_directories()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.API_VERSION,
        description=(
            "Local-first AI Analytics SaaS MVP API. "
            "Sprint 8.7 production hardening. Official release: Data Bot AI v1.0.0."
        ),
        lifespan=lifespan,
    )

    origins = cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=cors_allow_credentials() and "*" not in origins,
        allow_methods=cors_methods(),
        allow_headers=cors_headers(),
    )
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(MonitoringMiddleware)
    app.add_middleware(AuthContextMiddleware)

    register_error_handlers(app)

    @app.get("/health", tags=["Health"])
    def health_check():
        """Legacy health endpoint retained for backward compatibility."""
        return {"status": "ok", "app": settings.APP_NAME, "version": settings.API_VERSION}

    # Existing product routes (unchanged)
    app.include_router(upload_router)
    app.include_router(dataset_router)
    app.include_router(analytics_router)
    app.include_router(insight_router)
    app.include_router(intelligence_router)
    app.include_router(visual_builder_router)
    app.include_router(report_router)
    app.include_router(theme_router)
    app.include_router(branding_router)
    app.include_router(sql_lab_router)
    app.include_router(dax_router)

    # Sprint 7.8 — production API gateway (/api/v1)
    app.include_router(system_router)
    app.include_router(analyst_router)
    app.include_router(workflow_router)
    app.include_router(evaluation_router)
    app.include_router(knowledge_router)

    # Sprint 8.0 — authentication & platform identity (/api/v1/auth)
    app.include_router(auth_router)

    # Sprint 8.1 — organizations, workspaces, RBAC
    app.include_router(organization_router)
    app.include_router(workspace_router)
    app.include_router(rbac_router)

    # Sprint 8.3 — async jobs / background execution
    app.include_router(job_router)

    # Sprint 8.4 — dataset persistence, object storage & file lifecycle
    app.include_router(storage_router)

    # Sprint 8.5 — monitoring, health, metrics, system status
    app.include_router(monitoring_router)

    # Sprint 8.6 — commercial platform (billing, API keys, admin)
    app.include_router(billing_router)
    app.include_router(apikey_router)
    app.include_router(admin_router)

    # Sprint 8.7 — release candidate validation & benchmarks
    app.include_router(release_router)

    return app


app = create_app()
