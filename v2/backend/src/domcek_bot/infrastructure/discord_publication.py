"""Discord REST delivery adapter with explicit retry-safety classification."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from urllib.parse import quote

import httpx

from domcek_bot.application.publication.engine import (
    DiscordAmbiguousError,
    DiscordDefinitiveError,
    DiscordTransientError,
)
from domcek_bot.application.records import PublicationMessageRecord

DISCORD_API_BASE = "https://discord.com/api/v10"


class DiscordHttpPublicationGateway:
    def __init__(self, *, bot_token: str, timeout_seconds: float = 15.0) -> None:
        self._client = httpx.AsyncClient(
            base_url=DISCORD_API_BASE,
            headers={"Authorization": f"Bot {bot_token}"},
            timeout=timeout_seconds,
        )

    async def send_message(self, message: PublicationMessageRecord) -> int:
        payload: dict[str, object] = {
            "nonce": message.nonce,
            "enforce_nonce": True,
            "embeds": list(message.embeds),
            "allowed_mentions": {"parse": list(message.allowed_mentions)},
        }
        if message.content is not None:
            payload["content"] = message.content
        try:
            response = await self._client.post(
                f"/channels/{message.discord_channel_id}/messages", json=payload
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise DiscordAmbiguousError("Discord request ended without confirmation") from exc
        if response.status_code == 429:
            retry_after = _retry_after(response)
            raise DiscordTransientError("Discord rate limit", retry_after=retry_after)
        if response.status_code >= 500:
            raise DiscordAmbiguousError(
                f"Discord server error without effect confirmation ({response.status_code})"
            )
        if response.status_code >= 400:
            raise DiscordDefinitiveError(
                f"Discord rejected message ({response.status_code}, {_discord_code(response)})"
            )
        response_payload: object = response.json()
        try:
            if not isinstance(response_payload, dict):
                raise TypeError
            message_id = response_payload["id"]
            if not isinstance(message_id, (str, int)) or isinstance(message_id, bool):
                raise TypeError
            return int(message_id)
        except (KeyError, TypeError, ValueError) as exc:
            raise DiscordAmbiguousError("Discord success response has no message ID") from exc

    async def add_reaction(self, *, channel_id: int, message_id: int, emoji: str) -> None:
        try:
            encoded_emoji = quote(emoji, safe="")
            response = await self._client.put(
                f"/channels/{channel_id}/messages/{message_id}/reactions/{encoded_emoji}/@me"
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise DiscordAmbiguousError("Discord reaction result is unknown") from exc
        if response.status_code == 429:
            raise DiscordTransientError(
                "Discord reaction rate limit", retry_after=_retry_after(response)
            )
        if response.status_code >= 400:
            raise DiscordDefinitiveError(
                f"Discord rejected reaction ({response.status_code}, {_discord_code(response)})"
            )

    async def close(self) -> None:
        await self._client.aclose()


class DiscordHttpPublicationGuardGateway:
    def __init__(
        self, *, bot_token: str, frontend_base_url: str, timeout_seconds: float = 10.0
    ) -> None:
        self._frontend_base_url = frontend_base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=DISCORD_API_BASE,
            headers={"Authorization": f"Bot {bot_token}"},
            timeout=timeout_seconds,
        )

    async def admin_member_ids(self, guild_id: int, admin_role_id: int) -> tuple[int, ...]:
        after = 0
        members: list[int] = []
        while True:
            response = await self._client.get(
                f"/guilds/{guild_id}/members",
                params={"limit": 1000, "after": after},
            )
            response.raise_for_status()
            payload: object = response.json()
            if not isinstance(payload, list):
                raise RuntimeError("Discord member response is malformed")
            for item in payload:
                if not isinstance(item, dict):
                    continue
                roles = item.get("roles")
                user = item.get("user")
                if (
                    isinstance(roles, list)
                    and str(admin_role_id) in {str(role) for role in roles}
                    and isinstance(user, dict)
                    and isinstance(user.get("id"), str)
                ):
                    members.append(int(user["id"]))
            if len(payload) < 1000:
                return tuple(dict.fromkeys(members))
            last = payload[-1]
            if not isinstance(last, dict) or not isinstance(last.get("user"), dict):
                raise RuntimeError("Discord member pagination is malformed")
            after = int(last["user"]["id"])

    async def send_guard_dm(
        self,
        *,
        recipient_user_id: int,
        run_id: uuid.UUID,
        release_at: datetime,
        nonce: str,
    ) -> tuple[int, int]:
        channel_response = await self._client.post(
            "/users/@me/channels", json={"recipient_id": str(recipient_user_id)}
        )
        channel_response.raise_for_status()
        channel = channel_response.json()
        if not isinstance(channel, dict) or not isinstance(channel.get("id"), str):
            raise RuntimeError("Discord DM channel response is malformed")
        channel_id = int(channel["id"])
        message_response = await self._client.post(
            f"/channels/{channel_id}/messages",
            json={
                "content": (
                    "**Carlo čaká pred zverejnením oznamov**\n"
                    f"Ak chcete publikovanie zastaviť, napíšte sem `stop` pred "
                    f"<t:{int(release_at.timestamp())}:T>.\n"
                    f"[Otvoriť administráciu]({self._frontend_base_url}/?guard={run_id})"
                ),
                "nonce": nonce,
                "enforce_nonce": True,
                "allowed_mentions": {"parse": []},
                "components": [
                    {
                        "type": 1,
                        "components": [
                            {
                                "type": 2,
                                "style": 4,
                                "label": "Zastaviť publikovanie",
                                "custom_id": f"guard:stop:{run_id}",
                            }
                        ],
                    }
                ],
            },
        )
        message_response.raise_for_status()
        message = message_response.json()
        if not isinstance(message, dict) or not isinstance(message.get("id"), str):
            raise RuntimeError("Discord DM response is malformed")
        return channel_id, int(message["id"])

    async def delete_guard_dm(self, *, channel_id: int, message_id: int) -> None:
        response = await self._client.delete(f"/channels/{channel_id}/messages/{message_id}")
        if response.status_code not in {204, 404}:
            response.raise_for_status()

    async def close(self) -> None:
        await self._client.aclose()


class DiscordModeratorAlertGateway:
    def __init__(
        self,
        *,
        bot_token: str,
        frontend_base_url: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._frontend_base_url = frontend_base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=DISCORD_API_BASE,
            headers={"Authorization": f"Bot {bot_token}"},
            timeout=timeout_seconds,
        )

    async def send_alert(
        self,
        *,
        guild_id: int,
        moderator_channel_id: int | None,
        title: str,
        summary: str,
        correlation_id: str,
        run_id: uuid.UUID | None,
    ) -> None:
        del guild_id
        if moderator_channel_id is None:
            return
        link = (
            f"{self._frontend_base_url}/historia?run={run_id}#run-{run_id}"
            if run_id is not None
            else f"{self._frontend_base_url}/audit"
        )
        content = (
            f"**{title}**\n{summary}\n"
            f"Korelačné ID: `{correlation_id}`\n"
            f"[Otvoriť administráciu]({link})"
        )[:2000]
        nonce = hashlib.sha256(f"alert:{correlation_id}:{run_id or 'none'}".encode()).hexdigest()[
            :25
        ]
        try:
            response = await self._client.post(
                f"/channels/{moderator_channel_id}/messages",
                json={
                    "content": content,
                    "nonce": nonce,
                    "enforce_nonce": True,
                    "allowed_mentions": {"parse": []},
                },
            )
        except (httpx.TimeoutException, httpx.NetworkError):
            return
        # Alert delivery must never recursively fail the primary publication.
        if response.status_code == 429:
            return

    async def close(self) -> None:
        await self._client.aclose()


def _retry_after(response: httpx.Response) -> float:
    try:
        value = float(response.json().get("retry_after", 1.0))
    except (TypeError, ValueError):
        value = 1.0
    return min(max(value, 0.0), 60.0)


def _discord_code(response: httpx.Response) -> str:
    try:
        return str(response.json().get("code", "unknown"))[:40]
    except ValueError:
        return "unknown"
