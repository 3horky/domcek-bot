"""Typed API service bundle and authentication dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fastapi import Request

from domcek_bot.api.errors import ApplicationError
from domcek_bot.application.audit import AuditQueryService
from domcek_bot.application.auth.authorization import Principal
from domcek_bot.application.auth.contracts import DiscordIdentityError, DiscordMemberNotFound
from domcek_bot.application.auth.oauth_state import OAuthStateCodec
from domcek_bot.application.auth.service import AuthService, GuildConfigurationMissing, LoginDenied
from domcek_bot.application.auth.session import InvalidSession, SessionService
from domcek_bot.application.channels import ChannelManagementService
from domcek_bot.application.discord_admin import DiscordAdministrationService
from domcek_bot.application.editor.content import ContentEditorialService
from domcek_bot.application.editor.events import EventEditorialService
from domcek_bot.application.operations import RuntimeOperationsService
from domcek_bot.application.publication.history import PublicationHistoryService
from domcek_bot.application.publication.manual import ManualPublicationService
from domcek_bot.application.publication.recovery import PublicationRecoveryService
from domcek_bot.application.publication.service import PublicationDraftService
from domcek_bot.application.publication.shadow import ShadowPublicationService
from domcek_bot.application.records import WebSessionRecord
from domcek_bot.application.settings import SettingsService
from domcek_bot.application.undo import UndoService

SESSION_COOKIE = "domcek_session"
CSRF_COOKIE = "domcek_csrf"
OAUTH_STATE_COOKIE = "domcek_oauth_state"


class AsyncCloseable(Protocol):
    async def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class ApiServices:
    auth: AuthService
    sessions: SessionService
    oauth_state: OAuthStateCodec
    publication_drafts: PublicationDraftService
    event_editor: EventEditorialService
    content_editor: ContentEditorialService
    audit: AuditQueryService
    manual_publications: ManualPublicationService | None = None
    publication_recovery: PublicationRecoveryService | None = None
    settings: SettingsService | None = None
    channels: ChannelManagementService | None = None
    discord_admin: DiscordAdministrationService | None = None
    publication_history: PublicationHistoryService | None = None
    shadow_publications: ShadowPublicationService | None = None
    operations: RuntimeOperationsService | None = None
    undo: UndoService | None = None
    resources: tuple[AsyncCloseable, ...] = ()

    async def close(self) -> None:
        await self.auth.close()
        for resource in self.resources:
            await resource.close()


@dataclass(frozen=True, slots=True)
class AuthContext:
    session: WebSessionRecord
    principal: Principal


def services(request: Request) -> ApiServices:
    value = getattr(request.app.state, "services", None)
    if not isinstance(value, ApiServices):
        raise ApplicationError(
            "service_unavailable",
            "Služba nie je pripravená",
            "Autentifikačná služba momentálne nie je dostupná.",
            503,
        )
    return value


async def authenticated_context(request: Request) -> AuthContext:
    bundle = services(request)
    try:
        session, principal = await bundle.auth.principal_for_session(
            request.cookies.get(SESSION_COOKIE)
        )
    except (InvalidSession, LoginDenied, DiscordMemberNotFound) as exc:
        raise ApplicationError(
            "authentication_required",
            "Vyžaduje sa prihlásenie",
            "Relácia nie je platná alebo už nemáte prístup k administrácii.",
            401,
        ) from exc
    except GuildConfigurationMissing as exc:
        raise ApplicationError(
            "guild_not_configured",
            "Carlo ešte nie je pripravený",
            "Nastavenie rolí servera nie je dostupné. "
            "Skúste to znova alebo kontaktujte správcu Carla.",
            503,
        ) from exc
    except DiscordIdentityError as exc:
        raise ApplicationError(
            "identity_unavailable",
            "Overenie identity nie je dostupné",
            "Discord členstvo sa momentálne nepodarilo bezpečne overiť.",
            503,
        ) from exc
    return AuthContext(session, principal)


async def csrf_context(request: Request) -> AuthContext:
    context = await authenticated_context(request)
    try:
        services(request).sessions.verify_csrf(
            context.session,
            request.cookies.get(CSRF_COOKIE),
            request.headers.get("X-CSRF-Token"),
        )
    except InvalidSession as exc:
        raise ApplicationError(
            "csrf_rejected",
            "Požiadavka bola odmietnutá",
            "Obnovte stránku a skúste operáciu znova.",
            403,
        ) from exc
    return context
