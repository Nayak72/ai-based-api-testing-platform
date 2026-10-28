from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    auth,
    catalog,
    kb,
    providers,
    quick_test,
    reports,
    runs,
    sessions,
    specs,
    test_cases,
)
from app.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.db.mongo import close_mongo_connection, connect_to_mongo, create_indexes


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger = structlog.get_logger()
    logger.info("Starting up...")
    await connect_to_mongo()
    await create_indexes()
    yield
    logger.info("Shutting down...")
    await close_mongo_connection()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(specs.router, prefix="/api/v1/specs", tags=["specs"])
    app.include_router(test_cases.router, prefix="/api/v1/specs", tags=["test-cases"])
    app.include_router(runs.router, prefix="/api/v1/runs", tags=["runs"])
    app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
    app.include_router(providers.router, prefix="/api/v1/providers", tags=["providers"])
    app.include_router(catalog.router, prefix="/api/v1/catalog", tags=["catalog"])
    app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
    app.include_router(kb.router, prefix="/api/v1/kb", tags=["knowledge-base"])
    app.include_router(quick_test.router, prefix="/api/v1/quick-test", tags=["quick-test"])

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": settings.app_version}

    return app


app = create_app()
