"""Liveness and dependency-aware readiness endpoints."""

from __future__ import annotations

from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from domcek_bot.config import Settings
from domcek_bot.infrastructure.database import DatabaseProtocol, DatabaseUnavailableError

router = APIRouter(prefix="/health", tags=["health"])


class LivenessResponse(BaseModel):
    status: Literal["alive"]
    version: str
    environment: str


class DependencyStatus(BaseModel):
    status: Literal["healthy", "unhealthy"]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    dependencies: dict[str, DependencyStatus]


def get_database(request: Request) -> DatabaseProtocol:
    return cast(DatabaseProtocol, request.app.state.database)


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


@router.get("/live", response_model=LivenessResponse)
async def liveness(settings: Annotated[Settings, Depends(get_settings)]) -> LivenessResponse:
    return LivenessResponse(
        status="alive",
        version=settings.app_version,
        environment=settings.app_env.value,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
)
async def readiness(
    database: Annotated[DatabaseProtocol, Depends(get_database)],
) -> ReadinessResponse | JSONResponse:
    try:
        await database.ping()
    except DatabaseUnavailableError:
        response = ReadinessResponse(
            status="not_ready",
            dependencies={"database": DependencyStatus(status="unhealthy")},
        )
        return JSONResponse(status_code=503, content=response.model_dump())
    return ReadinessResponse(
        status="ready",
        dependencies={"database": DependencyStatus(status="healthy")},
    )
