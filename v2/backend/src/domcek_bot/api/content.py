"""Manual-event and INFO-announcement administration endpoints."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict

from domcek_bot.api.dependencies import (
    AuthContext,
    authenticated_context,
    csrf_context,
    services,
)
from domcek_bot.api.errors import ApplicationError
from domcek_bot.application.auth.authorization import AuthorizationDenied
from domcek_bot.application.editor.content import (
    ContentConflict,
    ContentObjectNotFound,
    ContentValidationError,
    CreateInfoAnnouncement,
    CreateManualEvent,
    InfoAnnouncementValues,
    ManualEventValues,
    UpdateInfoAnnouncement,
    UpdateManualEvent,
)
from domcek_bot.application.records import InfoAnnouncementRecord, ManualEventRecord

router = APIRouter(prefix="/api/v1")


class ManualEventBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    is_all_day: bool
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    timezone: str = "Europe/Bratislava"
    description: str | None = None
    link_url: str | None = None
    active: bool = True

    def values(self) -> ManualEventValues:
        return ManualEventValues(**self.model_dump())


class ManualEventUpdateBody(ManualEventBody):
    expected_version: int

    def values(self) -> ManualEventValues:
        return ManualEventValues(**self.model_dump(exclude={"expected_version"}))


class InfoAnnouncementBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: str
    valid_from: date
    valid_until: date
    link_url: str | None = None
    image_url: str | None = None
    active: bool = True

    def values(self) -> InfoAnnouncementValues:
        return InfoAnnouncementValues(**self.model_dump())


class InfoAnnouncementUpdateBody(InfoAnnouncementBody):
    expected_version: int

    def values(self) -> InfoAnnouncementValues:
        return InfoAnnouncementValues(**self.model_dump(exclude={"expected_version"}))


@router.get("/manual-events")
async def list_manual_events(
    request: Request,
    context: Annotated[AuthContext, Depends(authenticated_context)],
) -> list[dict[str, object]]:
    try:
        records = await services(request).content_editor.list_manual(principal=context.principal)
    except AuthorizationDenied as exc:
        raise _content_error(exc) from exc
    return [_manual_json(record) for record in records]


@router.post("/manual-events", status_code=201)
async def create_manual_event(
    body: ManualEventBody,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> dict[str, object]:
    try:
        result = await services(request).content_editor.create_manual(
            CreateManualEvent(body.values()),
            principal=context.principal,
            correlation_id=str(request.state.correlation_id),
        )
    except (ContentValidationError, AuthorizationDenied) as exc:
        raise _content_error(exc) from exc
    return _manual_json(result)


@router.put("/manual-events/{event_id}")
async def update_manual_event(
    event_id: uuid.UUID,
    body: ManualEventUpdateBody,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> dict[str, object]:
    try:
        result = await services(request).content_editor.update_manual(
            UpdateManualEvent(event_id, body.expected_version, body.values()),
            principal=context.principal,
            correlation_id=str(request.state.correlation_id),
        )
    except (
        ContentValidationError,
        ContentObjectNotFound,
        ContentConflict,
        AuthorizationDenied,
    ) as exc:
        raise _content_error(exc) from exc
    return _manual_json(result)


@router.delete("/manual-events/{event_id}")
async def delete_manual_event(
    event_id: uuid.UUID,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
    expected_version: Annotated[int, Query(ge=1)],
) -> dict[str, object]:
    try:
        result = await services(request).content_editor.delete_manual(
            event_id,
            expected_version,
            principal=context.principal,
            correlation_id=str(request.state.correlation_id),
        )
    except (
        ContentValidationError,
        ContentObjectNotFound,
        ContentConflict,
        AuthorizationDenied,
    ) as exc:
        raise _content_error(exc) from exc
    return _manual_json(result)


@router.get("/info-announcements")
async def list_info_announcements(
    request: Request,
    context: Annotated[AuthContext, Depends(authenticated_context)],
) -> list[dict[str, object]]:
    try:
        records = await services(request).content_editor.list_info(principal=context.principal)
    except AuthorizationDenied as exc:
        raise _content_error(exc) from exc
    return [_info_json(record) for record in records]


@router.post("/info-announcements", status_code=201)
async def create_info_announcement(
    body: InfoAnnouncementBody,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> dict[str, object]:
    try:
        result = await services(request).content_editor.create_info(
            CreateInfoAnnouncement(body.values()),
            principal=context.principal,
            correlation_id=str(request.state.correlation_id),
        )
    except (ContentValidationError, AuthorizationDenied) as exc:
        raise _content_error(exc) from exc
    return _info_json(result)


@router.put("/info-announcements/{announcement_id}")
async def update_info_announcement(
    announcement_id: uuid.UUID,
    body: InfoAnnouncementUpdateBody,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> dict[str, object]:
    try:
        result = await services(request).content_editor.update_info(
            UpdateInfoAnnouncement(announcement_id, body.expected_version, body.values()),
            principal=context.principal,
            correlation_id=str(request.state.correlation_id),
        )
    except (
        ContentValidationError,
        ContentObjectNotFound,
        ContentConflict,
        AuthorizationDenied,
    ) as exc:
        raise _content_error(exc) from exc
    return _info_json(result)


@router.delete("/info-announcements/{announcement_id}")
async def delete_info_announcement(
    announcement_id: uuid.UUID,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
    expected_version: Annotated[int, Query(ge=1)],
) -> dict[str, object]:
    try:
        result = await services(request).content_editor.delete_info(
            announcement_id,
            expected_version,
            principal=context.principal,
            correlation_id=str(request.state.correlation_id),
        )
    except (
        ContentValidationError,
        ContentObjectNotFound,
        ContentConflict,
        AuthorizationDenied,
    ) as exc:
        raise _content_error(exc) from exc
    return _info_json(result)


def _content_error(exc: Exception) -> ApplicationError:
    if isinstance(exc, ContentValidationError):
        return ApplicationError(
            "content_validation_failed",
            "Údaje nemožno uložiť",
            str(exc),
            422,
        )
    if isinstance(exc, ContentObjectNotFound):
        return ApplicationError(
            "content_not_found",
            "Záznam sa nenašiel",
            "Záznam neexistuje alebo nepatrí do tohto servera.",
            404,
        )
    if isinstance(exc, ContentConflict):
        current = exc.current
        value = (
            _manual_json(current)
            if isinstance(current, ManualEventRecord)
            else _info_json(current)
            if isinstance(current, InfoAnnouncementRecord)
            else None
        )
        return ApplicationError(
            "version_conflict",
            "Záznam sa medzičasom zmenil",
            "Obnovte aktuálne údaje a vedome zopakujte svoju úpravu.",
            409,
            {"current": value},
        )
    return ApplicationError(
        "forbidden",
        "Prístup bol odmietnutý",
        "Na túto operáciu nemáte oprávnenie.",
        403,
    )


def _manual_json(value: ManualEventRecord) -> dict[str, object]:
    return {
        "id": str(value.id),
        "title": value.title,
        "description": value.description,
        "is_all_day": value.is_all_day,
        "starts_at": value.starts_at.isoformat() if value.starts_at else None,
        "ends_at": value.ends_at.isoformat() if value.ends_at else None,
        "starts_on": value.starts_on.isoformat() if value.starts_on else None,
        "ends_on": value.ends_on.isoformat() if value.ends_on else None,
        "timezone": value.timezone,
        "link_url": value.link_url,
        "active": value.active,
        "deleted_at": value.deleted_at.isoformat() if value.deleted_at else None,
        "version": value.version,
    }


def _info_json(value: InfoAnnouncementRecord) -> dict[str, object]:
    return {
        "id": str(value.id),
        "title": value.title,
        "description": value.description,
        "link_url": value.link_url,
        "image_url": value.image_url,
        "valid_from": value.valid_from.isoformat(),
        "valid_until": value.valid_until.isoformat(),
        "active": value.active,
        "deleted_at": value.deleted_at.isoformat() if value.deleted_at else None,
        "version": value.version,
    }
