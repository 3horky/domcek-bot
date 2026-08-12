"""Production composition root for the HTTP process."""

from __future__ import annotations

from datetime import timedelta

import structlog
from fastapi import FastAPI

from domcek_bot.api.app import create_app
from domcek_bot.api.dependencies import ApiServices
from domcek_bot.application.alerts import AlertCategory, ConfiguredModeratorAlerts
from domcek_bot.application.audit import AuditQueryService
from domcek_bot.application.auth.oauth_state import OAuthStateCodec
from domcek_bot.application.auth.service import AuthService
from domcek_bot.application.auth.session import SessionService
from domcek_bot.application.bootstrap import ensure_guild_config
from domcek_bot.application.calendar.sync import CalendarSyncService
from domcek_bot.application.channels import ChannelManagementService
from domcek_bot.application.discord_admin import DiscordAdministrationService
from domcek_bot.application.editor.content import ContentEditorialService
from domcek_bot.application.editor.events import EventEditorialService
from domcek_bot.application.operations import RuntimeOperationsService
from domcek_bot.application.publication.engine import PublicationEngine
from domcek_bot.application.publication.history import PublicationHistoryService
from domcek_bot.application.publication.intro import IntroService
from domcek_bot.application.publication.manual import ManualPublicationService
from domcek_bot.application.publication.recovery import PublicationRecoveryService
from domcek_bot.application.publication.service import PublicationDraftService
from domcek_bot.application.publication.shadow import ShadowPublicationService
from domcek_bot.application.records import GuildConfigRecord
from domcek_bot.application.settings import SettingsService
from domcek_bot.config import ConfigurationError, ProcessKind, load_settings
from domcek_bot.infrastructure.calendar_factory import build_google_calendar_client
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.discord_admin import DiscordHttpAdministrationGateway
from domcek_bot.infrastructure.discord_identity import DiscordHttpIdentityClient
from domcek_bot.infrastructure.discord_publication import (
    DiscordHttpPublicationGateway,
    DiscordModeratorAlertGateway,
)
from domcek_bot.infrastructure.gemini_intro import GeminiIntroGenerator
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

logger = structlog.get_logger(__name__)


def create_runtime_app() -> FastAPI:
    settings = load_settings(ProcessKind.API)
    database = Database(settings)
    unit_of_work = SqlAlchemyUnitOfWork(database)
    sessions = SessionService(
        unit_of_work,
        secret=settings.session_secret_value(),
        lifetime=timedelta(hours=settings.session_lifetime_hours),
    )
    discord = DiscordHttpIdentityClient(
        client_id=settings.resolved_discord_oauth_client_id,
        client_secret=settings.discord_oauth_secret_value(),
        redirect_uri=settings.discord_oauth_redirect_uri,
        bot_token=settings.discord_token_value(),
    )
    guild_id = settings.discord_guild_id
    if guild_id is None:
        raise RuntimeError("validated API settings have no Discord guild ID")
    auth = AuthService(unit_of_work, discord, sessions, guild_id=guild_id)
    draft_service = PublicationDraftService(unit_of_work)
    intro_key = settings.optional_intro_generator_key()
    intro_generator = (
        GeminiIntroGenerator(
            api_key=intro_key,
            model=settings.intro_generator_model,
            timeout_seconds=settings.intro_generator_timeout_seconds,
        )
        if intro_key is not None
        else None
    )
    publication_gateway = DiscordHttpPublicationGateway(bot_token=settings.discord_token_value())
    alert_gateway = DiscordModeratorAlertGateway(
        bot_token=settings.discord_token_value(),
        frontend_base_url=settings.frontend_base_url,
    )
    publication_alerts = ConfiguredModeratorAlerts(
        unit_of_work, alert_gateway, AlertCategory.PUBLICATION
    )
    channel_alerts = ConfiguredModeratorAlerts(unit_of_work, alert_gateway, AlertCategory.CHANNEL)
    role_alerts = ConfiguredModeratorAlerts(unit_of_work, alert_gateway, AlertCategory.ROLE)
    publication_engine = PublicationEngine(
        unit_of_work,
        draft_service,
        IntroService(intro_generator),
        publication_gateway,
        alerts=publication_alerts,
        seen_emoji=settings.publication_seen_emoji,
        max_safe_retries=settings.publication_retry_attempts,
    )
    google_calendar = build_google_calendar_client(settings)
    calendar_sync = CalendarSyncService(unit_of_work, google_calendar)
    discord_admin_gateway = DiscordHttpAdministrationGateway(
        bot_token=settings.discord_token_value()
    )
    api_services = ApiServices(
        auth=auth,
        sessions=sessions,
        oauth_state=OAuthStateCodec(
            secret=settings.session_secret_value(),
            lifetime=timedelta(minutes=settings.oauth_state_lifetime_minutes),
        ),
        publication_drafts=draft_service,
        event_editor=EventEditorialService(unit_of_work),
        content_editor=ContentEditorialService(unit_of_work),
        audit=AuditQueryService(unit_of_work),
        manual_publications=ManualPublicationService(
            draft_service,
            publication_engine,
            secret=settings.session_secret_value(),
            publication_enabled=settings.manual_publication_enabled,
        ),
        publication_recovery=PublicationRecoveryService(unit_of_work, publication_engine),
        settings=SettingsService(
            unit_of_work,
            calendar_sync,
            reaction_validator=discord_admin_gateway,
            discord_settings_validator=discord_admin_gateway,
        ),
        channels=ChannelManagementService(unit_of_work, discord_admin_gateway, channel_alerts),
        discord_admin=DiscordAdministrationService(
            unit_of_work, discord_admin_gateway, role_alerts
        ),
        publication_history=PublicationHistoryService(
            unit_of_work,
            calendar_warning_age=timedelta(minutes=settings.calendar_stale_warning_minutes),
            calendar_max_safe_age=timedelta(minutes=settings.calendar_max_safe_age_minutes),
        ),
        shadow_publications=ShadowPublicationService(unit_of_work, draft_service),
        operations=RuntimeOperationsService(unit_of_work),
        resources=tuple(
            resource
            for resource in (
                publication_gateway,
                alert_gateway,
                intro_generator,
                google_calendar,
                discord_admin_gateway,
            )
            if resource is not None
        ),
    )

    async def bootstrap() -> None:
        required_roles = (
            settings.discord_admin_role_id,
            settings.discord_team_mod_role_id,
            settings.discord_publisher_role_id,
        )
        if any(role_id is None for role_id in required_roles):
            async with unit_of_work.transaction() as repositories:
                existing = await repositories.guild_configs.get(guild_id)
            if existing is None:
                raise ConfigurationError(
                    "DISCORD_ADMIN_ROLE_ID, DISCORD_TEAM_MOD_ROLE_ID and "
                    "DISCORD_PUBLISHER_ROLE_ID are required to initialize a guild"
                )
            return
        created = await ensure_guild_config(
            unit_of_work,
            GuildConfigRecord(
                guild_id=guild_id,
                timezone=settings.timezone,
                admin_role_id=settings.discord_admin_role_id,
                team_mod_role_id=settings.discord_team_mod_role_id,
                publisher_role_id=settings.discord_publisher_role_id,
                announcement_channel_id=settings.discord_announcement_channel_id,
                command_channel_id=settings.discord_command_channel_id,
                moderator_channel_id=settings.discord_moderator_channel_id,
                projects_category_id=settings.discord_projects_category_id,
                archive_category_id=settings.discord_archive_category_id,
            ),
        )
        if created:
            await logger.ainfo("guild_config_initialized", guild_id=guild_id)

    return create_app(
        settings=settings,
        database=database,
        services=api_services,
        startup=bootstrap,
    )
