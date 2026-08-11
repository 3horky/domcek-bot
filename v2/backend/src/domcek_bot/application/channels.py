"""Shared channel creation and archive approval use cases."""

from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Protocol

from domcek_bot.application.alerts import ModeratorAlertTransport
from domcek_bot.application.audit import AuditWriter
from domcek_bot.application.auth.authorization import Capability, Principal
from domcek_bot.application.records import (
    ChannelArchiveRequestRecord,
    IntegrationTaskRecord,
)
from domcek_bot.application.unit_of_work import UnitOfWork
from domcek_bot.domain.enums import ArchiveState, IntegrationTaskState

CHANNEL_TASK = "discord_channel_create"
CHANNEL_NAME = re.compile(r"[^a-z0-9-]+")
CHANNEL_RECOVERY_AFTER = timedelta(minutes=5)


class ChannelOperationError(RuntimeError):
    pass


class ChannelConfigurationMissing(ChannelOperationError):
    pass


class ChannelOperationInProgress(ChannelOperationError):
    pass


class ArchiveDecisionConflict(ChannelOperationError):
    pass


@dataclass(frozen=True, slots=True)
class CreatedChannel:
    channel_id: int
    name: str
    jump_url: str
    category_id: int | None = None


class DiscordChannelGateway(Protocol):
    async def category_allows_project_channel(self, *, guild_id: int, category_id: int) -> bool: ...

    async def get_text_channel(self, *, guild_id: int, channel_id: int) -> CreatedChannel: ...

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
    ) -> CreatedChannel: ...

    async def find_created_text_channel(
        self,
        *,
        guild_id: int,
        category_id: int,
        operation_marker: str,
    ) -> CreatedChannel | None: ...

    async def archive_text_channel(
        self,
        *,
        guild_id: int,
        channel_id: int,
        archive_category_id: int,
        archived_name: str,
        reason: str,
    ) -> CreatedChannel: ...


class ChannelManagementService:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        discord: DiscordChannelGateway,
        alerts: ModeratorAlertTransport | None = None,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._discord = discord
        self._alerts = alerts

    async def create_channel(
        self,
        *,
        name: str,
        member_ids: tuple[int, ...],
        role_ids: tuple[int, ...],
        idempotency_key: str,
        principal: Principal,
        correlation_id: str,
        emoji: str = "🏠",
        owner_id: int | None = None,
        category_id: int | None = None,
        now: datetime | None = None,
    ) -> CreatedChannel:
        principal.require(Capability.MANAGE_CHANNELS)
        normalized_name = normalize_channel_name(name)
        channel_emoji = normalize_channel_emoji(emoji)
        final_name = f"{channel_emoji}・{normalized_name}"[:100]
        effective_owner = principal.user_id if owner_id is None else owner_id
        members = _snowflakes((effective_owner, *member_ids), "members")
        roles = _snowflakes(role_ids, "roles")
        if len(idempotency_key) > 160 or not idempotency_key:
            raise ValueError("idempotency key is invalid")
        started_at = now or datetime.now(UTC)
        proposed_task = IntegrationTaskRecord(
            id=uuid.uuid4(),
            guild_id=principal.guild_id,
            task_type=CHANNEL_TASK,
            deduplication_key=idempotency_key,
            state=IntegrationTaskState.RUNNING,
            scheduled_for=started_at,
            attempt=1,
            started_at=started_at,
        )
        async with self._unit_of_work.transaction() as repositories:
            config = await repositories.guild_configs.get(principal.guild_id)
        if config is None or config.projects_category_id is None:
            raise ChannelConfigurationMissing("projects category is not configured")
        target_category_id = config.projects_category_id if category_id is None else category_id
        if target_category_id <= 0 or target_category_id == config.archive_category_id:
            raise ValueError("selected project category is not allowed")
        if not await self._discord.category_allows_project_channel(
            guild_id=principal.guild_id,
            category_id=target_category_id,
        ):
            raise ValueError("selected project category contains voice channels")
        async with self._unit_of_work.transaction() as repositories:
            claimed = await repositories.integration_tasks.claim(proposed_task)
        task = claimed
        if task.state is IntegrationTaskState.SUCCEEDED and task.result_value:
            return _created_channel_from_result(task.result_value)
        if task.id != proposed_task.id:
            try:
                recovered = await self._discord.find_created_text_channel(
                    guild_id=principal.guild_id,
                    category_id=target_category_id,
                    operation_marker=str(task.id),
                )
            except Exception as exc:
                raise ChannelOperationInProgress(
                    "existing channel operation cannot be reconciled yet"
                ) from exc
            if recovered is not None:
                return await self._record_created_channel(
                    task=task,
                    created=recovered,
                    principal=principal,
                    correlation_id=correlation_id,
                    channel_emoji=channel_emoji,
                    effective_owner=effective_owner,
                    member_count=len(members),
                    role_count=len(roles),
                    category_id=target_category_id,
                )
            still_fresh = task.started_at is None or (
                task.started_at + CHANNEL_RECOVERY_AFTER > started_at
            )
            if task.state is IntegrationTaskState.RUNNING and still_fresh:
                raise ChannelOperationInProgress("channel operation already exists")
            async with self._unit_of_work.transaction() as repositories:
                await repositories.integration_tasks.restart(task.id, started_at=started_at)
        try:
            created = await self._discord.create_text_channel(
                guild_id=principal.guild_id,
                category_id=target_category_id,
                name=final_name,
                member_ids=members,
                role_ids=roles,
                operation_marker=str(task.id),
                reason=f"Carlo request {correlation_id}",
            )
        except Exception as exc:
            try:
                recovered = await self._discord.find_created_text_channel(
                    guild_id=principal.guild_id,
                    category_id=target_category_id,
                    operation_marker=str(task.id),
                )
            except Exception:
                recovered = None
            if recovered is not None:
                return await self._record_created_channel(
                    task=task,
                    created=recovered,
                    principal=principal,
                    correlation_id=correlation_id,
                    channel_emoji=channel_emoji,
                    effective_owner=effective_owner,
                    member_count=len(members),
                    role_count=len(roles),
                    category_id=target_category_id,
                )
            async with self._unit_of_work.transaction() as repositories:
                await repositories.integration_tasks.set_result(
                    task.id,
                    state=IntegrationTaskState.FAILED,
                    completed_at=datetime.now(UTC),
                    error_code="discord_channel_create_failed",
                    error_detail=_safe_error(exc),
                )
                await AuditWriter(repositories.audit_logs).failure(
                    guild_id=principal.guild_id,
                    actor_user_id=principal.user_id,
                    action="channel.create",
                    object_type="discord_channel",
                    object_id=final_name,
                    correlation_id=correlation_id,
                    after_value={"error_code": "discord_channel_create_failed"},
                )
            await self._alert_failure(
                guild_id=principal.guild_id,
                title="Vytvorenie kanála zlyhalo",
                summary=f"Kanál {final_name}; bezpečný kód: discord_channel_create_failed.",
                correlation_id=correlation_id,
            )
            raise ChannelOperationError("Discord channel creation failed") from exc
        return await self._record_created_channel(
            task=task,
            created=created,
            principal=principal,
            correlation_id=correlation_id,
            channel_emoji=channel_emoji,
            effective_owner=effective_owner,
            member_count=len(members),
            role_count=len(roles),
            category_id=target_category_id,
        )

    async def _record_created_channel(
        self,
        *,
        task: IntegrationTaskRecord,
        created: CreatedChannel,
        principal: Principal,
        correlation_id: str,
        channel_emoji: str,
        effective_owner: int,
        member_count: int,
        role_count: int,
        category_id: int,
    ) -> CreatedChannel:
        result_value: dict[str, object] = {
            "channel_id": created.channel_id,
            "name": created.name,
            "jump_url": created.jump_url,
            "category_id": created.category_id,
        }
        async with self._unit_of_work.transaction() as repositories:
            await repositories.integration_tasks.set_result(
                task.id,
                state=IntegrationTaskState.SUCCEEDED,
                completed_at=datetime.now(UTC),
                result_value=result_value,
            )
            await AuditWriter(repositories.audit_logs).success(
                guild_id=principal.guild_id,
                actor_user_id=principal.user_id,
                action="channel.create",
                object_type="discord_channel",
                object_id=str(created.channel_id),
                correlation_id=correlation_id,
                after_value={
                    "name": created.name,
                    "emoji": channel_emoji,
                    "owner_id": effective_owner,
                    "member_count": member_count,
                    "role_count": role_count,
                    "category_id": category_id,
                },
            )
        return created

    async def request_archive(
        self,
        *,
        channel_id: int,
        reason: str,
        principal: Principal,
        correlation_id: str,
        now: datetime | None = None,
    ) -> ChannelArchiveRequestRecord:
        principal.require(Capability.MANAGE_CHANNELS)
        if channel_id <= 0:
            raise ValueError("archive channel identifier is invalid")
        normalized_reason = reason.strip()
        if not 3 <= len(normalized_reason) <= 1000:
            raise ValueError("archive reason must contain 3 to 1000 characters")
        try:
            channel = await self._discord.get_text_channel(
                guild_id=principal.guild_id,
                channel_id=channel_id,
            )
        except Exception as exc:
            raise ChannelOperationError(
                "archive target is not a text channel in the configured guild"
            ) from exc
        requested_at = now or datetime.now(UTC)
        async with self._unit_of_work.transaction() as repositories:
            config = await repositories.guild_configs.get(principal.guild_id)
            if config is None or config.archive_category_id is None:
                raise ChannelConfigurationMissing("archive category is not configured")
            existing = await repositories.channel_archive_requests.get_pending_for_channel(
                principal.guild_id, channel_id
            )
            if existing is not None:
                return existing
            record = ChannelArchiveRequestRecord(
                id=uuid.uuid4(),
                guild_id=principal.guild_id,
                discord_channel_id=channel_id,
                original_channel_name=channel.name,
                archive_category_id=config.archive_category_id,
                requested_by_user_id=principal.user_id,
                reason=normalized_reason,
                state=ArchiveState.PENDING,
                expires_at=requested_at + timedelta(hours=48),
            )
            await repositories.channel_archive_requests.add(record)
            await AuditWriter(repositories.audit_logs).success(
                guild_id=principal.guild_id,
                actor_user_id=principal.user_id,
                action="archive.requested",
                object_type="channel_archive_request",
                object_id=str(record.id),
                correlation_id=correlation_id,
                after_value={"channel_id": channel_id},
            )
        return record

    async def attach_approval_message(self, request_id: uuid.UUID, message_id: int) -> None:
        async with self._unit_of_work.transaction() as repositories:
            await repositories.channel_archive_requests.set_approval_message(request_id, message_id)

    async def list_pending(self, guild_id: int) -> list[ChannelArchiveRequestRecord]:
        async with self._unit_of_work.transaction() as repositories:
            return await repositories.channel_archive_requests.list_pending(guild_id)

    async def recover_archives(
        self, guild_id: int, *, correlation_id: str
    ) -> list[ChannelArchiveRequestRecord]:
        async with self._unit_of_work.transaction() as repositories:
            records = await repositories.channel_archive_requests.list_recoverable(guild_id)
        recovered: list[ChannelArchiveRequestRecord] = []
        for record in records:
            try:
                recovered.append(
                    await self._execute_archive(
                        record,
                        actor_user_id=record.decided_by_user_id,
                        correlation_id=f"{correlation_id}:{record.id}",
                    )
                )
            except ChannelOperationError:
                continue
        return recovered

    async def decide_archive(
        self,
        request_id: uuid.UUID,
        *,
        approve: bool,
        principal: Principal,
        correlation_id: str,
        now: datetime | None = None,
    ) -> ChannelArchiveRequestRecord:
        principal.require(Capability.APPROVE_ARCHIVE)
        decided_at = now or datetime.now(UTC)
        decision = ArchiveState.ARCHIVING if approve else ArchiveState.REJECTED
        expired = False
        async with self._unit_of_work.transaction() as repositories:
            record = await repositories.channel_archive_requests.get(request_id)
            if record is None or record.guild_id != principal.guild_id:
                raise LookupError("archive request not found")
            if record.expires_at <= decided_at:
                changed = await repositories.channel_archive_requests.decide(
                    request_id,
                    state=ArchiveState.EXPIRED,
                    decided_by_user_id=principal.user_id,
                    decided_at=decided_at,
                )
                if not changed:
                    raise ArchiveDecisionConflict("archive request was already decided")
                expired = True
            else:
                changed = await repositories.channel_archive_requests.decide(
                    request_id,
                    state=decision,
                    decided_by_user_id=principal.user_id,
                    decided_at=decided_at,
                )
                if not changed:
                    raise ArchiveDecisionConflict("archive request was already decided")
                await AuditWriter(repositories.audit_logs).success(
                    guild_id=principal.guild_id,
                    actor_user_id=principal.user_id,
                    action="archive.approved" if approve else "archive.rejected",
                    object_type="channel_archive_request",
                    object_id=str(request_id),
                    correlation_id=correlation_id,
                    after_value={"decision": decision.value},
                )
        if expired:
            raise ArchiveDecisionConflict("archive request expired")
        if not approve:
            return replace(
                record,
                state=ArchiveState.REJECTED,
                decided_by_user_id=principal.user_id,
                decided_at=decided_at,
            )
        approved_record = replace(
            record,
            state=ArchiveState.ARCHIVING,
            decided_by_user_id=principal.user_id,
            decided_at=decided_at,
        )
        return await self._execute_archive(
            approved_record,
            actor_user_id=principal.user_id,
            correlation_id=correlation_id,
        )

    async def _execute_archive(
        self,
        record: ChannelArchiveRequestRecord,
        *,
        actor_user_id: int | None,
        correlation_id: str,
    ) -> ChannelArchiveRequestRecord:
        decided_at = record.decided_at or datetime.now(UTC)
        archived_name = archive_channel_name(record.original_channel_name, decided_at)
        try:
            current = await self._discord.get_text_channel(
                guild_id=record.guild_id,
                channel_id=record.discord_channel_id,
            )
            already_archived = (
                current.name == archived_name and current.category_id == record.archive_category_id
            )
            if not already_archived:
                await self._discord.archive_text_channel(
                    guild_id=record.guild_id,
                    channel_id=record.discord_channel_id,
                    archive_category_id=record.archive_category_id,
                    archived_name=archived_name,
                    reason=f"Carlo archive {correlation_id}: {record.reason}",
                )
        except Exception as exc:
            async with self._unit_of_work.transaction() as repositories:
                await AuditWriter(repositories.audit_logs).failure(
                    guild_id=record.guild_id,
                    actor_user_id=actor_user_id,
                    action="archive.execute",
                    object_type="channel_archive_request",
                    object_id=str(record.id),
                    correlation_id=correlation_id,
                    after_value={"error_code": "discord_archive_failed"},
                )
            await self._alert_failure(
                guild_id=record.guild_id,
                title="Archivácia kanála zlyhala",
                summary=(
                    f"Kanál {record.original_channel_name}; bezpečný kód: discord_archive_failed."
                ),
                correlation_id=correlation_id,
            )
            raise ChannelOperationError("Discord archive operation failed") from exc
        async with self._unit_of_work.transaction() as repositories:
            changed = await repositories.channel_archive_requests.mark_execution(
                record.id,
                state=ArchiveState.EXECUTED,
                expected_states=(
                    ArchiveState.ARCHIVING,
                    ArchiveState.FAILED,
                    ArchiveState.APPROVED,
                ),
            )
            if changed:
                await AuditWriter(repositories.audit_logs).success(
                    guild_id=record.guild_id,
                    actor_user_id=actor_user_id,
                    action="archive.executed",
                    object_type="channel_archive_request",
                    object_id=str(record.id),
                    correlation_id=correlation_id,
                    after_value={
                        "channel_id": record.discord_channel_id,
                        "archived_name": archived_name,
                        "reconciled_existing_effect": already_archived,
                    },
                )
        return replace(
            record,
            state=ArchiveState.EXECUTED,
            decided_by_user_id=actor_user_id,
            decided_at=decided_at,
        )

    async def _alert_failure(
        self, *, guild_id: int, title: str, summary: str, correlation_id: str
    ) -> None:
        if self._alerts is None:
            return
        try:
            await self._alerts.send_alert(
                guild_id=guild_id,
                moderator_channel_id=None,
                title=title,
                summary=summary,
                correlation_id=correlation_id,
                run_id=None,
            )
        except Exception:
            return


def normalize_channel_name(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    normalized = CHANNEL_NAME.sub("-", ascii_value.lower().strip()).strip("-")
    normalized = re.sub(r"-{2,}", "-", normalized)[:100].rstrip("-")
    if not normalized:
        raise ValueError("channel name is empty after normalization")
    return normalized


def normalize_channel_emoji(value: str) -> str:
    normalized = value.strip()
    if (
        not normalized
        or len(normalized) > 16
        or any(unicodedata.category(char) == "Cc" for char in normalized)
    ):
        raise ValueError("channel emoji is invalid")
    if any(char.isspace() for char in normalized):
        raise ValueError("channel emoji cannot contain whitespace")
    return normalized


def archive_channel_name(original_name: str, decided_at: datetime) -> str:
    base = normalize_channel_name(original_name)
    suffix = decided_at.astimezone(UTC).strftime("-%Y-%m-%d")
    return f"{base[: 100 - len(suffix)].rstrip('-')}{suffix}"


def _snowflakes(values: tuple[int, ...], field: str) -> tuple[int, ...]:
    unique = tuple(dict.fromkeys(values))
    if len(unique) > 25 or any(value <= 0 for value in unique):
        raise ValueError(f"{field} contain invalid Discord identifiers")
    return unique


def _created_channel_from_result(value: dict[str, object]) -> CreatedChannel:
    channel_id = value.get("channel_id")
    name = value.get("name")
    jump_url = value.get("jump_url")
    category_id = value.get("category_id")
    if (
        not isinstance(channel_id, int)
        or not isinstance(name, str)
        or not isinstance(jump_url, str)
    ):
        raise ChannelOperationError("stored channel result is invalid")
    if category_id is not None and not isinstance(category_id, int):
        raise ChannelOperationError("stored channel category result is invalid")
    return CreatedChannel(channel_id, name, jump_url, category_id)


def _safe_error(exc: BaseException) -> str:
    return str(exc).replace("\n", " ")[:500] or type(exc).__name__
