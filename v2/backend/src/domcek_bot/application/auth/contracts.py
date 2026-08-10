"""Provider-neutral Discord identity contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class DiscordIdentityError(RuntimeError):
    """Safe provider failure exposed to the application layer."""


class DiscordCodeRejected(DiscordIdentityError):
    pass


class DiscordMemberNotFound(DiscordIdentityError):
    pass


@dataclass(frozen=True, slots=True)
class DiscordOAuthToken:
    access_token: str
    token_type: str
    expires_in: int
    scopes: frozenset[str]


@dataclass(frozen=True, slots=True)
class DiscordUser:
    user_id: int
    username: str
    global_name: str | None
    avatar_hash: str | None


@dataclass(frozen=True, slots=True)
class DiscordGuildMember:
    user: DiscordUser
    guild_id: int
    role_ids: frozenset[int]
    nickname: str | None = None


class DiscordIdentityClient(Protocol):
    async def exchange_code(self, code: str) -> DiscordOAuthToken: ...

    async def current_user(self, access_token: str) -> DiscordUser: ...

    async def current_member(self, access_token: str, guild_id: int) -> DiscordGuildMember: ...

    async def guild_member(self, guild_id: int, user_id: int) -> DiscordGuildMember: ...

    async def close(self) -> None: ...
