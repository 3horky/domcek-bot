"""Discord REST delivery adapter with explicit retry-safety classification."""

from __future__ import annotations

import hashlib
import uuid
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
