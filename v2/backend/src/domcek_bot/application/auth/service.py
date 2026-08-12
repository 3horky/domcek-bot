"""Discord login and current-principal orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from domcek_bot.application.auth.authorization import Principal, resolve_app_roles
from domcek_bot.application.auth.contracts import DiscordIdentityClient, DiscordUser
from domcek_bot.application.auth.session import IssuedSession, SessionService
from domcek_bot.application.records import WebSessionRecord
from domcek_bot.application.unit_of_work import UnitOfWork

REQUIRED_OAUTH_SCOPES = frozenset({"identify", "guilds.members.read"})


class LoginDenied(PermissionError):
    pass


class GuildConfigurationMissing(RuntimeError):
    """The server cannot authorize anyone because its role mapping is unavailable."""


@dataclass(frozen=True, slots=True)
class LoginResult:
    session: IssuedSession
    principal: Principal


class AuthService:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        discord: DiscordIdentityClient,
        sessions: SessionService,
        *,
        guild_id: int,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._discord = discord
        self._sessions = sessions
        self._guild_id = guild_id

    async def close(self) -> None:
        await self._discord.close()

    async def login(self, code: str) -> LoginResult:
        token = await self._discord.exchange_code(code)
        if not REQUIRED_OAUTH_SCOPES <= token.scopes:
            raise LoginDenied("Discord authorization is missing a required scope")
        user = await self._discord.current_user(token.access_token)
        member = await self._discord.current_member(token.access_token, self._guild_id)
        if member.user.user_id != user.user_id:
            raise LoginDenied("Discord identity and membership do not match")
        principal = await self._principal(member.user, member.role_ids, member.nickname)
        if not principal.app_roles:
            raise LoginDenied("Discord member has no administration role")
        session = await self._sessions.create(guild_id=self._guild_id, user_id=user.user_id)
        return LoginResult(session=session, principal=principal)

    async def principal_for_session(
        self, session_token: str | None
    ) -> tuple[WebSessionRecord, Principal]:
        record = await self._sessions.authenticate(session_token)
        member = await self._discord.guild_member(record.guild_id, record.discord_user_id)
        principal = await self._principal(member.user, member.role_ids, member.nickname)
        if not principal.app_roles:
            raise LoginDenied("Discord member no longer has an administration role")
        return record, principal

    async def _principal(
        self,
        user: DiscordUser,
        role_ids: frozenset[int],
        nickname: str | None,
    ) -> Principal:
        async with self._unit_of_work.transaction() as repositories:
            config = await repositories.guild_configs.get(self._guild_id)
        if config is None:
            raise GuildConfigurationMissing("guild configuration is missing")
        roles = resolve_app_roles(role_ids, config)
        avatar_url = (
            None
            if user.avatar_hash is None
            else f"https://cdn.discordapp.com/avatars/{user.user_id}/{user.avatar_hash}.png"
        )
        return Principal(
            guild_id=self._guild_id,
            user_id=user.user_id,
            username=user.username,
            display_name=nickname or user.global_name or user.username,
            avatar_url=avatar_url,
            discord_role_ids=role_ids,
            app_roles=roles,
        )
