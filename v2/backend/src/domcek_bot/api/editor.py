"""Versioned editorial write endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from domcek_bot.api.dependencies import AuthContext, csrf_context, services
from domcek_bot.api.errors import ApplicationError
from domcek_bot.application.auth.authorization import AuthorizationDenied
from domcek_bot.application.editor.events import (
    EditorialConflict,
    EditorialObjectNotFound,
    EditorialValidationError,
    SeriesEditorialConflict,
    UpdateEventOverride,
    UpdateSeriesOverride,
)
from domcek_bot.application.records import EventOverrideRecord, EventSeriesOverrideRecord
from domcek_bot.domain.enums import DescriptionState, InclusionDecision

router = APIRouter(prefix="/api/v1/events")


class EventOverrideUpdateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=0)
    public_title: str | None = None
    description_state: DescriptionState = DescriptionState.INHERIT
    public_description: str | None = None
    inclusion_decision: InclusionDecision | None = None


@router.put("/{event_id}/override")
async def update_event_override(
    event_id: uuid.UUID,
    body: EventOverrideUpdateBody,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> dict[str, object]:
    try:
        result = await services(request).event_editor.update_instance(
            UpdateEventOverride(
                event_id=event_id,
                expected_version=body.expected_version,
                public_title=body.public_title,
                description_state=body.description_state,
                public_description=body.public_description,
                inclusion_decision=body.inclusion_decision,
            ),
            principal=context.principal,
            correlation_id=str(request.state.correlation_id),
        )
    except EditorialValidationError as exc:
        raise ApplicationError(
            "editorial_validation_failed",
            "Úpravu nemožno uložiť",
            str(exc),
            422,
        ) from exc
    except EditorialObjectNotFound as exc:
        raise ApplicationError(
            "event_not_found",
            "Udalosť sa nenašla",
            "Udalosť neexistuje alebo nepatrí do tohto servera.",
            404,
        ) from exc
    except AuthorizationDenied as exc:
        raise ApplicationError(
            "forbidden",
            "Prístup bol odmietnutý",
            "Na túto úpravu nemáte oprávnenie.",
            403,
        ) from exc
    except EditorialConflict as exc:
        raise ApplicationError(
            "version_conflict",
            "Udalosť sa medzičasom zmenila",
            "Obnovte aktuálne údaje a vedome zopakujte svoju úpravu.",
            409,
            {"current": _override_json(exc.current)},
        ) from exc
    return _override_json(result) or {}


def _override_json(value: EventOverrideRecord | None) -> dict[str, object] | None:
    if value is None:
        return None
    return {
        "event_id": str(value.external_event_id),
        "public_title": value.public_title,
        "description_state": value.description_state.value,
        "public_description": value.public_description,
        "inclusion_decision": value.inclusion_decision.value,
        "version": value.version,
    }


@router.put("/{event_id}/series-override")
async def update_series_override(
    event_id: uuid.UUID,
    body: EventOverrideUpdateBody,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> dict[str, object]:
    if body.inclusion_decision is not None:
        raise ApplicationError(
            "editorial_validation_failed",
            "Úpravu nemožno uložiť",
            "Rozhodnutie o zaradení sa viaže iba na konkrétny výskyt.",
            422,
        )
    try:
        result = await services(request).event_editor.update_series(
            UpdateSeriesOverride(
                event_id=event_id,
                expected_version=body.expected_version,
                public_title=body.public_title,
                description_state=body.description_state,
                public_description=body.public_description,
            ),
            principal=context.principal,
            correlation_id=str(request.state.correlation_id),
        )
    except EditorialValidationError as exc:
        raise ApplicationError(
            "editorial_validation_failed", "Úpravu nemožno uložiť", str(exc), 422
        ) from exc
    except EditorialObjectNotFound as exc:
        raise ApplicationError(
            "event_not_found",
            "Udalosť sa nenašla",
            "Udalosť neexistuje alebo nepatrí do tohto servera.",
            404,
        ) from exc
    except AuthorizationDenied as exc:
        raise ApplicationError(
            "forbidden",
            "Prístup bol odmietnutý",
            "Na túto úpravu nemáte oprávnenie.",
            403,
        ) from exc
    except SeriesEditorialConflict as exc:
        raise ApplicationError(
            "version_conflict",
            "Pravidlo série sa medzičasom zmenilo",
            "Obnovte aktuálne údaje a vedome zopakujte svoju úpravu.",
            409,
            {"current": _series_json(exc.current)},
        ) from exc
    return _series_json(result) or {}


def _series_json(value: EventSeriesOverrideRecord | None) -> dict[str, object] | None:
    if value is None:
        return None
    return {
        "id": str(value.id),
        "calendar_source_id": str(value.calendar_source_id),
        "series_key": value.series_key,
        "effective_from_key": value.effective_from_key,
        "effective_all_day": value.effective_all_day,
        "effective_from_at": (
            value.effective_from_at.isoformat() if value.effective_from_at else None
        ),
        "effective_from_date": (
            value.effective_from_date.isoformat() if value.effective_from_date else None
        ),
        "public_title": value.public_title,
        "description_state": value.description_state.value,
        "public_description": value.public_description,
        "version": value.version,
    }
