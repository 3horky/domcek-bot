from __future__ import annotations

import httpx
import pytest

from domcek_bot.application.discord_admin import DiscordAdministrationError
from domcek_bot.infrastructure.discord_admin import (
    ADD_REACTIONS,
    READ_MESSAGE_HISTORY,
    VIEW_CHANNEL,
    DiscordHttpAdministrationGateway,
)

GUILD_ID = 1535774834955391047
CHANNEL_ID = 1535774834955391048
BOT_ID = 1535774834955391049
BOT_ROLE_ID = 1535774834955391050


def _discord_transport(*, permissions: int) -> httpx.MockTransport:
    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == f"/api/v10/guilds/{GUILD_ID}/channels":
            payload: object = [
                {
                    "id": str(CHANNEL_ID),
                    "name": "oznamy",
                    "type": 0,
                    "permission_overwrites": [],
                }
            ]
        elif path == f"/api/v10/guilds/{GUILD_ID}/roles":
            payload = [
                {
                    "id": str(GUILD_ID),
                    "name": "@everyone",
                    "permissions": str(permissions),
                    "position": 0,
                },
                {
                    "id": str(BOT_ROLE_ID),
                    "name": "Carlo",
                    "permissions": "0",
                    "position": 1,
                },
            ]
        elif path == f"/api/v10/guilds/{GUILD_ID}/emojis":
            payload = []
        elif path == "/api/v10/users/@me":
            payload = {"id": str(BOT_ID), "username": "Carlo"}
        elif path == f"/api/v10/guilds/{GUILD_ID}/members/{BOT_ID}":
            payload = {
                "user": {"id": str(BOT_ID), "username": "Carlo"},
                "roles": [str(BOT_ROLE_ID)],
            }
        else:  # pragma: no cover - makes an unexpected Discord call obvious
            return httpx.Response(404, json={"path": path})
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_reaction_validation_requires_all_channel_permissions() -> None:
    permissions = VIEW_CHANNEL | READ_MESSAGE_HISTORY
    async with httpx.AsyncClient(transport=_discord_transport(permissions=permissions)) as client:
        gateway = DiscordHttpAdministrationGateway(bot_token="test", client=client)
        with pytest.raises(DiscordAdministrationError, match="Add Reactions"):
            await gateway.validate_reaction_targets(
                GUILD_ID,
                emoji_ids=(),
                channel_ids=(CHANNEL_ID,),
            )


@pytest.mark.asyncio
async def test_reaction_validation_accepts_complete_channel_permissions() -> None:
    permissions = VIEW_CHANNEL | READ_MESSAGE_HISTORY | ADD_REACTIONS
    async with httpx.AsyncClient(transport=_discord_transport(permissions=permissions)) as client:
        gateway = DiscordHttpAdministrationGateway(bot_token="test", client=client)
        await gateway.validate_reaction_targets(
            GUILD_ID,
            emoji_ids=(),
            channel_ids=(CHANNEL_ID,),
        )
