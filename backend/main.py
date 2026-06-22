import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes.analytics_routes import router as analytics_router
from backend.api.routes.branding_routes import router as branding_router
from backend.api.routes.dax_routes import router as dax_router
from backend.api.routes.dataset_routes import router as dataset_router
from backend.api.routes.insight_routes import router as insight_router
from backend.api.routes.intelligence_routes import router as intelligence_router
from backend.api.routes.report_routes import router as report_router
from backend.api.routes.sql_lab_routes import router as sql_lab_router
from backend.api.routes.theme_routes import router as theme_router
from backend.api.routes.upload_routes import router as upload_router
from backend.api.routes.visual_builder_routes import router as visual_builder_router
from backend.core.config import ensure_data_directories, settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


def create_app() -> FastAPI:
    ensure_data_directories()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.API_VERSION,
        description="Local-first AI Analytics SaaS MVP API",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["Health"])
    def health_check():
        return {"status": "ok", "app": settings.APP_NAME, "version": settings.API_VERSION}

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

    return app


app = create_app()
