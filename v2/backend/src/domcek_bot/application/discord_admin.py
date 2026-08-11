"""Shared web/Discord administration use cases for guild resources and roles."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from domcek_bot.application.alerts import ModeratorAlertTransport
from domcek_bot.application.audit import AuditWriter
from domcek_bot.application.auth.authorization import Capability, Principal
from domcek_bot.application.repositories import AuditLogRepository
from domcek_bot.application.unit_of_work import UnitOfWork


class DiscordAdministrationError(RuntimeError):
    pass


class LastAdminRemovalDenied(DiscordAdministrationError):
    pass


@dataclass(frozen=True, slots=True)
class DiscordChannelOption:
    id: int
    name: str
    kind: str
    category_id: int | None = None
    text_channel_count: int = 0
    voice_channel_count: int = 0
    can_create_project_channel: bool = False
    is_archive_category: bool = False
    is_default_project_category: bool = False


@dataclass(frozen=True, slots=True)
class DiscordRoleOption:
    id: int
    name: str
    position: int
    managed: bool


@dataclass(frozen=True, slots=True)
class DiscordMemberOption:
    id: int
    username: str
    display_name: str
    avatar_url: str | None
    role_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class DiscordEmojiOption:
    id: int
    name: str
    animated: bool
    available: bool


@dataclass(frozen=True, slots=True)
class DiscordDirectory:
    channels: tuple[DiscordChannelOption, ...]
    categories: tuple[DiscordChannelOption, ...]
    roles: tuple[DiscordRoleOption, ...]
    emojis: tuple[DiscordEmojiOption, ...]


class DiscordAdministrationGateway(Protocol):
    async def directory(self, guild_id: int) -> DiscordDirectory: ...

    async def search_members(
        self, guild_id: int, query: str, *, limit: int = 25
    ) -> tuple[DiscordMemberOption, ...]: ...

    async def role_is_assignable(self, guild_id: int, role_id: int) -> bool: ...

    async def count_role_members(self, guild_id: int, role_id: int) -> int: ...

    async def set_member_role(
        self, guild_id: int, member_id: int, role_id: int, *, enabled: bool, reason: str
    ) -> DiscordMemberOption: ...

    async def test_reaction(self, guild_id: int, channel_id: int, emoji: str) -> int: ...


class DiscordAdministrationService:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        discord: DiscordAdministrationGateway,
        alerts: ModeratorAlertTransport | None = None,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._discord = discord
        self._alerts = alerts

    async def directory(self, principal: Principal) -> DiscordDirectory:
        if not (
            Capability.MANAGE_SETTINGS in principal.capabilities
            or Capability.MANAGE_CHANNELS in principal.capabilities
        ):
            principal.require(Capability.MANAGE_SETTINGS)
        directory = await self._discord.directory(principal.guild_id)
        async with self._unit_of_work.transaction() as repositories:
            config = await repositories.guild_configs.get(principal.guild_id)
        archive_category_id = None if config is None else config.archive_category_id
        return replace(
            directory,
            categories=tuple(
                replace(
                    category,
                    can_create_project_channel=(
                        category.id != archive_category_id and category.voice_channel_count == 0
                    ),
                    is_archive_category=category.id == archive_category_id,
                    is_default_project_category=(
                        config is not None and category.id == config.projects_category_id
                    ),
                )
                for category in directory.categories
            ),
        )

    async def search_members(
        self, query: str, *, principal: Principal
    ) -> tuple[DiscordMemberOption, ...]:
        if not (
            Capability.MANAGE_ROLES in principal.capabilities
            or Capability.MANAGE_CHANNELS in principal.capabilities
        ):
            principal.require(Capability.MANAGE_ROLES)
        normalized = query.strip()
        if len(normalized) < 1 or len(normalized) > 100:
            raise ValueError("member query is invalid")
        return await self._discord.search_members(principal.guild_id, normalized)

    async def set_application_role(
        self,
        *,
        member_id: int,
        role: str,
        enabled: bool,
        principal: Principal,
        correlation_id: str,
    ) -> DiscordMemberOption:
        try:
            principal.require(Capability.MANAGE_ROLES)
            if member_id <= 0 or role not in {"team_mod", "admin"}:
                raise ValueError("role operation is invalid")
        except (PermissionError, ValueError) as exc:
            await self._audit_role_denial(
                principal=principal,
                member_id=member_id,
                role=role,
                enabled=enabled,
                correlation_id=correlation_id,
                reason=type(exc).__name__,
            )
            raise
        failure: Exception | None = None
        denial: Exception | None = None
        member: DiscordMemberOption | None = None
        async with self._unit_of_work.transaction() as repositories:
            await repositories.guild_configs.lock_role_mutations(principal.guild_id)
            config = await repositories.guild_configs.get(principal.guild_id)
            if config is None:
                await self._write_role_denial(
                    repositories.audit_logs,
                    principal=principal,
                    member_id=member_id,
                    role=role,
                    enabled=enabled,
                    correlation_id=correlation_id,
                    reason="guild_configuration_missing",
                )
                denial = LookupError("guild configuration not found")
            else:
                role_id = config.admin_role_id if role == "admin" else config.team_mod_role_id
                if role_id is None:
                    await self._write_role_denial(
                        repositories.audit_logs,
                        principal=principal,
                        member_id=member_id,
                        role=role,
                        enabled=enabled,
                        correlation_id=correlation_id,
                        reason="application_role_not_configured",
                    )
                    denial = DiscordAdministrationError("application role is not configured")
                elif not await self._discord.role_is_assignable(principal.guild_id, role_id):
                    await self._write_role_denial(
                        repositories.audit_logs,
                        principal=principal,
                        member_id=member_id,
                        role=role,
                        enabled=enabled,
                        correlation_id=correlation_id,
                        reason="discord_role_not_assignable",
                    )
                    denial = DiscordAdministrationError(
                        "Carlo lacks Manage Roles or its role is not above the target role"
                    )
                elif (
                    role == "admin"
                    and not enabled
                    and (await self._discord.count_role_members(principal.guild_id, role_id)) <= 1
                ):
                    await self._write_role_denial(
                        repositories.audit_logs,
                        principal=principal,
                        member_id=member_id,
                        role=role,
                        enabled=enabled,
                        correlation_id=correlation_id,
                        reason="last_admin_protection",
                    )
                    denial = LastAdminRemovalDenied("the last Carlo Admin cannot be removed")
                else:
                    try:
                        member = await self._discord.set_member_role(
                            principal.guild_id,
                            member_id,
                            role_id,
                            enabled=enabled,
                            reason=f"Carlo {correlation_id} by {principal.user_id}",
                        )
                    except Exception as exc:
                        failure = exc
                        await AuditWriter(repositories.audit_logs).failure(
                            guild_id=principal.guild_id,
                            actor_user_id=principal.user_id,
                            action="role.assigned" if enabled else "role.removed",
                            object_type="discord_member",
                            object_id=str(member_id),
                            correlation_id=correlation_id,
                            after_value={"role": role, "error": type(exc).__name__},
                        )
                    else:
                        await AuditWriter(repositories.audit_logs).success(
                            guild_id=principal.guild_id,
                            actor_user_id=principal.user_id,
                            action="role.assigned" if enabled else "role.removed",
                            object_type="discord_member",
                            object_id=str(member_id),
                            correlation_id=correlation_id,
                            after_value={"role": role},
                        )
        if denial is not None:
            raise denial
        if failure is not None:
            await self._alert_failure(
                principal.guild_id,
                member_id,
                role,
                correlation_id,
            )
            raise failure
        if member is None:
            raise DiscordAdministrationError("Discord returned no member after role mutation")
        return member

    async def _audit_role_denial(
        self,
        *,
        principal: Principal,
        member_id: int,
        role: str,
        enabled: bool,
        correlation_id: str,
        reason: str,
    ) -> None:
        async with self._unit_of_work.transaction() as repositories:
            await self._write_role_denial(
                repositories.audit_logs,
                principal=principal,
                member_id=member_id,
                role=role,
                enabled=enabled,
                correlation_id=correlation_id,
                reason=reason,
            )

    @staticmethod
    async def _write_role_denial(
        audit_logs: AuditLogRepository,
        *,
        principal: Principal,
        member_id: int,
        role: str,
        enabled: bool,
        correlation_id: str,
        reason: str,
    ) -> None:
        await AuditWriter(audit_logs).failure(
            guild_id=principal.guild_id,
            actor_user_id=principal.user_id,
            action="role.change_denied",
            object_type="discord_member",
            object_id=str(member_id),
            correlation_id=correlation_id,
            after_value={
                "role": role,
                "enabled": enabled,
                "reason": reason,
            },
        )

    async def _alert_failure(
        self, guild_id: int, member_id: int, role: str, correlation_id: str
    ) -> None:
        if self._alerts is None:
            return
        try:
            await self._alerts.send_alert(
                guild_id=guild_id,
                moderator_channel_id=None,
                title="Zmena Discord roly zlyhala",
                summary=f"Člen {member_id}; rola {role}; operácia nebola dokončená.",
                correlation_id=correlation_id,
                run_id=None,
            )
        except Exception:
            return

    async def test_configured_reaction(
        self,
        *,
        kind: str,
        channel_id: int,
        emoji_id: int | None,
        emoji_unicode: str | None,
        principal: Principal,
        correlation_id: str,
    ) -> int:
        principal.require(Capability.MANAGE_SETTINGS)
        if kind not in {"seen", "auto", "mention"} or channel_id <= 0:
            raise ValueError("reaction test is invalid")
        emoji = _selected_emoji(emoji_id, emoji_unicode)
        message_id = await self._discord.test_reaction(principal.guild_id, channel_id, emoji)
        async with self._unit_of_work.transaction() as repositories:
            await AuditWriter(repositories.audit_logs).success(
                guild_id=principal.guild_id,
                actor_user_id=principal.user_id,
                action="reaction.tested",
                object_type="discord_message",
                object_id=str(message_id),
                correlation_id=correlation_id,
                after_value={
                    "kind": kind,
                    "channel_id": channel_id,
                    "emoji_id": emoji_id,
                    "emoji_unicode": emoji_unicode,
                },
            )
        return message_id


def _selected_emoji(emoji_id: int | None, unicode_value: str | None) -> str:
    normalized = None if unicode_value is None else unicode_value.strip()
    if emoji_id is not None and emoji_id <= 0:
        raise ValueError("selected reaction emoji ID is invalid")
    if emoji_id is not None and normalized:
        raise ValueError("selected reaction cannot use two emoji values")
    if emoji_id is not None:
        return f"_:{emoji_id}"
    if not normalized or len(normalized) > 32 or any(value in normalized for value in "\r\n"):
        raise ValueError("selected reaction has no valid emoji")
    return normalized
