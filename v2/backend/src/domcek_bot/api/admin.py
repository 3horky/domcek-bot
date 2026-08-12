"""Unified E9 web administration API."""

from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import time
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from domcek_bot.api.dependencies import AuthContext, authenticated_context, csrf_context, services
from domcek_bot.api.errors import ApplicationError
from domcek_bot.application.auth.authorization import AuthorizationDenied, Capability
from domcek_bot.application.channels import (
    ArchiveDecisionConflict,
    ChannelOperationError,
)
from domcek_bot.application.discord_admin import (
    DiscordAdministrationError,
    DiscordChannelOption,
    DiscordEmojiOption,
    DiscordRoleOption,
    LastAdminRemovalDenied,
)
from domcek_bot.application.records import (
    CalendarSourceRecord,
    ChannelArchiveRequestRecord,
    GuildConfigRecord,
    ReactionConfigRecord,
)
from domcek_bot.application.settings import SettingsValidationError
from domcek_bot.application.undo import UndoUnavailable
from domcek_bot.domain.errors import OptimisticLockError

router = APIRouter(prefix="/api/v1/admin")


class PublicationSettingsBody(BaseModel):
    expected_version: int = Field(ge=1)
    timezone: str = Field(min_length=1, max_length=64)
    publication_weekday: int = Field(ge=0, le=6)
    publication_time: time
    automatic_publication_enabled: bool
    publish_google_descriptions: bool
    generated_intro_enabled: bool
    everyone_mention_enabled: bool
    allow_stale_calendar_cache: bool = False
    publication_grace_seconds: int = Field(default=30, ge=0, le=300)
    publication_guard_recipient_ids: list[str] = Field(default_factory=list, max_length=100)
    alert_calendar_sync_enabled: bool
    alert_publication_enabled: bool
    alert_channel_operations_enabled: bool
    alert_role_operations_enabled: bool
    alert_publication_reminder_enabled: bool
    announcement_channel_id: str | None = None
    command_channel_id: str | None = None
    moderator_channel_id: str | None = None
    projects_category_id: str | None = None
    archive_category_id: str | None = None
    closing_message: str | None = Field(default=None, max_length=2000)


class CalendarBody(BaseModel):
    expected_version: int | None = Field(default=None, ge=1)
    external_calendar_id: str = Field(min_length=1, max_length=512)
    display_name: str = Field(min_length=1, max_length=200)
    priority: int = Field(ge=0, le=10_000)
    active: bool = True


class ReactionSettingsBody(BaseModel):
    expected_version: int = Field(ge=0)
    seen_enabled: bool
    seen_emoji_id: str | None = None
    seen_emoji_unicode: str | None = Field(default=None, max_length=32)
    auto_reaction_enabled: bool
    auto_reaction_emoji_id: str | None = None
    auto_reaction_emoji_unicode: str | None = Field(default=None, max_length=32)
    mention_reaction_enabled: bool
    mention_reaction_emoji_id: str | None = None
    mention_reaction_emoji_unicode: str | None = Field(default=None, max_length=32)
    auto_reaction_channel_ids: list[str] = Field(max_length=100)


class RoleMutationBody(BaseModel):
    member_id: str
    role: Literal["team_mod", "admin"]
    enabled: bool


class ReactionTestBody(BaseModel):
    kind: Literal["seen", "auto", "mention"]
    channel_id: str
    emoji_id: str | None = None
    emoji_unicode: str | None = Field(default=None, max_length=32)


class ChannelCreateBody(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    emoji: str = Field(default="🏠", min_length=1, max_length=16)
    owner_id: str | None = None
    member_ids: list[str] = Field(default_factory=list, max_length=100)
    role_ids: list[str] = Field(default_factory=list, max_length=100)
    category_id: str | None = None
    idempotency_key: str = Field(min_length=1, max_length=160)


class ArchiveRequestBody(BaseModel):
    channel_id: str
    reason: str = Field(min_length=3, max_length=1000)


class ArchiveDecisionBody(BaseModel):
    approve: bool


@router.get("/undo", response_class=JSONResponse)
async def list_undo_operations(
    request: Request,
    context: Annotated[AuthContext, Depends(authenticated_context)],
    scope: Literal["roles", "channels"] = Query(),
) -> JSONResponse:
    service = _service(request, "undo")
    try:
        records = await service.list_available(principal=context.principal, scope=scope)
    except AuthorizationDenied as exc:
        raise _forbidden("Nemáte oprávnenie zobraziť vratné zmeny.") from exc
    return JSONResponse(
        [
            {
                "id": str(record.id),
                "operation_type": record.operation_type,
                "object_id": record.object_id,
                "state": record.state.value,
                "before_snapshot": record.before_snapshot,
                "after_snapshot": record.after_snapshot,
                "created_at": (
                    None if record.created_at is None else record.created_at.isoformat()
                ),
                "last_block_reason": record.last_block_reason,
            }
            for record in records
        ]
    )


@router.post("/undo/{operation_id}", response_class=JSONResponse)
async def undo_operation(
    operation_id: uuid.UUID,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> JSONResponse:
    service = _service(request, "undo")
    try:
        result = await service.undo(
            operation_id,
            principal=context.principal,
            correlation_id=request.state.correlation_id,
        )
    except AuthorizationDenied as exc:
        raise _forbidden("Túto zmenu už nemáte oprávnenie vrátiť späť.") from exc
    except LookupError as exc:
        raise ApplicationError(
            "undo_not_found", "Zmenu nemožno nájsť", "Obnovte stránku a skúste to znova.", 404
        ) from exc
    except UndoUnavailable as exc:
        details = {
            "role_changed_since_operation": "Rola sa medzitým zmenila.",
            "last_admin_protection": "Návrat by odobral posledného Admina.",
            "created_channel_changed_offer_archive": (
                "Kanál už nie je prázdny alebo sa zmenil. "
                "Namiesto odstránenia ho môžete archivovať."
            ),
            "archived_channel_changed_since_operation": (
                "Archivovaný kanál sa medzitým zmenil, preto ho Carlo bezpečne nepresunie späť."
            ),
            "archived_channel_missing": "Archivovaný kanál už neexistuje.",
        }
        raise ApplicationError(
            "undo_unavailable",
            "Zmenu už nemožno bezpečne vrátiť",
            details.get(exc.reason, "Aktuálny stav Discordu už nezodpovedá pôvodnej zmene."),
            409,
        ) from exc
    return JSONResponse(
        {
            "id": str(result.id),
            "operation_type": result.operation_type,
            "state": result.state.value,
            "object_id": result.object_id,
        }
    )


@router.get("/settings", response_class=JSONResponse)
async def get_settings(
    request: Request,
    context: Annotated[AuthContext, Depends(authenticated_context)],
) -> JSONResponse:
    service = _service(request, "settings")
    try:
        snapshot = await service.get(context.principal)
    except AuthorizationDenied as exc:
        raise _forbidden("Nastavenia môže spravovať iba Admin.") from exc
    return JSONResponse(
        {
            "publication": _guild_json(snapshot.guild),
            "calendars": [_calendar_json(item) for item in snapshot.calendars],
            "reactions": _reaction_json(snapshot.reactions),
        }
    )


@router.put("/settings/publication", response_class=JSONResponse)
async def update_publication_settings(
    body: PublicationSettingsBody,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> JSONResponse:
    service = _service(request, "settings")
    try:
        result = await service.update_publication(
            **body.model_dump(
                exclude={
                    "announcement_channel_id",
                    "command_channel_id",
                    "moderator_channel_id",
                    "projects_category_id",
                    "archive_category_id",
                    "publication_guard_recipient_ids",
                }
            ),
            publication_guard_recipient_ids=tuple(_ids(body.publication_guard_recipient_ids)),
            announcement_channel_id=_id(body.announcement_channel_id),
            command_channel_id=_id(body.command_channel_id),
            moderator_channel_id=_id(body.moderator_channel_id),
            projects_category_id=_id(body.projects_category_id),
            archive_category_id=_id(body.archive_category_id),
            principal=context.principal,
            correlation_id=request.state.correlation_id,
        )
    except (SettingsValidationError, ValueError) as exc:
        raise _invalid(str(exc)) from exc
    except OptimisticLockError as exc:
        raise _conflict() from exc
    except AuthorizationDenied as exc:
        raise _forbidden("Nastavenia môže spravovať iba Admin.") from exc
    return JSONResponse(_guild_json(result))


@router.post("/calendars", response_class=JSONResponse, status_code=201)
async def create_calendar(
    body: CalendarBody,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> JSONResponse:
    service = _service(request, "settings")
    try:
        result = await service.add_calendar(
            **body.model_dump(exclude={"expected_version"}),
            principal=context.principal,
            correlation_id=request.state.correlation_id,
        )
    except AuthorizationDenied as exc:
        raise _forbidden("Kalendáre môže spravovať iba Admin.") from exc
    except SettingsValidationError as exc:
        raise _invalid(str(exc)) from exc
    return JSONResponse(_calendar_json(result), status_code=201)


@router.put("/calendars/{source_id}", response_class=JSONResponse)
async def update_calendar(
    source_id: uuid.UUID,
    body: CalendarBody,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> JSONResponse:
    if body.expected_version is None:
        raise _invalid("Chýba verzia kalendára.")
    service = _service(request, "settings")
    try:
        result = await service.update_calendar(
            source_id,
            **body.model_dump(exclude={"expected_version"}),
            expected_version=body.expected_version,
            principal=context.principal,
            correlation_id=request.state.correlation_id,
        )
    except AuthorizationDenied as exc:
        raise _forbidden("Kalendáre môže spravovať iba Admin.") from exc
    except SettingsValidationError as exc:
        raise _invalid(str(exc)) from exc
    except OptimisticLockError as exc:
        raise _conflict() from exc
    except LookupError as exc:
        raise _not_found("Kalendár sa nenašiel.") from exc
    return JSONResponse(_calendar_json(result))


@router.post("/calendars/{source_id}/sync", response_class=JSONResponse)
async def sync_calendar(
    source_id: uuid.UUID,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
    force_full: bool = Query(default=False),
) -> JSONResponse:
    service = _service(request, "settings")
    try:
        result = await service.sync_calendar(
            source_id,
            force_full=force_full,
            principal=context.principal,
            correlation_id=request.state.correlation_id,
        )
    except AuthorizationDenied as exc:
        raise _forbidden("Synchronizáciu môže spustiť iba Admin.") from exc
    except LookupError as exc:
        raise _not_found("Kalendár sa nenašiel.") from exc
    except Exception as exc:
        raise ApplicationError(
            "calendar_sync_failed",
            "Synchronizácia zlyhala",
            "Google kalendár sa nepodarilo synchronizovať. Stav zdroja bol uložený.",
            502,
        ) from exc
    return JSONResponse(
        {
            "source_id": str(result.source_id),
            "mode": result.mode.value,
            "received": result.received,
            "created": result.created,
            "updated": result.updated,
            "completed_at": result.completed_at.isoformat(),
        }
    )


@router.put("/settings/reactions", response_class=JSONResponse)
async def update_reactions(
    body: ReactionSettingsBody,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> JSONResponse:
    service = _service(request, "settings")
    try:
        record = ReactionConfigRecord(
            guild_id=context.principal.guild_id,
            seen_enabled=body.seen_enabled,
            seen_emoji_id=_id(body.seen_emoji_id),
            seen_emoji_unicode=body.seen_emoji_unicode,
            auto_reaction_enabled=body.auto_reaction_enabled,
            auto_reaction_emoji_id=_id(body.auto_reaction_emoji_id),
            auto_reaction_emoji_unicode=body.auto_reaction_emoji_unicode,
            mention_reaction_enabled=body.mention_reaction_enabled,
            mention_reaction_emoji_id=_id(body.mention_reaction_emoji_id),
            mention_reaction_emoji_unicode=body.mention_reaction_emoji_unicode,
            auto_reaction_channel_ids=tuple(_ids(body.auto_reaction_channel_ids)),
            version=max(1, body.expected_version),
        )
        result = await service.update_reactions(
            record,
            expected_version=body.expected_version,
            principal=context.principal,
            correlation_id=request.state.correlation_id,
        )
    except (SettingsValidationError, ValueError) as exc:
        raise _invalid(str(exc)) from exc
    except DiscordAdministrationError as exc:
        raise _invalid("Vybrané emoji alebo kanál už na Discorde nie sú dostupné.") from exc
    except OptimisticLockError as exc:
        raise _conflict() from exc
    except AuthorizationDenied as exc:
        raise _forbidden("Reakcie môže spravovať iba Admin.") from exc
    return JSONResponse(_reaction_json(result))


@router.get("/discord/directory", response_class=JSONResponse)
async def discord_directory(
    request: Request,
    context: Annotated[AuthContext, Depends(authenticated_context)],
) -> JSONResponse:
    service = _service(request, "discord_admin")
    try:
        result = await service.directory(context.principal)
    except AuthorizationDenied as exc:
        raise _forbidden("Nemáte oprávnenie na správu Discordu.") from exc
    except DiscordAdministrationError as exc:
        raise _discord_unavailable() from exc
    return JSONResponse(
        {
            "channels": [_directory_item_json(item) for item in result.channels],
            "categories": [_directory_item_json(item) for item in result.categories],
            "roles": [_directory_item_json(item) for item in result.roles],
            "emojis": [_directory_item_json(item) for item in result.emojis],
        }
    )


@router.get("/discord/members", response_class=JSONResponse)
async def search_members(
    request: Request,
    context: Annotated[AuthContext, Depends(authenticated_context)],
    query: str = Query(min_length=1, max_length=100),
) -> JSONResponse:
    service = _service(request, "discord_admin")
    try:
        result = await service.search_members(query, principal=context.principal)
    except AuthorizationDenied as exc:
        raise _forbidden("Nemáte oprávnenie vyhľadávať členov.") from exc
    except DiscordAdministrationError as exc:
        raise _discord_unavailable() from exc
    return JSONResponse([_snowflake_dict(asdict(item)) for item in result])


@router.put("/discord/roles", response_class=JSONResponse)
async def mutate_role(
    body: RoleMutationBody,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> JSONResponse:
    service = _service(request, "discord_admin")
    try:
        result = await service.set_application_role(
            member_id=_required_id(body.member_id),
            role=body.role,
            enabled=body.enabled,
            principal=context.principal,
            correlation_id=request.state.correlation_id,
        )
    except AuthorizationDenied as exc:
        raise _forbidden("Roly môže spravovať iba Admin.") from exc
    except ValueError as exc:
        raise _invalid("Discord member ID nie je platné.") from exc
    except LastAdminRemovalDenied as exc:
        raise ApplicationError(
            "last_admin",
            "Posledného Admina nemožno odobrať",
            "Najprv udeľte Admin oprávnenie ďalšiemu členovi.",
            409,
        ) from exc
    except DiscordAdministrationError as exc:
        raise _discord_unavailable() from exc
    return JSONResponse(_snowflake_dict(asdict(result)))


@router.post("/discord/reactions/test", response_class=JSONResponse)
async def test_reaction(
    body: ReactionTestBody,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> JSONResponse:
    service = _service(request, "discord_admin")
    try:
        message_id = await service.test_configured_reaction(
            kind=body.kind,
            channel_id=_required_id(body.channel_id),
            emoji_id=_id(body.emoji_id),
            emoji_unicode=body.emoji_unicode,
            principal=context.principal,
            correlation_id=request.state.correlation_id,
        )
    except AuthorizationDenied as exc:
        raise _forbidden("Reakcie môže testovať iba Admin.") from exc
    except ValueError as exc:
        raise _invalid(str(exc)) from exc
    except DiscordAdministrationError as exc:
        raise _discord_unavailable() from exc
    return JSONResponse({"message_id": str(message_id)})


@router.post("/channels", response_class=JSONResponse, status_code=201)
async def create_channel(
    body: ChannelCreateBody,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> JSONResponse:
    service = _service(request, "channels")
    try:
        result = await service.create_channel(
            name=body.name,
            member_ids=tuple(_ids(body.member_ids)),
            role_ids=tuple(_ids(body.role_ids)),
            category_id=_id(body.category_id),
            idempotency_key=body.idempotency_key,
            principal=context.principal,
            correlation_id=request.state.correlation_id,
            emoji=body.emoji,
            owner_id=_id(body.owner_id),
        )
    except AuthorizationDenied as exc:
        raise _forbidden("Kanály môže vytvárať Admin alebo Team Mod.") from exc
    except (ValueError, ChannelOperationError) as exc:
        raise _invalid("Kanál sa nepodarilo bezpečne vytvoriť.") from exc
    return JSONResponse(
        {
            "channel_id": str(result.channel_id),
            "name": result.name,
            "jump_url": result.jump_url,
            "undo_id": None if result.undo_id is None else str(result.undo_id),
        },
        status_code=201,
    )


@router.get("/archives", response_class=JSONResponse)
async def list_archives(
    request: Request,
    context: Annotated[AuthContext, Depends(authenticated_context)],
) -> JSONResponse:
    try:
        context.principal.require(Capability.MANAGE_CHANNELS)
        service = _service(request, "channels")
        result = await service.list_pending(context.principal.guild_id)
    except AuthorizationDenied as exc:
        raise _forbidden("Archivácie môže zobraziť Admin alebo Team Mod.") from exc
    return JSONResponse([_archive_json(item) for item in result])


@router.post("/archives", response_class=JSONResponse, status_code=201)
async def request_archive(
    body: ArchiveRequestBody,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> JSONResponse:
    service = _service(request, "channels")
    try:
        result = await service.request_archive(
            channel_id=_required_id(body.channel_id),
            reason=body.reason,
            principal=context.principal,
            correlation_id=request.state.correlation_id,
        )
    except AuthorizationDenied as exc:
        raise _forbidden("Archiváciu môže navrhnúť Admin alebo Team Mod.") from exc
    except (ValueError, ChannelOperationError) as exc:
        raise _invalid("Žiadosť o archiváciu sa nepodarilo vytvoriť.") from exc
    return JSONResponse(_archive_json(result), status_code=201)


@router.post("/archives/{request_id}/decision", response_class=JSONResponse)
async def decide_archive(
    request_id: uuid.UUID,
    body: ArchiveDecisionBody,
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> JSONResponse:
    service = _service(request, "channels")
    try:
        result = await service.decide_archive(
            request_id,
            approve=body.approve,
            principal=context.principal,
            correlation_id=request.state.correlation_id,
        )
    except AuthorizationDenied as exc:
        raise _forbidden("Archiváciu môže rozhodnúť iba Admin.") from exc
    except (ArchiveDecisionConflict, LookupError) as exc:
        raise ApplicationError(
            "archive_conflict",
            "Žiadosť už nie je otvorená",
            "Obnovte zoznam čakajúcich žiadostí.",
            409,
        ) from exc
    except ChannelOperationError as exc:
        raise _discord_unavailable() from exc
    return JSONResponse(_archive_json(result))


@router.post("/archives/recover", response_class=JSONResponse)
async def recover_archives(
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> JSONResponse:
    service = _service(request, "channels")
    try:
        context.principal.require(Capability.APPROVE_ARCHIVE)
        results = await service.recover_archives(
            context.principal.guild_id,
            correlation_id=request.state.correlation_id,
        )
    except AuthorizationDenied as exc:
        raise _forbidden("Obnovu archivácie môže spustiť iba Admin.") from exc
    return JSONResponse([_archive_json(item) for item in results])


def _service(request: Request, name: str) -> Any:
    value = getattr(services(request), name)
    if value is None:
        raise ApplicationError(
            "service_unavailable",
            "Administrácia nie je pripravená",
            "Požadovaná administračná služba momentálne nie je dostupná.",
            503,
        )
    return value


def _guild_json(record: GuildConfigRecord) -> dict[str, object]:
    data: dict[str, Any] = asdict(record)
    data["guild_id"] = str(data["guild_id"])
    for key in (
        "admin_role_id",
        "team_mod_role_id",
        "publisher_role_id",
        "announcement_channel_id",
        "command_channel_id",
        "moderator_channel_id",
        "projects_category_id",
        "archive_category_id",
    ):
        data[key] = None if data[key] is None else str(data[key])
    data["publication_guard_recipient_ids"] = [
        str(value) for value in record.publication_guard_recipient_ids
    ]
    data["publication_time"] = record.publication_time.isoformat()
    return dict(data)


def _calendar_json(record: CalendarSourceRecord) -> dict[str, object]:
    data: dict[str, Any] = asdict(record)
    data.pop("sync_token", None)
    data.pop("sync_token_query_key", None)
    data["id"] = str(data["id"])
    data["guild_id"] = str(data["guild_id"])
    data["sync_status"] = record.sync_status.value
    for key in ("last_sync_attempt_at", "last_sync_success_at", "last_full_sync_at"):
        value = data[key]
        data[key] = None if value is None else value.isoformat()
    return dict(data)


def _reaction_json(record: ReactionConfigRecord) -> dict[str, object]:
    data = asdict(record)
    data["guild_id"] = str(record.guild_id)
    for key in ("seen_emoji_id", "auto_reaction_emoji_id", "mention_reaction_emoji_id"):
        data[key] = None if data[key] is None else str(data[key])
    data["auto_reaction_channel_ids"] = [str(value) for value in record.auto_reaction_channel_ids]
    return data


def _archive_json(record: ChannelArchiveRequestRecord) -> dict[str, object]:
    data: dict[str, Any] = asdict(record)
    for key in (
        "guild_id",
        "discord_channel_id",
        "archive_category_id",
        "requested_by_user_id",
        "decided_by_user_id",
        "discord_approval_message_id",
        "undo_id",
    ):
        data[key] = None if data[key] is None else str(data[key])
    data["id"] = str(data["id"])
    data["state"] = record.state.value
    data["expires_at"] = record.expires_at.isoformat()
    data["decided_at"] = None if record.decided_at is None else record.decided_at.isoformat()
    return dict(data)


def _snowflake_dict(data: dict[str, object]) -> dict[str, object]:
    data["id"] = str(data["id"])
    if "role_ids" in data:
        role_ids = data["role_ids"]
        if isinstance(role_ids, (tuple, list)):
            data["role_ids"] = [str(value) for value in role_ids]
    return data


def _directory_item_json(
    item: DiscordChannelOption | DiscordRoleOption | DiscordEmojiOption,
) -> dict[str, object]:
    data: dict[str, Any] = asdict(item)
    data["id"] = str(data["id"])
    if "category_id" in data:
        data["category_id"] = None if data["category_id"] is None else str(data["category_id"])
    return dict(data)


def _id(value: str | None) -> int | None:
    return None if value is None or not value.strip() else _required_id(value)


def _ids(values: list[str]) -> list[int]:
    return [_required_id(value) for value in values]


def _required_id(value: str) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise ValueError("Discord identifikátor nie je platný") from exc
    if result <= 0:
        raise ValueError("Discord identifikátor nie je platný")
    return result


def _forbidden(detail: str) -> ApplicationError:
    return ApplicationError("forbidden", "Prístup bol odmietnutý", detail, 403)


def _invalid(detail: str) -> ApplicationError:
    return ApplicationError("invalid_settings", "Nastavenie nie je platné", detail, 422)


def _conflict() -> ApplicationError:
    return ApplicationError(
        "edit_conflict",
        "Nastavenia sa medzitým zmenili",
        "Obnovte údaje a skúste zmenu znova.",
        409,
    )


def _not_found(detail: str) -> ApplicationError:
    return ApplicationError("not_found", "Záznam sa nenašiel", detail, 404)


def _discord_unavailable() -> ApplicationError:
    return ApplicationError(
        "discord_unavailable",
        "Discord operáciu nemožno dokončiť",
        "Skontrolujte oprávnenia Carla a skúste operáciu znova.",
        502,
    )
