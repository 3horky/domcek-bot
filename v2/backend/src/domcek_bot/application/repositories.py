"""Repository contracts owned by the application layer."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol

from domcek_bot.application.records import (
    AuditLogRecord,
    CalendarSourceRecord,
    ChannelArchiveRequestRecord,
    EventOverrideRecord,
    EventSeriesOverrideRecord,
    ExternalEventRecord,
    GuildConfigRecord,
    InfoAnnouncementRecord,
    IntegrationTaskRecord,
    ManualEventRecord,
    PublicationItemRecord,
    PublicationMessageRecord,
    PublicationRunRecord,
    ReactionConfigRecord,
    RuntimeHeartbeatRecord,
    ShadowPublicationRecord,
    WebSessionRecord,
)
from domcek_bot.domain.enums import ArchiveState, IntegrationTaskState, PublicationState


class GuildConfigRepository(Protocol):
    async def get(self, guild_id: int) -> GuildConfigRecord | None: ...

    async def add(self, record: GuildConfigRecord) -> None: ...

    async def list_all(self) -> list[GuildConfigRecord]: ...

    async def update(self, record: GuildConfigRecord, *, expected_version: int) -> int: ...

    async def lock_role_mutations(self, guild_id: int) -> None: ...


class CalendarSourceRepository(Protocol):
    async def get(self, source_id: uuid.UUID) -> CalendarSourceRecord | None: ...

    async def add(self, record: CalendarSourceRecord) -> None: ...

    async def list_for_guild(self, guild_id: int) -> list[CalendarSourceRecord]: ...

    async def update(self, record: CalendarSourceRecord, *, expected_version: int) -> int: ...

    async def try_acquire_sync(
        self,
        source_id: uuid.UUID,
        *,
        attempted_at: datetime,
        stale_before: datetime,
    ) -> bool: ...

    async def mark_sync_succeeded(
        self,
        source_id: uuid.UUID,
        *,
        sync_token: str,
        sync_token_query_key: str,
        completed_at: datetime,
        was_full_sync: bool,
    ) -> None: ...

    async def mark_sync_failed(
        self, source_id: uuid.UUID, *, attempted_at: datetime, error_code: str
    ) -> None: ...


class ReactionConfigRepository(Protocol):
    async def get(self, guild_id: int) -> ReactionConfigRecord | None: ...

    async def add(self, record: ReactionConfigRecord) -> None: ...

    async def update(self, record: ReactionConfigRecord, *, expected_version: int) -> int: ...


class ExternalEventRepository(Protocol):
    async def get(self, event_id: uuid.UUID) -> ExternalEventRecord | None: ...

    async def get_by_source_key(self, source_key: str) -> ExternalEventRecord | None: ...

    async def add(self, record: ExternalEventRecord) -> None: ...

    async def list_for_source(self, source_id: uuid.UUID) -> list[ExternalEventRecord]: ...

    async def list_for_sources(
        self, source_ids: tuple[uuid.UUID, ...]
    ) -> list[ExternalEventRecord]: ...

    async def upsert_from_sync(self, record: ExternalEventRecord) -> bool: ...

    async def cancel_by_provider_event_id(
        self,
        source_id: uuid.UUID,
        provider_event_id: str,
        *,
        synced_at: datetime,
    ) -> bool: ...

    async def mark_missing_deleted(
        self,
        source_id: uuid.UUID,
        seen_source_keys: set[str],
        *,
        deleted_at: datetime,
    ) -> int: ...

    async def mark_deleted(self, event_id: uuid.UUID, deleted_at: datetime) -> bool: ...


class EventOverrideRepository(Protocol):
    async def get(self, external_event_id: uuid.UUID) -> EventOverrideRecord | None: ...

    async def add(self, record: EventOverrideRecord) -> None: ...

    async def update(self, record: EventOverrideRecord, *, expected_version: int) -> int: ...

    async def list_for_events(
        self, event_ids: tuple[uuid.UUID, ...]
    ) -> list[EventOverrideRecord]: ...


class EventSeriesOverrideRepository(Protocol):
    async def get_effective(
        self,
        source_id: uuid.UUID,
        series_key: str,
        effective_from_key: str,
    ) -> EventSeriesOverrideRecord | None: ...

    async def add(self, record: EventSeriesOverrideRecord) -> None: ...

    async def update(self, record: EventSeriesOverrideRecord, *, expected_version: int) -> int: ...

    async def list_for_sources(
        self, source_ids: tuple[uuid.UUID, ...]
    ) -> list[EventSeriesOverrideRecord]: ...


class ManualEventRepository(Protocol):
    async def get(self, event_id: uuid.UUID) -> ManualEventRecord | None: ...

    async def add(self, record: ManualEventRecord) -> None: ...

    async def update(self, record: ManualEventRecord, *, expected_version: int) -> int: ...

    async def list_for_guild(self, guild_id: int) -> list[ManualEventRecord]: ...


class InfoAnnouncementRepository(Protocol):
    async def get(self, announcement_id: uuid.UUID) -> InfoAnnouncementRecord | None: ...

    async def add(self, record: InfoAnnouncementRecord) -> None: ...

    async def update(self, record: InfoAnnouncementRecord, *, expected_version: int) -> int: ...

    async def list_for_guild(self, guild_id: int) -> list[InfoAnnouncementRecord]: ...


class PublicationRunRepository(Protocol):
    async def completed_slot_keys(self, guild_id: int) -> frozenset[str]: ...

    async def lock_slot(self, guild_id: int, slot_key: str) -> None: ...

    async def get(self, run_id: uuid.UUID) -> PublicationRunRecord | None: ...

    async def get_for_slot(self, guild_id: int, slot_key: str) -> PublicationRunRecord | None: ...

    async def list_for_guild(
        self, guild_id: int, *, limit: int = 50
    ) -> list[PublicationRunRecord]: ...

    async def list_items(self, run_id: uuid.UUID) -> list[PublicationItemRecord]: ...

    async def add_snapshot(
        self,
        run: PublicationRunRecord,
        items: tuple[PublicationItemRecord, ...],
        messages: tuple[PublicationMessageRecord, ...],
    ) -> None: ...

    async def list_messages(self, run_id: uuid.UUID) -> list[PublicationMessageRecord]: ...

    async def claim_message(self, message_id: uuid.UUID, *, attempted_at: datetime) -> bool: ...

    async def increment_message_attempt(
        self, message_id: uuid.UUID, *, attempted_at: datetime
    ) -> None: ...

    async def mark_message_sent(
        self, message_id: uuid.UUID, *, discord_message_id: int, sent_at: datetime
    ) -> None: ...

    async def mark_message_failed(self, message_id: uuid.UUID, *, detail: str) -> None: ...

    async def mark_reaction_warning(self, message_id: uuid.UUID, *, detail: str) -> None: ...

    async def reset_uncertain_message(self, message_id: uuid.UUID) -> None: ...

    async def resolve_incidents(
        self,
        run_id: uuid.UUID,
        *,
        resolution: str,
        resolved_by_user_id: int,
        resolved_at: datetime,
    ) -> None: ...

    async def count_open_incidents(self, guild_id: int) -> int: ...

    async def set_state(
        self,
        run_id: uuid.UUID,
        state: PublicationState,
        *,
        completed_at: datetime | None = None,
        error_code: str | None = None,
        error_detail: str | None = None,
        increment_attempt: bool = False,
        warning_codes: tuple[str, ...] | None = None,
    ) -> None: ...

    async def mark_uncertain(
        self,
        run_id: uuid.UUID,
        message_id: uuid.UUID,
        *,
        correlation_id: str,
        summary: str,
    ) -> None: ...

    async def mark_delivery_exhausted(
        self,
        run_id: uuid.UUID,
        message_id: uuid.UUID,
        *,
        correlation_id: str,
        summary: str,
    ) -> None: ...

    async def list_recoverable(
        self, *, attempted_before: datetime
    ) -> list[PublicationRunRecord]: ...


class ShadowPublicationRepository(Protocol):
    async def record(self, capture: ShadowPublicationRecord) -> ShadowPublicationRecord: ...

    async def list_for_guild(
        self, guild_id: int, *, limit: int = 20
    ) -> list[ShadowPublicationRecord]: ...


class RuntimeHeartbeatRepository(Protocol):
    async def upsert(self, heartbeat: RuntimeHeartbeatRecord) -> None: ...

    async def list_for_guild(
        self, guild_id: int, *, limit: int = 50
    ) -> list[RuntimeHeartbeatRecord]: ...


class IntegrationTaskRepository(Protocol):
    async def claim(self, record: IntegrationTaskRecord) -> IntegrationTaskRecord: ...

    async def set_result(
        self,
        task_id: uuid.UUID,
        *,
        state: IntegrationTaskState,
        completed_at: datetime,
        result_value: dict[str, object] | None = None,
        error_code: str | None = None,
        error_detail: str | None = None,
    ) -> None: ...

    async def restart(self, task_id: uuid.UUID, *, started_at: datetime) -> None: ...

    async def list_for_guild(
        self, guild_id: int, *, limit: int = 20
    ) -> list[IntegrationTaskRecord]: ...


class ChannelArchiveRequestRepository(Protocol):
    async def get(self, request_id: uuid.UUID) -> ChannelArchiveRequestRecord | None: ...

    async def add(self, record: ChannelArchiveRequestRecord) -> None: ...

    async def list_pending(self, guild_id: int) -> list[ChannelArchiveRequestRecord]: ...

    async def list_recoverable(self, guild_id: int) -> list[ChannelArchiveRequestRecord]: ...

    async def get_pending_for_channel(
        self, guild_id: int, channel_id: int
    ) -> ChannelArchiveRequestRecord | None: ...

    async def set_approval_message(self, request_id: uuid.UUID, message_id: int) -> None: ...

    async def decide(
        self,
        request_id: uuid.UUID,
        *,
        state: ArchiveState,
        decided_by_user_id: int,
        decided_at: datetime,
    ) -> bool: ...

    async def mark_execution(
        self,
        request_id: uuid.UUID,
        *,
        state: ArchiveState,
        expected_states: tuple[ArchiveState, ...] = (ArchiveState.ARCHIVING,),
    ) -> bool: ...


class WebSessionRepository(Protocol):
    async def add(self, record: WebSessionRecord) -> None: ...

    async def get_active_by_token_hash(
        self, token_hash: str, *, now: datetime
    ) -> WebSessionRecord | None: ...

    async def touch(self, session_id: uuid.UUID, *, seen_at: datetime) -> None: ...

    async def revoke(self, session_id: uuid.UUID, *, revoked_at: datetime) -> bool: ...


class AuditLogRepository(Protocol):
    async def add(self, record: AuditLogRecord) -> None: ...

    async def list_for_object(self, object_type: str, object_id: str) -> list[AuditLogRecord]: ...

    async def list_for_guild(
        self,
        guild_id: int,
        *,
        limit: int,
        object_types: tuple[str, ...] | None = None,
    ) -> list[AuditLogRecord]: ...
