"""Discord REST adapter for web channel, role and reaction administration."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import httpx

from domcek_bot.application.channels import (
    ChannelOperationError,
    CreatedChannel,
    channel_alphabetical_key,
    channels_are_alphabetical,
)
from domcek_bot.application.discord_admin import (
    DiscordAdministrationError,
    DiscordChannelOption,
    DiscordDirectory,
    DiscordEmojiOption,
    DiscordMemberOption,
    DiscordRoleOption,
)

DISCORD_API = "https://discord.com/api/v10"
MANAGE_ROLES = 1 << 28
ADMINISTRATOR = 1 << 3
VIEW_CHANNEL = 1 << 10
READ_MESSAGE_HISTORY = 1 << 16
ADD_REACTIONS = 1 << 6
REQUIRED_REACTION_PERMISSIONS = VIEW_CHANNEL | READ_MESSAGE_HISTORY | ADD_REACTIONS
logger = logging.getLogger(__name__)


class DiscordHttpAdministrationGateway:
    def __init__(
        self,
        *,
        bot_token: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client = client or httpx.AsyncClient(timeout=15.0)
        self._owns_client = client is None
        self._headers = {"Authorization": f"Bot {bot_token}"}

    async def directory(self, guild_id: int) -> DiscordDirectory:
        channels_payload, roles_payload, emojis_payload = await self._parallel_directory(guild_id)
        text_counts: dict[int, int] = {}
        voice_counts: dict[int, int] = {}
        for item in channels_payload:
            parent_id = _optional_snowflake(item.get("parent_id"))
            if parent_id is None:
                continue
            if item.get("type") in {0, 5, 15, 16}:
                text_counts[parent_id] = text_counts.get(parent_id, 0) + 1
            elif item.get("type") in {2, 13}:
                voice_counts[parent_id] = voice_counts.get(parent_id, 0) + 1
        channels = tuple(
            DiscordChannelOption(
                id=_snowflake(item, "id"),
                name=str(item.get("name", "")),
                kind="category" if item.get("type") == 4 else "text",
                category_id=_optional_snowflake(item.get("parent_id")),
                text_channel_count=text_counts.get(_snowflake(item, "id"), 0),
                voice_channel_count=voice_counts.get(_snowflake(item, "id"), 0),
            )
            for item in channels_payload
            if item.get("type") in {0, 4}
        )

        roles = tuple(
            DiscordRoleOption(
                id=_snowflake(item, "id"),
                name=str(item.get("name", "")),
                position=int(item.get("position", 0)),
                managed=bool(item.get("managed", False)),
            )
            for item in roles_payload
        )
        emojis = tuple(
            DiscordEmojiOption(
                id=_snowflake(item, "id"),
                name=str(item.get("name", "")),
                animated=bool(item.get("animated", False)),
                available=bool(item.get("available", True)),
            )
            for item in emojis_payload
        )
        return DiscordDirectory(
            channels=tuple(sorted((item for item in channels if item.kind == "text"), key=_name)),
            categories=tuple(
                sorted((item for item in channels if item.kind == "category"), key=_name)
            ),
            roles=tuple(sorted(roles, key=lambda item: (-item.position, item.name.casefold()))),
            emojis=tuple(sorted(emojis, key=lambda item: item.name.casefold())),
        )

    async def category_allows_project_channel(self, *, guild_id: int, category_id: int) -> bool:
        channels = _objects(await self._json("GET", f"/guilds/{guild_id}/channels"))
        category_exists = any(
            item.get("type") == 4 and _snowflake(item, "id") == category_id for item in channels
        )
        has_voice_children = any(
            item.get("type") in {2, 13}
            and _optional_snowflake(item.get("parent_id")) == category_id
            for item in channels
        )
        return category_exists and not has_voice_children

    async def get_text_channel(self, *, guild_id: int, channel_id: int) -> CreatedChannel:
        payload = _object(await self._json("GET", f"/channels/{channel_id}"))
        if _optional_snowflake(payload.get("guild_id")) != guild_id or payload.get("type") != 0:
            raise ChannelOperationError("archive target is not a guild text channel")
        return CreatedChannel(
            channel_id,
            str(payload.get("name", "")),
            _jump_url(guild_id, channel_id),
            _optional_snowflake(payload.get("parent_id")),
        )

    async def channel_snapshot(self, *, guild_id: int, channel_id: int) -> dict[str, object] | None:
        try:
            response = await self._request("GET", f"/channels/{channel_id}", expected={200, 404})
        except DiscordAdministrationError as exc:
            raise ChannelOperationError("Discord channel could not be inspected") from exc
        if response.status_code == 404:
            return None
        payload = _object(response.json())
        if _optional_snowflake(payload.get("guild_id")) != guild_id or payload.get("type") != 0:
            raise ChannelOperationError("undo target is not a guild text channel")
        overwrites = payload.get("permission_overwrites", [])
        if not isinstance(overwrites, list):
            raise ChannelOperationError("Discord channel permissions are malformed")
        return {
            "id": str(channel_id),
            "name": str(payload.get("name", "")),
            "position": int(payload.get("position", 0)),
            "parent_id": payload.get("parent_id"),
            "topic": payload.get("topic"),
            "nsfw": bool(payload.get("nsfw", False)),
            "rate_limit_per_user": int(payload.get("rate_limit_per_user", 0)),
            "default_auto_archive_duration": payload.get("default_auto_archive_duration"),
            "permission_overwrites": sorted(
                (
                    {
                        "id": str(item.get("id", "")),
                        "type": int(item.get("type", 0)),
                        "allow": str(item.get("allow", "0")),
                        "deny": str(item.get("deny", "0")),
                    }
                    for item in overwrites
                    if isinstance(item, dict)
                ),
                key=lambda item: (item["type"], item["id"]),
            ),
            "last_message_id": payload.get("last_message_id"),
        }

    async def delete_text_channel(self, *, guild_id: int, channel_id: int, reason: str) -> None:
        await self.get_text_channel(guild_id=guild_id, channel_id=channel_id)
        await self._request(
            "DELETE",
            f"/channels/{channel_id}",
            headers={"X-Audit-Log-Reason": quote(reason[:512], safe="")},
            expected={200},
        )

    async def restore_text_channel(
        self,
        *,
        guild_id: int,
        channel_id: int,
        snapshot: dict[str, object],
        reason: str,
    ) -> CreatedChannel:
        await self.get_text_channel(guild_id=guild_id, channel_id=channel_id)
        payload = _object(
            await self._json(
                "PATCH",
                f"/channels/{channel_id}",
                json={
                    "name": snapshot["name"],
                    "position": snapshot.get("position"),
                    "parent_id": snapshot.get("parent_id"),
                    "topic": snapshot.get("topic"),
                    "nsfw": snapshot.get("nsfw", False),
                    "rate_limit_per_user": snapshot.get("rate_limit_per_user", 0),
                    "default_auto_archive_duration": snapshot.get("default_auto_archive_duration"),
                    "permission_overwrites": snapshot.get("permission_overwrites", []),
                },
                headers={"X-Audit-Log-Reason": quote(reason[:512], safe="")},
            )
        )
        return CreatedChannel(
            channel_id,
            str(payload.get("name", "")),
            _jump_url(guild_id, channel_id),
            _optional_snowflake(payload.get("parent_id")),
        )

    async def _parallel_directory(
        self, guild_id: int
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        import asyncio

        channels, roles, emojis = await asyncio.gather(
            self._json("GET", f"/guilds/{guild_id}/channels"),
            self._json("GET", f"/guilds/{guild_id}/roles"),
            self._json("GET", f"/guilds/{guild_id}/emojis"),
        )
        return _objects(channels), _objects(roles), _objects(emojis)

    async def search_members(
        self, guild_id: int, query: str, *, limit: int = 25
    ) -> tuple[DiscordMemberOption, ...]:
        payload = await self._json(
            "GET",
            f"/guilds/{guild_id}/members/search",
            params={"query": query, "limit": min(max(limit, 1), 100)},
        )
        return tuple(_member(item) for item in _objects(payload))

    async def get_member(self, guild_id: int, member_id: int) -> DiscordMemberOption:
        payload = await self._json("GET", f"/guilds/{guild_id}/members/{member_id}")
        return _member(_object(payload))

    async def validate_reaction_targets(
        self,
        guild_id: int,
        *,
        emoji_ids: tuple[int, ...],
        channel_ids: tuple[int, ...],
    ) -> None:
        channels, roles, emojis = await self._parallel_directory(guild_id)
        bot_user = _object(await self._json("GET", "/users/@me"))
        bot_id = _snowflake(bot_user, "id")
        bot_member = _object(await self._json("GET", f"/guilds/{guild_id}/members/{bot_id}"))
        available_emojis = {
            _snowflake(item, "id") for item in emojis if bool(item.get("available", True))
        }
        text_channels = {_snowflake(item, "id"): item for item in channels if item.get("type") == 0}
        if any(emoji_id not in available_emojis for emoji_id in emoji_ids):
            raise DiscordAdministrationError("selected server emoji is unavailable")
        if any(channel_id not in text_channels for channel_id in channel_ids):
            raise DiscordAdministrationError("selected reaction channel is unavailable")
        for channel_id in channel_ids:
            permissions = _channel_permissions(
                text_channels[channel_id],
                roles=roles,
                member=bot_member,
                guild_id=guild_id,
                member_id=bot_id,
            )
            if permissions & REQUIRED_REACTION_PERMISSIONS != REQUIRED_REACTION_PERMISSIONS:
                raise DiscordAdministrationError(
                    "Carlo lacks View Channel, Read Message History or Add Reactions"
                )

    async def validate_settings_targets(
        self,
        guild_id: int,
        *,
        channel_ids: tuple[int, ...],
        category_ids: tuple[int, ...],
    ) -> None:
        directory = await self.directory(guild_id)
        text_channels = {item.id for item in directory.channels}
        categories = {item.id for item in directory.categories}
        if any(channel_id not in text_channels for channel_id in channel_ids):
            raise DiscordAdministrationError(
                "selected settings channel is unavailable in the configured guild"
            )
        if any(category_id not in categories for category_id in category_ids):
            raise DiscordAdministrationError(
                "selected settings category is unavailable in the configured guild"
            )

    async def role_is_assignable(self, guild_id: int, role_id: int) -> bool:
        guild, roles, bot_member = await self._role_context(guild_id)
        target = next((item for item in roles if _snowflake(item, "id") == role_id), None)
        if target is None or bool(target.get("managed")) or role_id == guild_id:
            return False
        bot_role_ids = {_snowflake_value(value) for value in bot_member.get("roles", [])}
        bot_roles = [item for item in roles if _snowflake(item, "id") in bot_role_ids]
        permissions = 0
        for role in bot_roles:
            permissions |= int(role.get("permissions", "0"))
        bot_position = max((int(item.get("position", 0)) for item in bot_roles), default=0)
        can_manage = bool(permissions & (MANAGE_ROLES | ADMINISTRATOR))
        owner_id = _optional_snowflake(guild.get("owner_id"))
        bot_user = bot_member.get("user")
        is_owner = isinstance(bot_user, dict) and _snowflake(bot_user, "id") == owner_id
        return (can_manage or is_owner) and bot_position > int(target.get("position", 0))

    async def count_role_members(self, guild_id: int, role_id: int) -> int:
        count = 0
        after = 0
        while True:
            payload = await self._json(
                "GET",
                f"/guilds/{guild_id}/members",
                params={"limit": 1000, "after": after},
            )
            members = _objects(payload)
            count += sum(
                1
                for member in members
                if role_id in {_snowflake_value(value) for value in member.get("roles", [])}
            )
            if len(members) < 1000:
                return count
            after = max(_snowflake(item["user"], "id") for item in members)

    async def set_member_role(
        self, guild_id: int, member_id: int, role_id: int, *, enabled: bool, reason: str
    ) -> DiscordMemberOption:
        method = "PUT" if enabled else "DELETE"
        await self._request(
            method,
            f"/guilds/{guild_id}/members/{member_id}/roles/{role_id}",
            headers={"X-Audit-Log-Reason": quote(reason[:512], safe="")},
            expected={204},
        )
        payload = await self._json("GET", f"/guilds/{guild_id}/members/{member_id}")
        return _member(_object(payload))

    async def test_reaction(self, guild_id: int, channel_id: int, emoji: str) -> int:
        channel = await self._json("GET", f"/channels/{channel_id}")
        if _optional_snowflake(_object(channel).get("guild_id")) != guild_id:
            raise DiscordAdministrationError("reaction test channel belongs to another guild")
        message = _object(
            await self._json(
                "POST",
                f"/channels/{channel_id}/messages",
                json={
                    "content": "Carlo testuje túto reakciu. Túto správu môžete odstrániť.",
                    "allowed_mentions": {"parse": []},
                },
            )
        )
        message_id = _snowflake(message, "id")
        await self._request(
            "PUT",
            f"/channels/{channel_id}/messages/{message_id}/reactions/{quote(emoji, safe='')}/@me",
            expected={204},
        )
        return message_id

    async def create_text_channel(
        self,
        *,
        guild_id: int,
        category_id: int,
        name: str,
        member_ids: tuple[int, ...],
        role_ids: tuple[int, ...],
        operation_marker: str,
        reason: str,
    ) -> CreatedChannel:
        before_channels: list[dict[str, Any]] = []
        preserve_alphabetical_order = False
        try:
            before_channels = _category_text_channels(
                _objects(await self._json("GET", f"/guilds/{guild_id}/channels")), category_id
            )
            preserve_alphabetical_order = channels_are_alphabetical(
                tuple(str(item.get("name", "")) for item in before_channels)
            )
        except DiscordAdministrationError:
            logger.warning("Could not inspect the channel order before creation")
        allow = str((1 << 10) | (1 << 11) | (1 << 16) | (1 << 6))
        overwrites: list[dict[str, object]] = [
            {"id": str(guild_id), "type": 0, "deny": str(1 << 10), "allow": "0"}
        ]
        overwrites.extend(
            {"id": str(role_id), "type": 0, "allow": allow, "deny": "0"} for role_id in role_ids
        )
        overwrites.extend(
            {"id": str(member_id), "type": 1, "allow": allow, "deny": "0"}
            for member_id in member_ids
        )
        try:
            payload = _object(
                await self._json(
                    "POST",
                    f"/guilds/{guild_id}/channels",
                    json={
                        "name": name,
                        "type": 0,
                        "topic": _channel_operation_topic(operation_marker),
                        "parent_id": str(category_id),
                        "permission_overwrites": overwrites,
                    },
                    headers={"X-Audit-Log-Reason": quote(reason[:512], safe="")},
                )
            )
        except DiscordAdministrationError as exc:
            raise ChannelOperationError("Discord rejected channel creation") from exc
        channel_id = _snowflake(payload, "id")
        if preserve_alphabetical_order:
            try:
                await self._restore_alphabetical_category_order(
                    guild_id=guild_id,
                    category_id=category_id,
                    created_channel_id=channel_id,
                    before_channels=before_channels,
                    reason=reason,
                )
            except DiscordAdministrationError:
                # Channel creation already succeeded. Never retry that irreversible effect merely
                # because this best-effort cosmetic follow-up could not be completed.
                logger.warning("Could not preserve alphabetical Discord channel order")
        return CreatedChannel(
            channel_id,
            str(payload["name"]),
            _jump_url(guild_id, channel_id),
            _optional_snowflake(payload.get("parent_id")),
        )

    async def _restore_alphabetical_category_order(
        self,
        *,
        guild_id: int,
        category_id: int,
        created_channel_id: int,
        before_channels: list[dict[str, Any]],
        reason: str,
    ) -> None:
        after_channels = _category_text_channels(
            _objects(await self._json("GET", f"/guilds/{guild_id}/channels")), category_id
        )
        before_ids = [_snowflake(item, "id") for item in before_channels]
        after_ids = [_snowflake(item, "id") for item in after_channels]
        if set(after_ids) != {*before_ids, created_channel_id}:
            return
        if [
            channel_id for channel_id in after_ids if channel_id != created_channel_id
        ] != before_ids:
            return
        ordered = sorted(
            after_channels,
            key=lambda item: (
                channel_alphabetical_key(str(item.get("name", ""))),
                _snowflake(item, "id"),
            ),
        )
        ordered_ids = [_snowflake(item, "id") for item in ordered]
        if ordered_ids == after_ids:
            return
        first_position = min(int(item.get("position", 0)) for item in after_channels)
        await self._request(
            "PATCH",
            f"/guilds/{guild_id}/channels",
            json=[
                {"id": str(channel_id), "position": first_position + index}
                for index, channel_id in enumerate(ordered_ids)
            ],
            headers={"X-Audit-Log-Reason": quote(reason[:512], safe="")},
            expected={204},
        )

    async def find_created_text_channel(
        self,
        *,
        guild_id: int,
        category_id: int,
        operation_marker: str,
    ) -> CreatedChannel | None:
        expected_topic = _channel_operation_topic(operation_marker)
        channels = _objects(await self._json("GET", f"/guilds/{guild_id}/channels"))
        matches = [
            item
            for item in channels
            if item.get("type") == 0
            and _optional_snowflake(item.get("parent_id")) == category_id
            and item.get("topic") == expected_topic
        ]
        if len(matches) > 1:
            raise ChannelOperationError("multiple channels have the same operation marker")
        if not matches:
            return None
        channel_id = _snowflake(matches[0], "id")
        return CreatedChannel(
            channel_id,
            str(matches[0].get("name", "")),
            _jump_url(guild_id, channel_id),
            category_id,
        )

    async def archive_text_channel(
        self,
        *,
        guild_id: int,
        channel_id: int,
        archive_category_id: int,
        archived_name: str,
        reason: str,
    ) -> CreatedChannel:
        try:
            payload = _object(
                await self._json(
                    "PATCH",
                    f"/channels/{channel_id}",
                    json={
                        "name": archived_name,
                        "parent_id": str(archive_category_id),
                        "lock_permissions": True,
                    },
                    headers={"X-Audit-Log-Reason": quote(reason[:512], safe="")},
                )
            )
        except DiscordAdministrationError as exc:
            raise ChannelOperationError("Discord rejected channel archive") from exc
        return CreatedChannel(
            channel_id,
            str(payload["name"]),
            _jump_url(guild_id, channel_id),
            _optional_snowflake(payload.get("parent_id")),
        )

    async def _role_context(
        self, guild_id: int
    ) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
        import asyncio

        guild_payload, roles_payload, user_payload = await asyncio.gather(
            self._json("GET", f"/guilds/{guild_id}"),
            self._json("GET", f"/guilds/{guild_id}/roles"),
            self._json("GET", "/users/@me"),
        )
        bot_id = _snowflake(_object(user_payload), "id")
        member_payload = await self._json("GET", f"/guilds/{guild_id}/members/{bot_id}")
        return _object(guild_payload), _objects(roles_payload), _object(member_payload)

    async def _json(self, method: str, path: str, **kwargs: Any) -> object:
        response = await self._request(method, path, **kwargs)
        try:
            return response.json()
        except ValueError as exc:
            raise DiscordAdministrationError("Discord returned malformed JSON") from exc

    async def _request(
        self,
        method: str,
        path: str,
        *,
        expected: set[int] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        merged_headers = {**self._headers, **(headers or {})}
        try:
            response = await self._client.request(
                method, f"{DISCORD_API}{path}", headers=merged_headers, **kwargs
            )
        except httpx.HTTPError as exc:
            raise DiscordAdministrationError("Discord API is unavailable") from exc
        accepted = expected or set(range(200, 300))
        if response.status_code not in accepted:
            raise DiscordAdministrationError(
                f"Discord rejected administration request ({response.status_code})"
            )
        return response

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def _member(payload: dict[str, Any]) -> DiscordMemberOption:
    user = payload.get("user")
    if not isinstance(user, dict):
        raise DiscordAdministrationError("Discord member response is malformed")
    user_id = _snowflake(user, "id")
    username = str(user.get("username", ""))
    avatar = user.get("avatar")
    role_values = payload.get("roles", [])
    if not isinstance(role_values, list):
        raise DiscordAdministrationError("Discord member roles are malformed")
    display_name = str(payload.get("nick") or user.get("global_name") or username)
    avatar_url = (
        f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.png?size=64" if avatar else None
    )
    return DiscordMemberOption(
        id=user_id,
        username=username,
        display_name=display_name,
        avatar_url=avatar_url,
        role_ids=tuple(sorted(_snowflake_value(value) for value in role_values)),
        undo_id=None,
    )


def _channel_operation_topic(marker: str) -> str:
    return f"Carlo operation: {marker}"[:1024]


def _category_text_channels(
    channels: list[dict[str, Any]], category_id: int
) -> list[dict[str, Any]]:
    return sorted(
        (
            item
            for item in channels
            if item.get("type") == 0 and _optional_snowflake(item.get("parent_id")) == category_id
        ),
        key=lambda item: (int(item.get("position", 0)), _snowflake(item, "id")),
    )


def _channel_permissions(
    channel: dict[str, Any],
    *,
    roles: list[dict[str, Any]],
    member: dict[str, Any],
    guild_id: int,
    member_id: int,
) -> int:
    member_role_ids = {_snowflake_value(value) for value in member.get("roles", [])}
    applicable_role_ids = {guild_id, *member_role_ids}
    permissions = 0
    for role in roles:
        if _snowflake(role, "id") in applicable_role_ids:
            permissions |= int(role.get("permissions", "0"))
    if permissions & ADMINISTRATOR:
        return (1 << 53) - 1
    overwrites = channel.get("permission_overwrites", [])
    if not isinstance(overwrites, list):
        raise DiscordAdministrationError("Discord channel overwrites are malformed")
    everyone = next(
        (
            item
            for item in overwrites
            if isinstance(item, dict)
            and item.get("type") == 0
            and _optional_snowflake(item.get("id")) == guild_id
        ),
        None,
    )
    if everyone is not None:
        permissions = _apply_overwrite(permissions, everyone)
    role_allow = 0
    role_deny = 0
    for item in overwrites:
        if (
            isinstance(item, dict)
            and item.get("type") == 0
            and _optional_snowflake(item.get("id")) in member_role_ids
        ):
            role_allow |= int(item.get("allow", "0"))
            role_deny |= int(item.get("deny", "0"))
    permissions = (permissions & ~role_deny) | role_allow
    member_overwrite = next(
        (
            item
            for item in overwrites
            if isinstance(item, dict)
            and item.get("type") == 1
            and _optional_snowflake(item.get("id")) == member_id
        ),
        None,
    )
    return (
        _apply_overwrite(permissions, member_overwrite)
        if member_overwrite is not None
        else permissions
    )


def _apply_overwrite(permissions: int, overwrite: dict[str, Any]) -> int:
    return (permissions & ~int(overwrite.get("deny", "0"))) | int(overwrite.get("allow", "0"))


def _object(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise DiscordAdministrationError("Discord response is malformed")
    return payload


def _objects(payload: object) -> list[dict[str, Any]]:
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise DiscordAdministrationError("Discord response is malformed")
    return payload


def _snowflake(payload: dict[str, Any], key: str) -> int:
    try:
        value = int(payload[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise DiscordAdministrationError("Discord snowflake is malformed") from exc
    if value <= 0:
        raise DiscordAdministrationError("Discord snowflake is malformed")
    return value


def _snowflake_value(value: object) -> int:
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        raise DiscordAdministrationError("Discord snowflake is malformed")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise DiscordAdministrationError("Discord snowflake is malformed") from exc
    if result <= 0:
        raise DiscordAdministrationError("Discord snowflake is malformed")
    return int(result)


def _optional_snowflake(value: object) -> int | None:
    return None if value is None else _snowflake_value(value)


def _name(value: DiscordChannelOption) -> tuple[str, int]:
    return value.name.casefold(), value.id


def _jump_url(guild_id: int, channel_id: int) -> str:
    return f"https://discord.com/channels/{guild_id}/{channel_id}"
