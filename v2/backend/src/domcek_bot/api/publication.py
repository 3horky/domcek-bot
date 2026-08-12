"""Read-only publication draft API backed by the shared E4 composer."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from domcek_bot.api.dependencies import (
    AuthContext,
    authenticated_context,
    csrf_context,
    services,
)
from domcek_bot.api.errors import ApplicationError
from domcek_bot.application.auth.authorization import AuthorizationDenied, Capability
from domcek_bot.application.publication.composer import PublicationCompositionError
from domcek_bot.application.publication.engine import (
    PublicationAlreadyRunning,
    PublicationChannelMissing,
    PublicationResult,
)
from domcek_bot.application.publication.history import PublicationHistoryEntry
from domcek_bot.application.publication.manual import (
    InvalidPublishConfirmation,
    ManualPublicationDisabled,
)
from domcek_bot.application.publication.recovery import InvalidReconciliation
from domcek_bot.application.publication.service import PublicationConfigurationNotFound

router = APIRouter(prefix="/api/v1/publication")


class ConfirmPublicationBody(BaseModel):
    confirmation_token: str = Field(min_length=20, max_length=4096)


class ReconcileMessageBody(BaseModel):
    message_position: int = Field(ge=0, le=100)
    discord_message_id: int = Field(gt=0)


class ContinueMessageBody(BaseModel):
    message_position: int = Field(ge=0, le=100)


@router.get("/history", response_class=JSONResponse)
async def publication_history(
    request: Request,
    context: Annotated[AuthContext, Depends(authenticated_context)],
    limit: int = 50,
) -> JSONResponse:
    history = services(request).publication_history
    if history is None:
        raise _history_unavailable()
    try:
        entries = await history.list(context.principal, limit=limit)
    except AuthorizationDenied as exc:
        raise _history_forbidden() from exc
    return JSONResponse([_history_json(entry) for entry in entries])


@router.get("/history/{run_id}", response_class=JSONResponse)
async def publication_history_detail(
    run_id: uuid.UUID,
    request: Request,
    context: Annotated[AuthContext, Depends(authenticated_context)],
) -> JSONResponse:
    history = services(request).publication_history
    if history is None:
        raise _history_unavailable()
    try:
        entry = await history.get(run_id, context.principal)
    except AuthorizationDenied as exc:
        raise _history_forbidden() from exc
    if entry is None:
        raise ApplicationError(
            "publication_not_found",
            "Publikácia sa nenašla",
            "Záznam neexistuje alebo patrí inému Discord serveru.",
            404,
        )
    return JSONResponse(_history_json(entry))


@router.get("/dashboard", response_class=JSONResponse)
async def publication_dashboard(
    request: Request,
    context: Annotated[AuthContext, Depends(authenticated_context)],
) -> JSONResponse:
    history = services(request).publication_history
    if history is None:
        raise _history_unavailable()
    try:
        summary = await history.dashboard(context.principal)
    except AuthorizationDenied as exc:
        raise _history_forbidden() from exc
    except LookupError as exc:
        raise ApplicationError(
            "guild_not_configured",
            "Server nie je nakonfigurovaný",
            "Prevádzkový prehľad zatiaľ nie je dostupný.",
            409,
        ) from exc
    last = summary.last_publication
    return JSONResponse(
        {
            "automatic_publication_enabled": summary.automatic_publication_enabled,
            "last_calendar_sync_at": _iso(summary.last_calendar_sync_at),
            "pending_archive_count": summary.pending_archive_count,
            "discord_places_configured": summary.discord_places_configured,
            "active_calendars": [
                {
                    "id": str(calendar.id),
                    "display_name": calendar.display_name,
                    "sync_status": calendar.sync_status,
                    "freshness": calendar.freshness.value,
                    "last_sync_success_at": _iso(calendar.last_sync_success_at),
                    "last_sync_error": calendar.last_sync_error,
                }
                for calendar in summary.active_calendars
            ],
            "last_publication": None
            if last is None
            else {
                "id": str(last.id),
                "scheduled_for": last.scheduled_for.isoformat(),
                "completed_at": _iso(last.completed_at),
                "state": last.state.value,
                "mode": last.mode.value,
            },
        }
    )


@router.get("/shadow-history", response_class=JSONResponse)
async def publication_shadow_history(
    request: Request,
    context: Annotated[AuthContext, Depends(authenticated_context)],
    limit: int = 20,
) -> JSONResponse:
    shadow = services(request).shadow_publications
    if shadow is None:
        raise _history_unavailable()
    try:
        captures = await shadow.list(context.principal, limit=limit)
    except AuthorizationDenied as exc:
        raise _history_forbidden() from exc
    return JSONResponse(
        [
            {
                "id": str(capture.id),
                "slot_key": capture.slot_key,
                "scheduled_for": capture.scheduled_for.isoformat(),
                "first_observed_at": capture.first_observed_at.isoformat(),
                "last_observed_at": capture.last_observed_at.isoformat(),
                "observation_count": capture.observation_count,
                "draft_sha256": capture.draft_sha256,
                "item_count": capture.item_count,
                "message_count": capture.message_count,
                "calendar_sync_valid": capture.calendar_sync_valid,
                "calendar_sync_evidence": capture.calendar_sync_evidence,
                "warning_codes": list(capture.warning_codes),
                "draft": capture.draft_json,
            }
            for capture in captures
        ]
    )


@router.get("/draft", response_class=JSONResponse)
async def publication_draft(
    request: Request,
    context: Annotated[AuthContext, Depends(authenticated_context)],
) -> JSONResponse:
    try:
        context.principal.require(Capability.VIEW_ADMIN)
        draft = await services(request).publication_drafts.compose_next(
            context.principal.guild_id,
            reference_time=datetime.now(UTC),
            intro_text="Ahojte, prinášame prehľad udalostí na najbližšie dva týždne.",
        )
    except AuthorizationDenied as exc:
        raise ApplicationError(
            "forbidden",
            "Prístup bol odmietnutý",
            "Na zobrazenie najbližších oznamov nemáte oprávnenie.",
            403,
        ) from exc
    except PublicationConfigurationNotFound as exc:
        raise ApplicationError(
            "guild_not_configured",
            "Server nie je nakonfigurovaný",
            "Publikačná konfigurácia servera chýba.",
            409,
        ) from exc
    except PublicationCompositionError as exc:
        raise ApplicationError(
            "draft_invalid",
            "Náhľad sa nepodarilo zostaviť",
            "Niektorý oznam prekračuje publikačné limity alebo nie je platný.",
            422,
        ) from exc
    return JSONResponse(json.loads(draft.canonical_json()))


@router.post("/manual/preview", response_class=JSONResponse)
async def manual_publication_preview(
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> JSONResponse:
    manual = services(request).manual_publications
    if manual is None:
        raise ApplicationError(
            "service_unavailable",
            "Publikovanie nie je pripravené",
            "Služba ručného publikovania momentálne nie je dostupná.",
            503,
        )
    try:
        preview = await manual.preview(principal=context.principal)
    except ManualPublicationDisabled as exc:
        raise _manual_publication_disabled() from exc
    except AuthorizationDenied as exc:
        raise ApplicationError(
            "forbidden",
            "Publikovanie nebolo povolené",
            "Ručne môže publikovať iba Admin alebo SDB / FMA.",
            403,
        ) from exc
    return JSONResponse(
        {
            "slot_key": preview.slot_key,
            "scheduled_for": preview.scheduled_for.isoformat(),
            "announcement_count": preview.announcement_count,
            "message_count": preview.message_count,
            "announcement_channel_id": str(preview.announcement_channel_id),
            "confirmation_token": preview.confirmation_token,
            "expires_at": preview.expires_at.isoformat(),
            "draft": json.loads(preview.draft.canonical_json()),
        }
    )


@router.post("/manual/confirm", response_class=JSONResponse)
async def manual_publication_confirm(
    body: ConfirmPublicationBody,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> JSONResponse:
    manual = services(request).manual_publications
    if manual is None:
        raise ApplicationError(
            "service_unavailable",
            "Publikovanie nie je pripravené",
            "Služba ručného publikovania momentálne nie je dostupná.",
            503,
        )
    try:
        prepared, result = await manual.confirm(
            body.confirmation_token,
            principal=context.principal,
            correlation_id=request.state.correlation_id,
        )
    except ManualPublicationDisabled as exc:
        raise _manual_publication_disabled() from exc
    except AuthorizationDenied as exc:
        raise ApplicationError(
            "forbidden",
            "Publikovanie nebolo povolené",
            "Ručne môže publikovať iba Admin alebo SDB / FMA.",
            403,
        ) from exc
    except InvalidPublishConfirmation as exc:
        raise ApplicationError(
            "publish_confirmation_invalid",
            "Potvrdenie už nie je platné",
            "Načítajte nový náhľad a publikovanie potvrďte znova.",
            409,
        ) from exc
    except PublicationChannelMissing as exc:
        raise ApplicationError(
            "announcement_channel_missing",
            "Chýba cieľový kanál",
            "V nastaveniach vyberte Discord kanál pre oznamy.",
            409,
        ) from exc
    except PublicationAlreadyRunning as exc:
        raise ApplicationError(
            "publication_in_progress",
            "Publikovanie už prebieha",
            "Skontrolujte aktuálny publikačný run alebo recovery incident.",
            409,
        ) from exc
    return JSONResponse(
        {
            "run_id": str(result.run_id),
            "slot_key": prepared.run.slot_key,
            "created": prepared.created,
            "state": result.state.value,
            "message_ids": list(result.sent_message_ids),
            "warning_codes": list(result.warning_codes),
        }
    )


def _manual_publication_disabled() -> ApplicationError:
    return ApplicationError(
        "manual_publication_disabled",
        "Ručné odoslanie je vypnuté",
        "Carlo je v bezpečnostnom režime bez ručného odosielania na Discord.",
        409,
    )


@router.post("/recovery/{run_id}/link-existing", response_class=JSONResponse)
async def link_existing_publication_message(
    run_id: uuid.UUID,
    body: ReconcileMessageBody,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> JSONResponse:
    recovery = services(request).publication_recovery
    if recovery is None:
        raise _recovery_unavailable()
    try:
        result = await recovery.mark_existing_and_continue(
            run_id,
            message_position=body.message_position,
            discord_message_id=body.discord_message_id,
            principal=context.principal,
            correlation_id=request.state.correlation_id,
        )
    except AuthorizationDenied as exc:
        raise _recovery_forbidden() from exc
    except InvalidReconciliation as exc:
        raise _recovery_invalid() from exc
    return _recovery_response(result)


@router.post("/recovery/{run_id}/confirm-not-sent", response_class=JSONResponse)
async def continue_publication_after_confirmation(
    run_id: uuid.UUID,
    body: ContinueMessageBody,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> JSONResponse:
    recovery = services(request).publication_recovery
    if recovery is None:
        raise _recovery_unavailable()
    try:
        result = await recovery.confirm_not_sent_and_continue(
            run_id,
            message_position=body.message_position,
            principal=context.principal,
            correlation_id=request.state.correlation_id,
        )
    except AuthorizationDenied as exc:
        raise _recovery_forbidden() from exc
    except InvalidReconciliation as exc:
        raise _recovery_invalid() from exc
    return _recovery_response(result)


def _recovery_response(result: PublicationResult) -> JSONResponse:
    return JSONResponse(
        {
            "run_id": str(result.run_id),
            "state": result.state.value,
            "message_ids": list(result.sent_message_ids),
            "warning_codes": list(result.warning_codes),
        }
    )


def _recovery_unavailable() -> ApplicationError:
    return ApplicationError(
        "service_unavailable",
        "Recovery nie je pripravené",
        "Služba obnovy publikovania momentálne nie je dostupná.",
        503,
    )


def _recovery_forbidden() -> ApplicationError:
    return ApplicationError(
        "forbidden",
        "Recovery nebolo povolené",
        "Neistý výsledok publikovania môže vyhodnotiť iba Admin.",
        403,
    )


def _recovery_invalid() -> ApplicationError:
    return ApplicationError(
        "reconciliation_invalid",
        "Recovery už nie je možné použiť",
        "Správa už bola vyhodnotená alebo nepatrí k tomuto serveru.",
        409,
    )


def _history_json(entry: PublicationHistoryEntry) -> dict[str, object]:
    run = entry.run
    return {
        "id": str(run.id),
        "slot_key": run.slot_key,
        "scheduled_for": run.scheduled_for.isoformat(),
        "mode": run.mode.value,
        "initiated_by_user_id": str(run.initiated_by_user_id)
        if run.initiated_by_user_id is not None
        else None,
        "state": run.state.value,
        "attempt": run.attempt,
        "composer_version": run.composer_version,
        "intro_text": run.intro_text,
        "intro_prompt_version": run.intro_prompt_version,
        "intro_used_fallback": run.intro_used_fallback,
        "outro_text": run.outro_text,
        "warning_codes": list(run.warning_codes),
        "started_at": _iso(run.started_at),
        "completed_at": _iso(run.completed_at),
        "error_code": run.error_code,
        "error_detail": run.error_detail,
        "items": [
            {
                "id": str(item.id),
                "kind": item.item_type.value,
                "position": item.position,
                "title": item.final_title,
                "description": item.final_description,
                "display_time": item.display_time,
                "day_emoji": item.day_emoji,
                "starts_at": _iso(item.starts_at),
                "ends_at": _iso(item.ends_at),
                "starts_on": item.starts_on.isoformat() if item.starts_on else None,
                "ends_on": item.ends_on.isoformat() if item.ends_on else None,
                "is_all_day": item.is_all_day,
                "link_url": item.link_url,
                "image_url": item.image_url,
            }
            for item in entry.items
        ],
        "messages": [
            {
                "id": str(message.id),
                "position": message.position,
                "discord_channel_id": str(message.discord_channel_id),
                "discord_message_id": str(message.discord_message_id)
                if message.discord_message_id is not None
                else None,
                "jump_url": (
                    f"https://discord.com/channels/{run.guild_id}/{message.discord_channel_id}/"
                    f"{message.discord_message_id}"
                    if message.discord_message_id is not None
                    else None
                ),
                "state": message.state.value,
                "content": message.content,
                "embeds": list(message.embeds),
                "allowed_mentions": list(message.allowed_mentions),
                "seen_target": message.seen_target,
                "attempt_count": message.attempt_count,
                "error_detail": message.error_detail,
                "reaction_error": message.reaction_error,
                "sent_at": _iso(message.sent_at),
            }
            for message in entry.messages
        ],
    }


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _history_unavailable() -> ApplicationError:
    return ApplicationError(
        "service_unavailable",
        "História nie je pripravená",
        "História publikácií momentálne nie je dostupná.",
        503,
    )


def _history_forbidden() -> ApplicationError:
    return ApplicationError(
        "forbidden",
        "História nebola povolená",
        "Na zobrazenie histórie publikácií nemáte oprávnenie.",
        403,
    )
