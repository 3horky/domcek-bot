from __future__ import annotations

from urllib.parse import parse_qs

import httpx
import pytest

from domcek_bot.application.auth.contracts import DiscordCodeRejected, DiscordMemberNotFound
from domcek_bot.infrastructure.discord_identity import DiscordHttpIdentityClient


async def test_oauth_exchange_and_user_membership_use_minimal_credentials() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/oauth2/token":
            form = parse_qs(request.content.decode())
            assert form == {
                "grant_type": ["authorization_code"],
                "code": ["one-use-code"],
                "redirect_uri": ["http://localhost:8000/api/v1/auth/discord/callback"],
            }
            assert request.headers["content-type"].startswith("application/x-www-form-urlencoded")
            return httpx.Response(
                200,
                json={
                    "access_token": "short-lived-access",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "scope": "identify guilds.members.read",
                },
            )
        if request.url.path == "/api/v10/users/@me":
            assert request.headers["authorization"] == "Bearer short-lived-access"
            return httpx.Response(
                200,
                json={
                    "id": "123",
                    "username": "user",
                    "global_name": "User",
                    "avatar": None,
                },
            )
        if request.url.path == "/api/v10/users/@me/guilds/456/member":
            return httpx.Response(
                200,
                json={
                    "user": {"id": "123", "username": "user", "avatar": None},
                    "roles": ["789"],
                    "nick": "Member",
                },
            )
        if request.url.path == "/api/v10/guilds/456/members/123":
            assert request.headers["authorization"] == "Bot bot-secret"
            return httpx.Response(
                200,
                json={
                    "user": {"id": "123", "username": "user", "avatar": None},
                    "roles": ["789"],
                },
            )
        raise AssertionError(f"unexpected request: {request.url}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = DiscordHttpIdentityClient(
            client_id=111,
            client_secret="oauth-secret",
            redirect_uri="http://localhost:8000/api/v1/auth/discord/callback",
            bot_token="bot-secret",
            client=http,
        )
        token = await client.exchange_code("one-use-code")
        user = await client.current_user(token.access_token)
        current = await client.current_member(token.access_token, 456)
        refreshed = await client.guild_member(456, user.user_id)

    assert token.scopes == frozenset({"identify", "guilds.members.read"})
    assert current.role_ids == refreshed.role_ids == frozenset({789})
    assert len(requests) == 4


async def test_provider_rejections_are_mapped_without_response_payloads() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/oauth2/token":
            return httpx.Response(400, json={"error": "invalid_grant", "secret": "never expose"})
        return httpx.Response(404, json={"message": "Unknown Member"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = DiscordHttpIdentityClient(
            client_id=111,
            client_secret="oauth-secret",
            redirect_uri="http://localhost/callback",
            bot_token="bot-secret",
            client=http,
        )
        with pytest.raises(DiscordCodeRejected) as rejected:
            await client.exchange_code("bad")
        with pytest.raises(DiscordMemberNotFound):
            await client.guild_member(456, 123)

    assert "never expose" not in str(rejected.value)
