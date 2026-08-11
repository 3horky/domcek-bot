from __future__ import annotations

import io
import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
from PIL import Image
from pydantic import SecretStr
from sqlalchemy import text

from domcek_bot.api.app import create_app
from domcek_bot.api.dependencies import CSRF_COOKIE, SESSION_COOKIE, ApiServices
from domcek_bot.application.audit import AuditQueryService
from domcek_bot.application.auth.authorization import Capability, Principal
from domcek_bot.application.auth.contracts import (
    DiscordGuildMember,
    DiscordOAuthToken,
    DiscordUser,
)
from domcek_bot.application.auth.oauth_state import OAuthStateCodec
from domcek_bot.application.auth.service import AuthService
from domcek_bot.application.auth.session import SessionService
from domcek_bot.application.channels import CreatedChannel
from domcek_bot.application.discord_admin import DiscordMemberOption
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
from domcek_bot.application.records import (
    CalendarSourceRecord,
    ExternalEventRecord,
    GuildConfigRecord,
    PublicationMessageRecord,
)
from domcek_bot.application.settings import SettingsService
from domcek_bot.config import AppEnvironment, Settings
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.models import Base
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.skipif(
    "TEST_DATABASE_URL" not in os.environ,
    reason="integration database not configured",
)

GUILD_ID = 1535774834955391047
USER_ID = 1535771583841439765
TEAM_ROLE = 1535775387307745400
PUBLISHER_ROLE = 1535775015285559339
ADMIN_ROLE = 1535774886306390127
NOW = datetime(2026, 8, 9, 10, tzinfo=UTC)


class MutableDiscordIdentity:
    def __init__(self) -> None:
        self.role_ids: frozenset[int] = frozenset()
        self.user = DiscordUser(USER_ID, "matrix-user", "Matrix User", None)

    async def exchange_code(self, code: str) -> DiscordOAuthToken:
        del code
        return DiscordOAuthToken(
            "unused",
            "Bearer",
            3600,
            frozenset({"identify", "guilds.members.read"}),
        )

    async def current_user(self, access_token: str) -> DiscordUser:
        del access_token
        return self.user

    async def current_member(self, access_token: str, guild_id: int) -> DiscordGuildMember:
        del access_token
        return DiscordGuildMember(self.user, guild_id, self.role_ids, None)

    async def guild_member(self, guild_id: int, user_id: int) -> DiscordGuildMember:
        assert user_id == USER_ID
        return DiscordGuildMember(self.user, guild_id, self.role_ids, None)

    async def close(self) -> None:
        return None


class UnusedPublicationDiscord:
    async def send_message(self, message: PublicationMessageRecord) -> int:
        raise AssertionError(f"preview unexpectedly sent message {message.id}")

    async def add_reaction(self, *, channel_id: int, message_id: int, emoji: str) -> None:
        raise AssertionError(
            f"preview unexpectedly reacted in {channel_id}/{message_id} with {emoji}"
        )


class MatrixChannelAdministration:
    async def create_channel(self, **values: Any) -> CreatedChannel:
        principal = cast(Principal, values["principal"])
        principal.require(Capability.MANAGE_CHANNELS)
        return CreatedChannel(777, "🏠・matrix", "https://discord.test/channels/777", 333)


class MatrixRoleAdministration:
    calls = 0

    async def set_application_role(self, **values: Any) -> DiscordMemberOption:
        principal = cast(Principal, values["principal"])
        principal.require(Capability.MANAGE_ROLES)
        self.calls += 1
        return DiscordMemberOption(
            cast(int, values["member_id"]),
            "matrix-member",
            "Matrix Member",
            None,
            (),
        )

    async def test_configured_reaction(self, **values: Any) -> int:
        principal = cast(Principal, values["principal"])
        principal.require(Capability.MANAGE_SETTINGS)
        return 123


@pytest.fixture
async def database() -> AsyncIterator[Database]:
    settings = Settings(
        app_env=AppEnvironment.TEST,
        database_url=os.environ["TEST_DATABASE_URL"],
        session_secret=SecretStr("s" * 32),
        discord_oauth_client_secret=SecretStr("oauth-secret"),
        discord_bot_token=SecretStr("bot-token"),
        discord_application_id=USER_ID,
        discord_guild_id=GUILD_ID,
    )
    database = Database(settings)
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    async with database.transaction() as connection:
        await connection.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))
    try:
        yield database
    finally:
        async with database.transaction() as connection:
            await connection.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))
        await database.close()


async def _seed(database: Database, count: int) -> list[uuid.UUID]:
    unit_of_work = SqlAlchemyUnitOfWork(database)
    source = CalendarSourceRecord(
        id=uuid.uuid4(),
        guild_id=GUILD_ID,
        provider="google",
        external_calendar_id="matrix@example.test",
        display_name="Matrix calendar",
    )
    event_ids: list[uuid.UUID] = []
    async with unit_of_work.transaction() as repositories:
        await repositories.guild_configs.add(
            GuildConfigRecord(
                guild_id=GUILD_ID,
                admin_role_id=ADMIN_ROLE,
                team_mod_role_id=TEAM_ROLE,
                publisher_role_id=PUBLISHER_ROLE,
            )
        )
        await repositories.calendar_sources.add(source)
        for position in range(count):
            event_id = uuid.uuid4()
            event_ids.append(event_id)
            await repositories.external_events.add(
                ExternalEventRecord(
                    id=event_id,
                    calendar_source_id=source.id,
                    source_key=f"matrix-{position}",
                    provider_event_id=f"matrix-provider-{position}",
                    source_title=f"Matrix {position}",
                    is_all_day=False,
                    starts_at=NOW + timedelta(days=position + 1),
                    ends_at=NOW + timedelta(days=position + 1, hours=1),
                    last_synced_at=NOW,
                )
            )
    return event_ids


async def test_direct_api_role_matrix(database: Database, tmp_path: Path) -> None:
    event_ids = await _seed(database, 8)
    settings = Settings(
        app_env=AppEnvironment.TEST,
        database_url=os.environ["TEST_DATABASE_URL"],
        session_secret=SecretStr("s" * 32),
        discord_oauth_client_secret=SecretStr("oauth-secret"),
        discord_bot_token=SecretStr("bot-token"),
        discord_application_id=USER_ID,
        discord_guild_id=GUILD_ID,
        media_root=tmp_path / "media",
        public_media_base_url="http://testserver",
    )
    unit_of_work = SqlAlchemyUnitOfWork(database)
    discord = MutableDiscordIdentity()
    sessions = SessionService(
        unit_of_work,
        secret=settings.session_secret_value(),
        lifetime=timedelta(hours=12),
    )
    draft_service = PublicationDraftService(unit_of_work)
    publication_engine = PublicationEngine(
        unit_of_work,
        draft_service,
        IntroService(None),
        UnusedPublicationDiscord(),
    )
    services = ApiServices(
        auth=AuthService(unit_of_work, discord, sessions, guild_id=GUILD_ID),
        sessions=sessions,
        oauth_state=OAuthStateCodec(
            secret=settings.session_secret_value(), lifetime=timedelta(minutes=10)
        ),
        publication_drafts=draft_service,
        event_editor=EventEditorialService(unit_of_work),
        content_editor=ContentEditorialService(unit_of_work),
        audit=AuditQueryService(unit_of_work),
        manual_publications=ManualPublicationService(
            draft_service,
            publication_engine,
            secret=settings.session_secret_value(),
        ),
        publication_recovery=PublicationRecoveryService(unit_of_work, publication_engine),
        settings=SettingsService(unit_of_work),
        publication_history=PublicationHistoryService(unit_of_work),
        shadow_publications=ShadowPublicationService(unit_of_work, draft_service),
        operations=RuntimeOperationsService(unit_of_work),
        channels=cast(Any, MatrixChannelAdministration()),
        discord_admin=cast(Any, MatrixRoleAdministration()),
    )
    app = create_app(settings=settings, database=database, services=services)
    transport = httpx.ASGITransport(app=app)

    async def request(
        role_id: int | None,
        method: str,
        path: str,
        *,
        json: dict[str, object] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
    ) -> httpx.Response:
        discord.role_ids = frozenset({role_id}) if role_id is not None else frozenset()
        issued = await sessions.create(guild_id=GUILD_ID, user_id=USER_ID)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
            cookies={
                SESSION_COOKIE: issued.session_token,
                CSRF_COOKIE: issued.csrf_token,
            },
        ) as client:
            return await client.request(
                method,
                path,
                json=json,
                files=files,
                headers={"X-CSRF-Token": issued.csrf_token},
            )

    roles = (TEAM_ROLE, PUBLISHER_ROLE, ADMIN_ROLE, None)
    expected_view = (200, 200, 200, 401)
    expected_edit = (200, 403, 200, 401)
    expected_force = (403, 403, 200, 401)
    expected_content = (201, 403, 201, 401)
    expected_audit = (200, 403, 200, 401)
    expected_manual_publish = (403, 200, 200, 401)
    expected_settings = (403, 403, 200, 401)
    expected_recovery = (403, 403, 409, 401)

    for role_id, expected in zip(roles, expected_view, strict=True):
        response = await request(role_id, "GET", "/api/v1/publication/draft")
        assert response.status_code == expected

    for role_id, expected in zip(roles, expected_view, strict=True):
        response = await request(role_id, "GET", "/api/v1/publication/history")
        assert response.status_code == expected

    for role_id, expected in zip(roles, expected_view, strict=True):
        response = await request(role_id, "GET", "/api/v1/publication/dashboard")
        assert response.status_code == expected

    for role_id, expected in zip(roles, expected_view, strict=True):
        response = await request(role_id, "GET", "/api/v1/publication/shadow-history")
        assert response.status_code == expected

    for role_id, expected in zip(roles, expected_view, strict=True):
        response = await request(role_id, "GET", "/api/v1/operations/summary")
        assert response.status_code == expected

    for role_id, expected in zip(roles, expected_settings, strict=True):
        response = await request(role_id, "GET", "/api/v1/admin/settings")
        assert response.status_code == expected

    missing_run_id = uuid.uuid4()
    for role_id, expected in zip(roles, expected_recovery, strict=True):
        response = await request(
            role_id,
            "POST",
            f"/api/v1/publication/recovery/{missing_run_id}/confirm-not-sent",
            json={"message_position": 0},
        )
        assert response.status_code == expected

    for role_id, expected in zip(roles, expected_recovery, strict=True):
        response = await request(
            role_id,
            "POST",
            f"/api/v1/publication/recovery/{missing_run_id}/link-existing",
            json={"message_position": 0, "discord_message_id": "123456789012345678"},
        )
        assert response.status_code == expected

    for position, (role_id, expected) in enumerate(zip(roles, expected_edit, strict=True)):
        response = await request(
            role_id,
            "PUT",
            f"/api/v1/events/{event_ids[position]}/override",
            json={
                "expected_version": 0,
                "public_title": "API úprava",
                "description_state": "inherit",
            },
        )
        assert response.status_code == expected

    for position, (role_id, expected) in enumerate(
        zip(roles, expected_force, strict=True), start=4
    ):
        response = await request(
            role_id,
            "PUT",
            f"/api/v1/events/{event_ids[position]}/override",
            json={
                "expected_version": 0,
                "description_state": "inherit",
                "inclusion_decision": "force_include",
            },
        )
        assert response.status_code == expected

    for position, (role_id, expected) in enumerate(zip(roles, expected_content, strict=True)):
        response = await request(
            role_id,
            "POST",
            "/api/v1/manual-events",
            json={
                "title": f"Ručná udalosť {position}",
                "is_all_day": True,
                "starts_on": "2026-08-15",
            },
        )
        assert response.status_code == expected

    image_buffer = io.BytesIO()
    Image.new("RGB", (32, 24), "green").save(image_buffer, format="PNG")
    for role_id, expected in zip(roles, expected_content, strict=True):
        response = await request(
            role_id,
            "POST",
            "/api/v1/uploads/info-images",
            files={"image": ("thumbnail.png", image_buffer.getvalue(), "image/png")},
        )
        assert response.status_code == expected
        if expected == 201:
            image_url = response.json()["image_url"]
            assert image_url.startswith("http://testserver/media/info/")
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client:
                delivered = await client.get(image_url)
            assert delivered.status_code == 200
            assert delivered.headers["content-type"] == "image/webp"

    for role_id, expected in zip(roles, expected_audit, strict=True):
        response = await request(role_id, "GET", "/api/v1/audit")
        assert response.status_code == expected

    for role_id, expected in zip(roles, expected_manual_publish, strict=True):
        response = await request(role_id, "POST", "/api/v1/publication/manual/preview")
        assert response.status_code == expected
        if expected == 200:
            assert response.json()["confirmation_token"]
            assert response.json()["draft"]["messages"][0]["allowed_mentions"] == ["everyone"]

    publication_body: dict[str, object] = {
        "expected_version": 1,
        "timezone": "Europe/Bratislava",
        "publication_weekday": 0,
        "publication_time": "20:00:00",
        "automatic_publication_enabled": True,
        "publish_google_descriptions": False,
        "generated_intro_enabled": True,
        "everyone_mention_enabled": True,
        "allow_stale_calendar_cache": False,
        "alert_calendar_sync_enabled": True,
        "alert_publication_enabled": True,
        "alert_channel_operations_enabled": True,
        "alert_role_operations_enabled": True,
        "alert_publication_reminder_enabled": False,
        "announcement_channel_id": None,
        "command_channel_id": None,
        "moderator_channel_id": None,
        "projects_category_id": None,
        "archive_category_id": None,
        "closing_message": None,
    }
    for role_id, expected in zip(roles, expected_settings, strict=True):
        response = await request(
            role_id,
            "PUT",
            "/api/v1/admin/settings/publication",
            json=publication_body,
        )
        assert response.status_code == expected

    reaction_body: dict[str, object] = {
        "expected_version": 0,
        "seen_enabled": True,
        "seen_emoji_id": None,
        "seen_emoji_unicode": "✅",
        "auto_reaction_enabled": False,
        "auto_reaction_emoji_id": None,
        "auto_reaction_emoji_unicode": None,
        "mention_reaction_enabled": False,
        "mention_reaction_emoji_id": None,
        "mention_reaction_emoji_unicode": None,
        "auto_reaction_channel_ids": [],
    }
    for role_id, expected in zip(roles, expected_settings, strict=True):
        response = await request(
            role_id,
            "PUT",
            "/api/v1/admin/settings/reactions",
            json=reaction_body,
        )
        assert response.status_code == expected

    for role_id, expected in zip(roles, expected_settings, strict=True):
        response = await request(
            role_id,
            "POST",
            "/api/v1/admin/discord/reactions/test",
            json={
                "kind": "seen",
                "channel_id": "111",
                "emoji_id": None,
                "emoji_unicode": "🎉",
            },
        )
        assert response.status_code == expected

    for role_id, expected in zip(roles, (403, 403, 201, 401), strict=True):
        response = await request(
            role_id,
            "POST",
            "/api/v1/admin/calendars",
            json={
                "external_calendar_id": "new@example.test",
                "display_name": "Nový kalendár",
                "priority": 50,
                "active": True,
            },
        )
        assert response.status_code == expected

    for role_id, expected in zip(roles, (403, 403, 200, 401), strict=True):
        response = await request(
            role_id,
            "PUT",
            "/api/v1/admin/discord/roles",
            json={"member_id": "123456789", "role": "team_mod", "enabled": True},
        )
        assert response.status_code == expected

    for role_id, expected in zip(roles, (201, 403, 201, 401), strict=True):
        response = await request(
            role_id,
            "POST",
            "/api/v1/admin/channels",
            json={
                "name": "matrix",
                "idempotency_key": f"matrix-{role_id}",
            },
        )
        assert response.status_code == expected

    malformed_member = await request(
        ADMIN_ROLE,
        "PUT",
        "/api/v1/admin/discord/roles",
        json={"member_id": "nie-id", "role": "team_mod", "enabled": True},
    )
    assert malformed_member.status_code == 422
    assert malformed_member.json()["code"] == "invalid_settings"

    await services.auth.close()
