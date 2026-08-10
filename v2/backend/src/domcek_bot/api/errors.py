"""Stable mapping of application errors to user-safe HTTP problem responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class ApplicationError(Exception):
    code: str
    title: str
    detail: str
    status_code: int = 400
    extensions: dict[str, Any] = field(default_factory=dict)


def problem_response(
    *,
    status_code: int,
    code: str,
    title: str,
    detail: str,
    correlation_id: str,
    extensions: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        media_type="application/problem+json; charset=utf-8",
        content={
            "type": f"https://domcek.invalid/problems/{code}",
            "title": title,
            "status": status_code,
            "detail": detail,
            "code": code,
            "correlation_id": correlation_id,
            **(extensions or {}),
        },
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def handle_application_error(request: Request, exc: ApplicationError) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        await logger.awarning(
            "application_error",
            error_code=exc.code,
            status_code=exc.status_code,
            correlation_id=correlation_id,
        )
        return problem_response(
            status_code=exc.status_code,
            code=exc.code,
            title=exc.title,
            detail=exc.detail,
            correlation_id=correlation_id,
            extensions=exc.extensions,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        del exc
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        await logger.awarning(
            "request_validation_failed",
            correlation_id=correlation_id,
        )
        return problem_response(
            status_code=422,
            code="request_validation_failed",
            title="Požiadavka nie je platná",
            detail="Skontrolujte povinné polia a formát odoslaných údajov.",
            correlation_id=correlation_id,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        code = "not_found" if exc.status_code == 404 else "http_error"
        title = "Cesta sa nenašla" if exc.status_code == 404 else "Požiadavku nemožno vykonať"
        return problem_response(
            status_code=exc.status_code,
            code=code,
            title=title,
            detail="Požadovaná operácia nie je dostupná.",
            correlation_id=correlation_id,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        await logger.aexception(
            "unexpected_error",
            correlation_id=correlation_id,
            exc_info=exc,
        )
        return problem_response(
            status_code=500,
            code="internal_error",
            title="Interná chyba",
            detail="Požiadavku sa nepodarilo bezpečne spracovať.",
            correlation_id=correlation_id,
        )
