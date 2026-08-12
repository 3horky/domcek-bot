"""State-safe, durable compensation for reversible Discord administration effects."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from domcek_bot.application.audit import AuditWriter
from domcek_bot.application.auth.authorization import Capability, Principal
from domcek_bot.application.channels import ChannelOperationError, DiscordChannelGateway
from domcek_bot.application.discord_admin import (
    DiscordAdministrationError,
    DiscordAdministrationGateway,
)
from domcek_bot.application.records import UndoOperationRecord
from domcek_bot.application.unit_of_work import UnitOfWork
from domcek_bot.domain.enums import UndoState


class UndoUnavailable(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class UndoResult:
    id: uuid.UUID
    operation_type: str
    state: UndoState
    object_id: str


class UndoService:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        discord_admin: DiscordAdministrationGateway,
        channels: DiscordChannelGateway,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._discord_admin = discord_admin
        self._channels = channels

    async def list_available(
        self, *, principal: Principal, scope: str
    ) -> list[UndoOperationRecord]:
        operation_types: tuple[str, ...]
        if scope == "roles":
            principal.require(Capability.MANAGE_ROLES)
            operation_types = ("role_change",)
        elif scope == "channels":
            principal.require(Capability.MANAGE_CHANNELS)
            operation_types = ("channel_create", "channel_archive")
        else:
            raise ValueError("undo scope is invalid")
        async with self._unit_of_work.transaction() as repositories:
            return await repositories.undo_operations.list_available(
                principal.guild_id, operation_types=operation_types
            )

    async def undo(
        self,
        operation_id: uuid.UUID,
        *,
        principal: Principal,
        correlation_id: str,
        now: datetime | None = None,
    ) -> UndoResult:
        decided_at = now or datetime.now(UTC)
        blocked: UndoUnavailable | None = None
        async with self._unit_of_work.transaction() as repositories:
            operation = await repositories.undo_operations.get_for_update(operation_id)
            if operation is None or operation.guild_id != principal.guild_id:
                raise LookupError("undo operation not found")
            if operation.state is UndoState.UNDONE:
                return _result(operation, UndoState.UNDONE)
            self._require_capability(operation, principal)
            await repositories.undo_operations.mark_undoing(operation.id, started_at=decided_at)
            try:
                await self._apply(operation, principal, correlation_id)
            except (ChannelOperationError, DiscordAdministrationError):
                blocked = UndoUnavailable("discord_unavailable")
                await repositories.undo_operations.mark_blocked(operation.id, reason=blocked.reason)
                await AuditWriter(repositories.audit_logs).failure(
                    guild_id=principal.guild_id,
                    actor_user_id=principal.user_id,
                    action="undo.blocked",
                    object_type=operation.operation_type,
                    object_id=operation.object_id,
                    correlation_id=correlation_id,
                    after_value={"reason": blocked.reason},
                )
            except UndoUnavailable as exc:
                blocked = exc
                await repositories.undo_operations.mark_blocked(operation.id, reason=exc.reason)
                await AuditWriter(repositories.audit_logs).failure(
                    guild_id=principal.guild_id,
                    actor_user_id=principal.user_id,
                    action="undo.blocked",
                    object_type=operation.operation_type,
                    object_id=operation.object_id,
                    correlation_id=correlation_id,
                    after_value={"reason": exc.reason},
                )
            if blocked is None:
                await repositories.undo_operations.mark_undone(
                    operation.id,
                    undone_at=decided_at,
                    undone_by_user_id=principal.user_id,
                )
                await AuditWriter(repositories.audit_logs).success(
                    guild_id=principal.guild_id,
                    actor_user_id=principal.user_id,
                    action="undo.completed",
                    object_type=operation.operation_type,
                    object_id=operation.object_id,
                    correlation_id=correlation_id,
                )
        if blocked is not None:
            raise blocked
        return _result(operation, UndoState.UNDONE)

    @staticmethod
    def _require_capability(operation: UndoOperationRecord, principal: Principal) -> None:
        if operation.operation_type == "role_change":
            principal.require(Capability.MANAGE_ROLES)
        else:
            principal.require(Capability.MANAGE_CHANNELS)

    async def _apply(
        self, operation: UndoOperationRecord, principal: Principal, correlation_id: str
    ) -> None:
        if operation.operation_type == "role_change":
            await self._undo_role(operation, principal, correlation_id)
            return
        if operation.operation_type == "channel_create":
            await self._undo_created_channel(operation, principal, correlation_id)
            return
        if operation.operation_type == "channel_archive":
            await self._undo_archive(operation, principal, correlation_id)
            return
        raise UndoUnavailable("unknown_operation")

    async def _undo_role(
        self, operation: UndoOperationRecord, principal: Principal, correlation_id: str
    ) -> None:
        member_id = int(operation.object_id)
        role = str(operation.after_snapshot.get("role", ""))
        expected_enabled = bool(operation.after_snapshot.get("enabled"))
        target_enabled = bool(operation.before_snapshot.get("enabled"))
        config_role_id = await self._configured_role_id(principal.guild_id, role)
        member = await self._discord_admin.get_member(principal.guild_id, member_id)
        current_enabled = config_role_id in member.role_ids
        if current_enabled == target_enabled:
            return
        if current_enabled != expected_enabled:
            raise UndoUnavailable("role_changed_since_operation")
        if not await self._discord_admin.role_is_assignable(principal.guild_id, config_role_id):
            raise UndoUnavailable("role_no_longer_assignable")
        if (
            role == "admin"
            and not target_enabled
            and await self._discord_admin.count_role_members(principal.guild_id, config_role_id)
            <= 1
        ):
            raise UndoUnavailable("last_admin_protection")
        await self._discord_admin.set_member_role(
            principal.guild_id,
            member_id,
            config_role_id,
            enabled=target_enabled,
            reason=f"Carlo undo {correlation_id} by {principal.user_id}",
        )

    async def _configured_role_id(self, guild_id: int, role: str) -> int:
        async with self._unit_of_work.transaction() as repositories:
            config = await repositories.guild_configs.get(guild_id)
        role_id = None
        if config is not None:
            role_id = config.admin_role_id if role == "admin" else config.team_mod_role_id
        if role_id is None:
            raise UndoUnavailable("role_configuration_changed")
        return role_id

    async def _undo_created_channel(
        self, operation: UndoOperationRecord, principal: Principal, correlation_id: str
    ) -> None:
        channel_id = int(operation.object_id)
        current = await self._channels.channel_snapshot(
            guild_id=principal.guild_id, channel_id=channel_id
        )
        if current is None:
            return
        if current != operation.after_snapshot or current.get("last_message_id") is not None:
            raise UndoUnavailable("created_channel_changed_offer_archive")
        await self._channels.delete_text_channel(
            guild_id=principal.guild_id,
            channel_id=channel_id,
            reason=f"Carlo undo {correlation_id} by {principal.user_id}",
        )

    async def _undo_archive(
        self, operation: UndoOperationRecord, principal: Principal, correlation_id: str
    ) -> None:
        channel_id = int(operation.object_id)
        current = await self._channels.channel_snapshot(
            guild_id=principal.guild_id, channel_id=channel_id
        )
        if current is None:
            raise UndoUnavailable("archived_channel_missing")
        if current == operation.before_snapshot:
            return
        if current != operation.after_snapshot:
            raise UndoUnavailable("archived_channel_changed_since_operation")
        await self._channels.restore_text_channel(
            guild_id=principal.guild_id,
            channel_id=channel_id,
            snapshot=operation.before_snapshot,
            reason=f"Carlo undo {correlation_id} by {principal.user_id}",
        )


def _result(operation: UndoOperationRecord, state: UndoState) -> UndoResult:
    return UndoResult(operation.id, operation.operation_type, state, operation.object_id)
