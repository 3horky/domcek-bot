from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import cast
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from domcek_bot.api.app import create_app
from domcek_bot.api.dependencies import ApiServices
from domcek_bot.application.audit import AuditQueryService
from domcek_bot.application.auth.authorization import (
    AppRole,
    AuthorizationDenied,
    Capability,
    Principal,
    resolve_app_roles,
)
from domcek_bot.application.auth.contracts import (
    DiscordGuildMember,
    DiscordOAuthToken,
    DiscordUser,
)
from domcek_bot.application.auth.oauth_state import (
    InvalidOAuthState,
    OAuthStateCodec,
    safe_return_path,
)
from domcek_bot.application.auth.service import AuthService, GuildConfigurationMissing, LoginDenied
from domcek_bot.application.auth.session import InvalidSession, SessionService
from domcek_bot.application.bootstrap import ensure_guild_config
from domcek_bot.application.editor.content import ContentEditorialService
from domcek_bot.application.editor.events import (
    EditorialConflict,
    EventEditorialService,
    UpdateEventOverride,
)
from domcek_bot.application.publication.service import PublicationDraftService
from domcek_bot.application.records import (
    EventOverrideRecord,
    GuildConfigRecord,
    WebSessionRecord,
)
from domcek_bot.application.unit_of_work import RepositorySet, UnitOfWork
from domcek_bot.config import Settings
from domcek_bot.domain.enums import DescriptionState, InclusionDecision

GUILD_ID = 1535774834955391047
USER_ID = 1535771583841439765
TEAM_ROLE = 1535775387307745400
PUBLISHER_ROLE = 1535775015285559339
ADMIN_ROLE = 1535774886306390127
NOW = datetime(2026, 8, 9, 10, tzinfo=UTC)


class FakeGuildConfigs:
    def __init__(self, config: GuildConfigRecord | None) -> None:
        self.config = config

    async def get(self, guild_id: int) -> GuildConfigRecord | None:
        return self.config if self.config is not None and guild_id == self.config.guild_id else None

    async def add(self, record: GuildConfigRecord) -> None:
        self.config = record


class FakeWebSessions:
    def __init__(self) -> None:
        self.records: dict[uuid.UUID, WebSessionRecord] = {}

    async def add(self, record: WebSessionRecord) -> None:
        self.records[record.id] = record

    async def get_active_by_token_hash(
        self, token_hash: str, *, now: datetime
    ) -> WebSessionRecord | None:
        return next(
            (
                record
                for record in self.records.values()
                if record.session_token_hash == token_hash
                and record.revoked_at is None
                and record.expires_at > now
            ),
            None,
        )

    async def touch(self, session_id: uuid.UUID, *, seen_at: datetime) -> None:
        self.records[session_id] = replace(self.records[session_id], last_seen_at=seen_at)

    async def revoke(self, session_id: uuid.UUID, *, revoked_at: datetime) -> bool:
        record = self.records.get(session_id)
        if record is None or record.revoked_at is not None:
            return False
        self.records[session_id] = replace(record, revoked_at=revoked_at)
        return True


class FakeUnitOfWork:
    def __init__(self, config: GuildConfigRecord | None) -> None:
        self.guild_configs = FakeGuildConfigs(config)
        self.web_sessions = FakeWebSessions()

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[RepositorySet]:
        yield cast(RepositorySet, self)


class FakeDiscord:
    def __init__(self, role_ids: frozenset[int]) -> None:
        self.role_ids = role_ids
        self.closed = False
        self.scopes = frozenset({"identify", "guilds.members.read"})
        self.user = DiscordUser(USER_ID, "domcek-user", "Domček User", "avatar")

    async def exchange_code(self, code: str) -> DiscordOAuthToken:
        assert code == "valid-code"
        return DiscordOAuthToken(
            "access-token",
            "Bearer",
            3600,
            self.scopes,
        )

    async def current_user(self, access_token: str) -> DiscordUser:
        assert access_token == "access-token"
        return self.user

    async def current_member(self, access_token: str, guild_id: int) -> DiscordGuildMember:
        assert access_token == "access-token"
        return DiscordGuildMember(self.user, guild_id, self.role_ids, "Domček")

    async def guild_member(self, guild_id: int, user_id: int) -> DiscordGuildMember:
        assert user_id == USER_ID
        return DiscordGuildMember(self.user, guild_id, self.role_ids, "Domček")

    async def close(self) -> None:
        self.closed = True


class FakeDatabase:
    async def ping(self) -> None:
        return None

    async def close(self) -> None:
        return None


class CapturingEventEditor(EventEditorialService):
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        super().__init__(unit_of_work)
        self.conflict = False
        self.commands: list[UpdateEventOverride] = []

    async def update_instance(
        self,
        command: UpdateEventOverride,
        *,
        principal: Principal,
        correlation_id: str,
        now: datetime | None = None,
    ) -> EventOverrideRecord:
        del correlation_id, now
        self.commands.append(command)
        result = EventOverrideRecord(
            external_event_id=command.event_id,
            public_title=command.public_title,
            description_state=command.description_state,
            public_description=command.public_description,
            inclusion_decision=command.inclusion_decision or InclusionDecision.AUTO,
            updated_by_user_id=principal.user_id,
            version=1,
        )
        if self.conflict:
            raise EditorialConflict(result)
        return result


def _config() -> GuildConfigRecord:
    return GuildConfigRecord(
        guild_id=GUILD_ID,
        admin_role_id=ADMIN_ROLE,
        team_mod_role_id=TEAM_ROLE,
        publisher_role_id=PUBLISHER_ROLE,
    )


def _principal(role: AppRole) -> Principal:
    return Principal(
        guild_id=GUILD_ID,
        user_id=USER_ID,
        username="user",
        display_name="User",
        avatar_url=None,
        discord_role_ids=frozenset(),
        app_roles=frozenset({role}),
    )


def test_oauth_state_is_signed_expires_and_rejects_open_redirects() -> None:
    codec = OAuthStateCodec(secret="s" * 32, lifetime=timedelta(minutes=10))
    issued = codec.issue("/oznamy?tab=info", now=NOW)

    assert codec.verify(issued.value, issued.value, now=NOW).return_to == "/oznamy?tab=info"
    with pytest.raises(InvalidOAuthState, match="expired"):
        codec.verify(issued.value, issued.value, now=NOW + timedelta(minutes=11))
    with pytest.raises(InvalidOAuthState, match="does not match"):
        codec.verify(issued.value, "different", now=NOW)
    for unsafe in ("https://evil.test", "//evil.test", "/\\evil", "/ok\nLocation: evil"):
        with pytest.raises(InvalidOAuthState):
            safe_return_path(unsafe)


@pytest.mark.parametrize(
    ("role", "allowed", "denied"),
    [
        (AppRole.TEAM_MOD, Capability.EDIT_CONTENT, Capability.MANUAL_PUBLISH),
        (AppRole.PUBLISHER, Capability.MANUAL_PUBLISH, Capability.EDIT_CONTENT),
        (AppRole.ADMIN, Capability.MANAGE_ROLES, None),
    ],
)
def test_authorization_matrix(
    role: AppRole,
    allowed: Capability,
    denied: Capability | None,
) -> None:
    principal = _principal(role)
    principal.require(allowed)
    if denied is not None:
        with pytest.raises(AuthorizationDenied):
            principal.require(denied)

    discord_role = {
        AppRole.TEAM_MOD: TEAM_ROLE,
        AppRole.PUBLISHER: PUBLISHER_ROLE,
        AppRole.ADMIN: ADMIN_ROLE,
    }[role]
    assert role in resolve_app_roles(frozenset({discord_role}), _config())


async def test_initial_guild_bootstrap_is_idempotent_and_never_overwrites() -> None:
    fake_uow = FakeUnitOfWork(None)
    desired = _config()

    assert await ensure_guild_config(cast(UnitOfWork, fake_uow), desired) is True
    assert fake_uow.guild_configs.config == desired

    changed = replace(desired, closing_message="Uložené vo webovej administrácii")
    fake_uow.guild_configs.config = changed
    assert await ensure_guild_config(cast(UnitOfWork, fake_uow), desired) is False
    assert fake_uow.guild_configs.config == changed


async def test_session_token_and_csrf_are_hashed_and_revocable() -> None:
    fake_uow = FakeUnitOfWork(_config())
    service = SessionService(
        cast(UnitOfWork, fake_uow), secret="s" * 32, lifetime=timedelta(hours=12)
    )

    issued = await service.create(guild_id=GUILD_ID, user_id=USER_ID, now=NOW)

    assert issued.session_token not in issued.record.session_token_hash
    assert issued.csrf_token not in issued.record.csrf_token_hash
    loaded = await service.authenticate(issued.session_token, now=NOW)
    service.verify_csrf(loaded, issued.csrf_token, issued.csrf_token)
    with pytest.raises(InvalidSession):
        service.verify_csrf(loaded, issued.csrf_token, "wrong")
    with pytest.raises(InvalidSession):
        await service.authenticate(issued.session_token, now=NOW + timedelta(hours=12))
    await service.revoke(loaded, now=NOW)
    with pytest.raises(InvalidSession):
        await service.authenticate(issued.session_token, now=NOW)


def test_http_oauth_session_csrf_logout_and_security_headers(settings: Settings) -> None:
    configured = settings.model_copy(
        update={
            "discord_application_id": USER_ID,
            "discord_oauth_client_id": USER_ID,
            "discord_guild_id": GUILD_ID,
            "discord_oauth_client_secret": "oauth-secret",
            "discord_bot_token": "bot-token",
            "api_oauth_rate_limit": 1,
        }
    )
    fake_uow = FakeUnitOfWork(_config())
    unit_of_work = cast(UnitOfWork, fake_uow)
    discord = FakeDiscord(frozenset({TEAM_ROLE}))
    session_service = SessionService(
        unit_of_work,
        secret=configured.session_secret_value(),
        lifetime=timedelta(hours=12),
    )
    event_editor = CapturingEventEditor(unit_of_work)
    api_services = ApiServices(
        auth=AuthService(unit_of_work, discord, session_service, guild_id=GUILD_ID),
        sessions=session_service,
        oauth_state=OAuthStateCodec(
            secret=configured.session_secret_value(), lifetime=timedelta(minutes=10)
        ),
        publication_drafts=PublicationDraftService(unit_of_work),
        event_editor=event_editor,
        content_editor=ContentEditorialService(unit_of_work),
        audit=AuditQueryService(unit_of_work),
    )

    with TestClient(
        create_app(
            settings=configured,
            database=FakeDatabase(),
            services=api_services,
        )
    ) as client:
        login = client.get(
            "/api/v1/auth/discord/login?return_to=/oznamy",
            follow_redirects=False,
        )
        assert login.status_code == 302
        query = parse_qs(urlsplit(login.headers["location"]).query)
        assert set(query["scope"][0].split()) == {"identify", "guilds.members.read"}
        assert query["redirect_uri"] == [configured.discord_oauth_redirect_uri]
        state_cookie = "\n".join(login.headers.get_list("set-cookie"))
        assert "domcek_oauth_state=" in state_cookie
        assert "HttpOnly" in state_cookie
        assert "Path=/api/v1/auth/discord/callback" in state_cookie
        assert "SameSite=lax" in state_cookie

        limited = client.get("/api/v1/auth/discord/login", follow_redirects=False)
        assert limited.status_code == 429
        assert limited.json()["code"] == "rate_limited"
        assert int(limited.headers["retry-after"]) >= 1
        assert limited.headers["cache-control"] == "no-store"
        assert limited.headers["x-frame-options"] == "DENY"
        assert limited.headers["x-correlation-id"] == limited.json()["correlation_id"]

        callback = client.get(
            "/api/v1/auth/discord/callback",
            params={"code": "valid-code", "state": query["state"][0]},
            follow_redirects=False,
        )
        assert callback.status_code == 303
        assert callback.headers["location"] == "http://localhost:5173/oznamy"
        assert "access-token" not in callback.headers.get("set-cookie", "")
        callback_cookies = callback.headers.get_list("set-cookie")
        session_cookie = next(
            value for value in callback_cookies if value.startswith("domcek_session=")
        )
        csrf_cookie = next(value for value in callback_cookies if value.startswith("domcek_csrf="))
        assert "HttpOnly" in session_cookie
        assert "HttpOnly" not in csrf_cookie
        assert "SameSite=lax" in session_cookie
        assert "SameSite=lax" in csrf_cookie

        session = client.get("/api/v1/session")
        assert session.status_code == 200
        assert session.json()["roles"] == ["team_mod"]
        assert session.headers["x-frame-options"] == "DENY"
        assert session.headers["content-security-policy"].startswith("default-src 'none'")
        assert session.headers["cache-control"] == "no-store"

        cors = client.get(
            "/api/v1/session",
            headers={"Origin": configured.allowed_origin_list[0]},
        )
        assert cors.headers["access-control-allow-origin"] == configured.allowed_origin_list[0]
        rejected_origin = client.get("/api/v1/session", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in rejected_origin.headers
        preflight = client.options(
            "/api/v1/events/example/override",
            headers={
                "Origin": configured.allowed_origin_list[0],
                "Access-Control-Request-Method": "PUT",
                "Access-Control-Request-Headers": "X-CSRF-Token,Content-Type",
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-credentials"] == "true"

        unsafe_marker = "TOP_SECRET_INVALID_INPUT"
        invalid = client.put(
            f"/api/v1/events/{uuid.uuid4()}/override",
            headers={"X-CSRF-Token": client.cookies.get("domcek_csrf") or ""},
            json={"expected_version": 0, "unexpected": unsafe_marker},
        )
        assert invalid.status_code == 422
        assert invalid.headers["content-type"] == "application/problem+json; charset=utf-8"
        assert invalid.json()["code"] == "request_validation_failed"
        assert unsafe_marker not in invalid.text
        missing = client.get("/api/v1/does-not-exist")
        assert missing.status_code == 404
        assert missing.json()["code"] == "not_found"

        event_id = uuid.uuid4()
        csrf = client.cookies.get("domcek_csrf") or ""
        saved = client.put(
            f"/api/v1/events/{event_id}/override",
            headers={"X-CSRF-Token": csrf, "X-Correlation-ID": "editor-save"},
            json={
                "expected_version": 0,
                "public_title": "Web titulok",
                "description_state": "custom",
                "public_description": "Web popis",
            },
        )
        assert saved.status_code == 200
        assert saved.json()["version"] == 1
        assert event_editor.commands[0].description_state is DescriptionState.CUSTOM

        event_editor.conflict = True
        conflict = client.put(
            f"/api/v1/events/{event_id}/override",
            headers={"X-CSRF-Token": csrf},
            json={
                "expected_version": 0,
                "public_title": "Stará zmena",
                "description_state": "inherit",
            },
        )
        assert conflict.status_code == 409
        assert conflict.json()["code"] == "version_conflict"
        assert conflict.json()["current"]["version"] == 1

        rejected_logout = client.post("/api/v1/auth/logout")
        assert rejected_logout.status_code == 403
        logout = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
        assert logout.status_code == 204
        assert client.get("/api/v1/session").status_code == 401

    assert discord.closed


def test_http_login_reports_missing_server_configuration_as_service_failure(
    settings: Settings,
) -> None:
    configured = settings.model_copy(
        update={
            "discord_application_id": USER_ID,
            "discord_oauth_client_id": USER_ID,
            "discord_guild_id": GUILD_ID,
            "discord_oauth_client_secret": "oauth-secret",
            "discord_bot_token": "bot-token",
        }
    )
    fake_uow = FakeUnitOfWork(None)
    unit_of_work = cast(UnitOfWork, fake_uow)
    discord = FakeDiscord(frozenset({ADMIN_ROLE}))
    session_service = SessionService(
        unit_of_work,
        secret=configured.session_secret_value(),
        lifetime=timedelta(hours=12),
    )
    api_services = ApiServices(
        auth=AuthService(unit_of_work, discord, session_service, guild_id=GUILD_ID),
        sessions=session_service,
        oauth_state=OAuthStateCodec(
            secret=configured.session_secret_value(), lifetime=timedelta(minutes=10)
        ),
        publication_drafts=PublicationDraftService(unit_of_work),
        event_editor=EventEditorialService(unit_of_work),
        content_editor=ContentEditorialService(unit_of_work),
        audit=AuditQueryService(unit_of_work),
    )

    with TestClient(
        create_app(settings=configured, database=FakeDatabase(), services=api_services)
    ) as client:
        login = client.get("/api/v1/auth/discord/login", follow_redirects=False)
        state = parse_qs(urlsplit(login.headers["location"]).query)["state"][0]
        callback = client.get(
            "/api/v1/auth/discord/callback",
            params={"code": "valid-code", "state": state},
            follow_redirects=False,
        )

    assert callback.status_code == 503
    assert callback.json()["code"] == "guild_not_configured"
    assert callback.json()["title"] == "Carlo ešte nie je pripravený"
    assert "nemá prístup" not in callback.text
    assert not fake_uow.web_sessions.records


async def test_login_rejects_missing_scope_and_missing_admin_role() -> None:
    fake_uow = FakeUnitOfWork(_config())
    unit_of_work = cast(UnitOfWork, fake_uow)
    sessions = SessionService(
        unit_of_work,
        secret="s" * 32,
        lifetime=timedelta(hours=12),
    )
    discord = FakeDiscord(frozenset({TEAM_ROLE}))
    auth = AuthService(unit_of_work, discord, sessions, guild_id=GUILD_ID)

    discord.scopes = frozenset({"identify"})
    with pytest.raises(LoginDenied, match="scope"):
        await auth.login("valid-code")
    assert not fake_uow.web_sessions.records

    discord.scopes = frozenset({"identify", "guilds.members.read"})
    discord.role_ids = frozenset()
    with pytest.raises(LoginDenied, match="administration role"):
        await auth.login("valid-code")
    assert not fake_uow.web_sessions.records


async def test_login_distinguishes_missing_server_configuration_from_missing_user_role() -> None:
    fake_uow = FakeUnitOfWork(None)
    unit_of_work = cast(UnitOfWork, fake_uow)
    sessions = SessionService(
        unit_of_work,
        secret="s" * 32,
        lifetime=timedelta(hours=12),
    )
    discord = FakeDiscord(frozenset({ADMIN_ROLE}))
    auth = AuthService(unit_of_work, discord, sessions, guild_id=GUILD_ID)

    with pytest.raises(GuildConfigurationMissing, match="configuration is missing"):
        await auth.login("valid-code")
    assert not fake_uow.web_sessions.records
