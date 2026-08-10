"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from domcek_bot.api.admin import router as admin_router
from domcek_bot.api.audit import router as audit_router
from domcek_bot.api.auth import router as auth_router
from domcek_bot.api.content import router as content_router
from domcek_bot.api.dependencies import ApiServices
from domcek_bot.api.editor import router as editor_router
from domcek_bot.api.errors import install_error_handlers
from domcek_bot.api.health import router as health_router
from domcek_bot.api.media import public_router as public_media_router
from domcek_bot.api.media import upload_router as media_upload_router
from domcek_bot.api.middleware import (
    CorrelationIdMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from domcek_bot.api.operations import router as operations_router
from domcek_bot.api.publication import router as publication_router
from domcek_bot.config import ProcessKind, Settings, load_settings
from domcek_bot.infrastructure.database import Database, DatabaseProtocol
from domcek_bot.logging import configure_logging

logger = structlog.get_logger(__name__)


def create_app(
    *,
    settings: Settings | None = None,
    database: DatabaseProtocol | None = None,
    services: ApiServices | None = None,
    startup: Callable[[], Awaitable[None]] | None = None,
) -> FastAPI:
    resolved_settings = settings or load_settings(ProcessKind.API)
    configure_logging(resolved_settings, ProcessKind.API.value)
    resolved_database = database or Database(resolved_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if startup is not None:
            await startup()
        await logger.ainfo("api_started")
        try:
            yield
        finally:
            if services is not None:
                await services.close()
            await resolved_database.close()
            await logger.ainfo("api_stopped")

    app = FastAPI(
        title="Carlo API",
        version=resolved_settings.app_version,
        docs_url="/api/docs" if resolved_settings.app_env.value != "production" else None,
        openapi_url="/api/openapi.json"
        if resolved_settings.app_env.value != "production"
        else None,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.database = resolved_database
    app.state.services = services
    app.add_middleware(
        RateLimitMiddleware,
        window_seconds=resolved_settings.api_rate_limit_window_seconds,
        oauth_limit=resolved_settings.api_oauth_rate_limit,
        mutation_limit=resolved_settings.api_mutation_rate_limit,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.allowed_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-Correlation-ID", "X-CSRF-Token"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    install_error_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(audit_router)
    app.include_router(content_router)
    app.include_router(media_upload_router)
    app.include_router(public_media_router)
    app.include_router(editor_router)
    app.include_router(publication_router)
    app.include_router(operations_router)
    app.include_router(admin_router)
    return app
