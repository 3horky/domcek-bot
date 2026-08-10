"""Async Discord OAuth2 and guild-membership identity adapter."""

from __future__ import annotations

from typing import Any

import httpx

from domcek_bot.application.auth.contracts import (
    DiscordCodeRejected,
    DiscordGuildMember,
    DiscordIdentityError,
    DiscordMemberNotFound,
    DiscordOAuthToken,
    DiscordUser,
)

DISCORD_API = "https://discord.com/api/v10"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"  # noqa: S105


class DiscordHttpIdentityClient:
    def __init__(
        self,
        *,
        client_id: int,
        client_secret: str,
        redirect_uri: str,
        bot_token: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client_id = str(client_id)
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._bot_token = bot_token
        self._client = client or httpx.AsyncClient(timeout=10.0)
        self._owns_client = client is None

    async def exchange_code(self, code: str) -> DiscordOAuthToken:
        try:
            response = await self._client.post(
                DISCORD_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self._redirect_uri,
                },
                auth=(self._client_id, self._client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except httpx.HTTPError as exc:
            raise DiscordIdentityError("Discord token exchange is unavailable") from exc
        if response.status_code in {400, 401}:
            raise DiscordCodeRejected("Discord authorization code was rejected")
        if response.status_code != 200:
            raise DiscordIdentityError("Discord token exchange failed")
        payload = _object(response)
        try:
            access_token = str(payload["access_token"])
            token_type = str(payload["token_type"])
            expires_in = int(payload["expires_in"])
            scopes = frozenset(str(payload["scope"]).split())
        except (KeyError, TypeError, ValueError) as exc:
            raise DiscordIdentityError("Discord token response is malformed") from exc
        if not access_token or token_type.casefold() != "bearer" or expires_in <= 0:
            raise DiscordIdentityError("Discord token response is malformed")
        return DiscordOAuthToken(access_token, token_type, expires_in, scopes)

    async def current_user(self, access_token: str) -> DiscordUser:
        response = await self._get(
            f"{DISCORD_API}/users/@me", authorization=f"Bearer {access_token}"
        )
        return _user(_object(response))

    async def current_member(self, access_token: str, guild_id: int) -> DiscordGuildMember:
        response = await self._get(
            f"{DISCORD_API}/users/@me/guilds/{guild_id}/member",
            authorization=f"Bearer {access_token}",
            member_lookup=True,
        )
        return _member(_object(response), guild_id)

    async def guild_member(self, guild_id: int, user_id: int) -> DiscordGuildMember:
        response = await self._get(
            f"{DISCORD_API}/guilds/{guild_id}/members/{user_id}",
            authorization=f"Bot {self._bot_token}",
            member_lookup=True,
        )
        return _member(_object(response), guild_id)

    async def _get(
        self, url: str, *, authorization: str, member_lookup: bool = False
    ) -> httpx.Response:
        try:
            response = await self._client.get(url, headers={"Authorization": authorization})
        except httpx.HTTPError as exc:
            raise DiscordIdentityError("Discord identity API is unavailable") from exc
        if member_lookup and response.status_code == 404:
            raise DiscordMemberNotFound("Discord member was not found")
        if response.status_code != 200:
            raise DiscordIdentityError("Discord identity API request failed")
        return response

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def _object(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise DiscordIdentityError("Discord identity response is malformed") from exc
    if not isinstance(payload, dict):
        raise DiscordIdentityError("Discord identity response is malformed")
    return payload


def _user(payload: dict[str, Any]) -> DiscordUser:
    try:
        return DiscordUser(
            user_id=int(payload["id"]),
            username=str(payload["username"]),
            global_name=(
                None if payload.get("global_name") is None else str(payload["global_name"])
            ),
            avatar_hash=None if payload.get("avatar") is None else str(payload["avatar"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DiscordIdentityError("Discord user response is malformed") from exc


def _member(payload: dict[str, Any], guild_id: int) -> DiscordGuildMember:
    roles = payload.get("roles")
    user = payload.get("user")
    if not isinstance(roles, list) or not isinstance(user, dict):
        raise DiscordIdentityError("Discord member response is malformed")
    try:
        role_ids = frozenset(int(role) for role in roles)
    except (TypeError, ValueError) as exc:
        raise DiscordIdentityError("Discord member roles are malformed") from exc
    return DiscordGuildMember(
        user=_user(user),
        guild_id=guild_id,
        role_ids=role_ids,
        nickname=None if payload.get("nick") is None else str(payload["nick"]),
    )
