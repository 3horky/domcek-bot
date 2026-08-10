"""Isolated real API/PostgreSQL server for the Playwright full-stack smoke test."""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import uvicorn
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.engine import make_url

from domcek_bot.api.app import create_app
from domcek_bot.api.dependencies import ApiServices
from domcek_bot.application.audit import AuditQueryService
from domcek_bot.application.auth.contracts import (
    DiscordGuildMember,
    DiscordOAuthToken,
    DiscordUser,
)
from domcek_bot.application.auth.oauth_state import OAuthStateCodec
from domcek_bot.application.auth.service import AuthService
from domcek_bot.application.auth.session import SessionService
from domcek_bot.application.editor.content import ContentEditorialService
from domcek_bot.application.editor.events import EventEditorialService
from domcek_bot.application.publication.service import PublicationDraftService
from domcek_bot.application.records import (
    CalendarSourceRecord,
    ExternalEventRecord,
    GuildConfigRecord,
    WebSessionRecord,
)
from domcek_bot.config import AppEnvironment, Settings
from domcek_bot.domain.enums import SyncStatus
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.models import Base
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

GUILD_ID = 1535774834955391047
USER_ID = 1535771583841439765
ADMIN_ROLE_ID = 1535774886306390127
SESSION_TOKEN = "carlo-browser-e2e-session"  # noqa: S105
CSRF_TOKEN = "carlo-browser-e2e-csrf"  # noqa: S105
SESSION_SECRET = "carlo-browser-e2e-session-secret-32-bytes"  # noqa: S105
EVENT_ID = uuid.UUID("00000000-0000-4000-8000-000000000101")
SOURCE_ID = uuid.UUID("00000000-0000-4000-8000-000000000102")


class BrowserIdentity:
    """Deterministic Discord boundary; it never performs a network request."""

    def __init__(self) -> None:
        self.user = DiscordUser(USER_ID, "browser-admin", "Browser Admin", None)

    async def exchange_code(self, code: str) -> DiscordOAuthToken:
        del code
        raise AssertionError("the full-stack smoke test must not use OAuth")

    async def current_user(self, access_token: str) -> DiscordUser:
        del access_token
        raise AssertionError("the full-stack smoke test must not use OAuth")

    async def current_member(self, access_token: str, guild_id: int) -> DiscordGuildMember:
        del access_token, guild_id
        raise AssertionError("the full-stack smoke test must not use OAuth")

    async def guild_member(self, guild_id: int, user_id: int) -> DiscordGuildMember:
        if guild_id != GUILD_ID or user_id != USER_ID:
            raise AssertionError("unexpected full-stack smoke-test identity")
        return DiscordGuildMember(self.user, guild_id, frozenset({ADMIN_ROLE_ID}), None)

    async def close(self) -> None:
        return None


class DatabaseCleanup:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def close(self) -> None:
        await _truncate(self.database)


def _database_url() -> str:
    value = os.environ.get("TEST_DATABASE_URL")
    if not value:
        env_file = Path(__file__).resolve().parents[2] / ".env"
        if env_file.is_file():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("TEST_DATABASE_URL="):
                    value = line.partition("=")[2].strip()
                    break
    if not value:
        raise RuntimeError("TEST_DATABASE_URL is required for browser E2E")
    database_name = make_url(value).database or ""
    if not database_name.endswith("_test"):
        raise RuntimeError("browser E2E refuses a database without the _test suffix")
    return value


async def _truncate(database: Database) -> None:
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    async with database.transaction() as connection:
        await connection.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))


def _services(
    database: Database, settings: Settings
) -> tuple[ApiServices, SessionService, SqlAlchemyUnitOfWork]:
    unit_of_work = SqlAlchemyUnitOfWork(database)
    sessions = SessionService(
        unit_of_work,
        secret=settings.session_secret_value(),
        lifetime=timedelta(hours=1),
    )
    identity = BrowserIdentity()
    draft_service = PublicationDraftService(unit_of_work)
    return (
        ApiServices(
            auth=AuthService(unit_of_work, identity, sessions, guild_id=GUILD_ID),
            sessions=sessions,
            oauth_state=OAuthStateCodec(
                secret=settings.session_secret_value(), lifetime=timedelta(minutes=10)
            ),
            publication_drafts=draft_service,
            event_editor=EventEditorialService(unit_of_work),
            content_editor=ContentEditorialService(unit_of_work),
            audit=AuditQueryService(unit_of_work),
            resources=(DatabaseCleanup(database),),
        ),
        sessions,
        unit_of_work,
    )


async def _seed(
    database: Database, sessions: SessionService, unit_of_work: SqlAlchemyUnitOfWork
) -> None:
    await _truncate(database)
    now = datetime.now(UTC)
    async with unit_of_work.transaction() as repositories:
        await repositories.guild_configs.add(
            GuildConfigRecord(guild_id=GUILD_ID, admin_role_id=ADMIN_ROLE_ID)
        )
        await repositories.calendar_sources.add(
            CalendarSourceRecord(
                id=SOURCE_ID,
                guild_id=GUILD_ID,
                provider="google",
                external_calendar_id="browser-e2e@example.test",
                display_name="Browser E2E",
                sync_status=SyncStatus.SUCCEEDED,
                last_sync_attempt_at=now,
                last_sync_success_at=now,
                last_full_sync_at=now,
            )
        )
        await repositories.external_events.add(
            ExternalEventRecord(
                id=EVENT_ID,
                calendar_source_id=SOURCE_ID,
                source_key="browser-e2e-occurrence",
                provider_event_id="browser-e2e-event",
                source_title="Full-stack skúška",
                source_description="Text z izolovaného testovacieho kalendára.",
                is_all_day=False,
                starts_at=now + timedelta(days=8),
                ends_at=now + timedelta(days=8, hours=2),
                last_synced_at=now,
            )
        )
        await repositories.web_sessions.add(
            WebSessionRecord(
                id=uuid.uuid4(),
                guild_id=GUILD_ID,
                discord_user_id=USER_ID,
                session_token_hash=sessions.hash_token(SESSION_TOKEN),
                csrf_token_hash=sessions.hash_token(CSRF_TOKEN),
                created_at=now,
                last_seen_at=now,
                expires_at=now + timedelta(hours=1),
            )
        )


def _settings() -> Settings:
    return Settings(
        app_env=AppEnvironment.TEST,
        database_url=_database_url(),
        session_secret=SecretStr(SESSION_SECRET),
        discord_oauth_client_secret=SecretStr("browser-e2e-oauth"),
        discord_bot_token=SecretStr("browser-e2e-bot"),
        discord_application_id=USER_ID,
        discord_guild_id=GUILD_ID,
        frontend_base_url="http://127.0.0.1:4175",
        allowed_origins="http://127.0.0.1:4175",
    )


async def _cleanup_only(settings: Settings) -> None:
    database = Database(settings)
    try:
        await _truncate(database)
    finally:
        await database.close()


def main() -> None:
    settings = _settings()
    if sys.argv[1:] == ["--cleanup"]:
        asyncio.run(_cleanup_only(settings))
        return
    if sys.argv[1:]:
        raise RuntimeError("supported argument: --cleanup")
    database = Database(settings)
    services, sessions, unit_of_work = _services(database, settings)

    async def startup() -> None:
        await _seed(database, sessions, unit_of_work)

    app = create_app(
        settings=settings,
        database=database,
        services=services,
        startup=startup,
    )
    uvicorn.run(
        app,
        host=os.environ.get("CARLO_E2E_API_HOST", "127.0.0.1"),
        port=4180,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
