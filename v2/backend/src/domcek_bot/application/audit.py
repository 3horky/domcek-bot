"""Guild-isolated audit queries with role-appropriate visibility."""

from __future__ import annotations

import uuid
from typing import Any

from domcek_bot.application.auth.authorization import (
    AuthorizationDenied,
    Capability,
    Principal,
)
from domcek_bot.application.records import AuditLogRecord
from domcek_bot.application.repositories import AuditLogRepository
from domcek_bot.application.unit_of_work import UnitOfWork
from domcek_bot.domain.enums import AuditResult

TEAM_MOD_AUDIT_OBJECTS = (
    "event_override",
    "event_series_override",
    "manual_event",
    "info_announcement",
    "discord_channel",
    "channel_archive_request",
)


class AuditWriter:
    """Small helper keeping new use cases on one audit record shape."""

    def __init__(self, repository: AuditLogRepository) -> None:
        self._repository = repository

    async def success(
        self,
        *,
        guild_id: int,
        actor_user_id: int | None,
        action: str,
        object_type: str,
        object_id: str,
        correlation_id: str,
        before_value: dict[str, Any] | None = None,
        after_value: dict[str, Any] | None = None,
    ) -> None:
        await self._repository.add(
            AuditLogRecord(
                id=uuid.uuid4(),
                guild_id=guild_id,
                actor_user_id=actor_user_id,
                action=action,
                object_type=object_type,
                object_id=object_id,
                before_value=before_value,
                after_value=after_value,
                result=AuditResult.SUCCEEDED,
                correlation_id=correlation_id,
            )
        )

    async def failure(
        self,
        *,
        guild_id: int,
        actor_user_id: int | None,
        action: str,
        object_type: str,
        object_id: str,
        correlation_id: str,
        after_value: dict[str, Any] | None = None,
    ) -> None:
        await self._repository.add(
            AuditLogRecord(
                id=uuid.uuid4(),
                guild_id=guild_id,
                actor_user_id=actor_user_id,
                action=action,
                object_type=object_type,
                object_id=object_id,
                before_value=None,
                after_value=after_value,
                result=AuditResult.FAILED,
                correlation_id=correlation_id,
            )
        )


class AuditQueryService:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def list_recent(
        self,
        *,
        principal: Principal,
        limit: int,
    ) -> list[AuditLogRecord]:
        if not 1 <= limit <= 200:
            raise ValueError("audit limit must be between 1 and 200")
        object_types: tuple[str, ...] | None
        if Capability.VIEW_FULL_AUDIT in principal.capabilities:
            object_types = None
        elif Capability.EDIT_CONTENT in principal.capabilities:
            object_types = TEAM_MOD_AUDIT_OBJECTS
        else:
            raise AuthorizationDenied("audit is not available for this principal")
        async with self._unit_of_work.transaction() as repositories:
            return await repositories.audit_logs.list_for_guild(
                principal.guild_id,
                limit=limit,
                object_types=object_types,
            )
