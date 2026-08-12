"""PostgreSQL/SQLAlchemy implementations of application repositories."""

from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import delete, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

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
from domcek_bot.domain.enums import (
    ArchiveState,
    AuditResult,
    DescriptionState,
    ExternalEventStatus,
    InclusionDecision,
    IntegrationTaskState,
    PublicationIncidentState,
    PublicationItemType,
    PublicationMessageState,
    PublicationMode,
    PublicationState,
    SyncStatus,
)
from domcek_bot.domain.errors import OptimisticLockError
from domcek_bot.infrastructure.models import (
    AuditLogModel,
    CalendarSourceModel,
    ChannelArchiveRequestModel,
    EventOverrideModel,
    EventSeriesOverrideModel,
    ExternalEventModel,
    GuildConfigModel,
    InfoAnnouncementModel,
    IntegrationTaskModel,
    ManualEventModel,
    PublicationIncidentModel,
    PublicationItemModel,
    PublicationMessageModel,
    PublicationRunModel,
    ReactionConfigChannelModel,
    ReactionConfigModel,
    RuntimeHeartbeatModel,
    ShadowPublicationModel,
    WebSessionModel,
)


def _guild_record(model: GuildConfigModel) -> GuildConfigRecord:
    return GuildConfigRecord(
        guild_id=model.guild_id,
        timezone=model.timezone,
        publication_weekday=model.publication_weekday,
        publication_time=model.publication_time,
        automatic_publication_enabled=model.automatic_publication_enabled,
        publish_google_descriptions=model.publish_google_descriptions,
        generated_intro_enabled=model.generated_intro_enabled,
        everyone_mention_enabled=model.everyone_mention_enabled,
        allow_stale_calendar_cache=model.allow_stale_calendar_cache,
        alert_calendar_sync_enabled=model.alert_calendar_sync_enabled,
        alert_publication_enabled=model.alert_publication_enabled,
        alert_channel_operations_enabled=model.alert_channel_operations_enabled,
        alert_role_operations_enabled=model.alert_role_operations_enabled,
        alert_publication_reminder_enabled=model.alert_publication_reminder_enabled,
        admin_role_id=model.admin_role_id,
        team_mod_role_id=model.team_mod_role_id,
        publisher_role_id=model.publisher_role_id,
        announcement_channel_id=model.announcement_channel_id,
        command_channel_id=model.command_channel_id,
        moderator_channel_id=model.moderator_channel_id,
        projects_category_id=model.projects_category_id,
        archive_category_id=model.archive_category_id,
        closing_message=model.closing_message,
        version=model.version,
    )


def _calendar_source_record(model: CalendarSourceModel) -> CalendarSourceRecord:
    return CalendarSourceRecord(
        id=model.id,
        guild_id=model.guild_id,
        provider=model.provider,
        external_calendar_id=model.external_calendar_id,
        display_name=model.display_name,
        priority=model.priority,
        active=model.active,
        sync_status=SyncStatus(model.sync_status),
        sync_token=model.sync_token,
        sync_token_query_key=model.sync_token_query_key,
        last_sync_attempt_at=model.last_sync_attempt_at,
        last_sync_success_at=model.last_sync_success_at,
        last_full_sync_at=model.last_full_sync_at,
        last_sync_error=model.last_sync_error,
        version=model.version,
    )


def _reaction_config_record(
    model: ReactionConfigModel, channel_ids: tuple[int, ...]
) -> ReactionConfigRecord:
    return ReactionConfigRecord(
        guild_id=model.guild_id,
        seen_enabled=model.seen_enabled,
        seen_emoji_id=model.seen_emoji_id,
        seen_emoji_unicode=model.seen_emoji_unicode,
        auto_reaction_enabled=model.auto_reaction_enabled,
        auto_reaction_emoji_id=model.auto_reaction_emoji_id,
        auto_reaction_emoji_unicode=model.auto_reaction_emoji_unicode,
        mention_reaction_enabled=model.mention_reaction_enabled,
        mention_reaction_emoji_id=model.mention_reaction_emoji_id,
        mention_reaction_emoji_unicode=model.mention_reaction_emoji_unicode,
        auto_reaction_channel_ids=channel_ids,
        version=model.version,
    )


def _shadow_publication_record(model: ShadowPublicationModel) -> ShadowPublicationRecord:
    return ShadowPublicationRecord(
        id=model.id,
        guild_id=model.guild_id,
        slot_key=model.slot_key,
        scheduled_for=model.scheduled_for,
        first_observed_at=model.first_observed_at,
        last_observed_at=model.last_observed_at,
        observation_count=model.observation_count,
        draft_sha256=model.draft_sha256,
        draft_json=dict(model.draft_json),
        item_count=model.item_count,
        message_count=model.message_count,
        calendar_sync_valid=model.calendar_sync_valid,
        calendar_sync_evidence=dict(model.calendar_sync_evidence),
        warning_codes=tuple(model.warning_codes),
    )


def _runtime_heartbeat_record(model: RuntimeHeartbeatModel) -> RuntimeHeartbeatRecord:
    return RuntimeHeartbeatRecord(
        id=model.id,
        guild_id=model.guild_id,
        process_name=model.process_name,
        instance_id=model.instance_id,
        state=model.state,
        started_at=model.started_at,
        last_seen_at=model.last_seen_at,
        details=dict(model.details),
    )


def _external_event_record(model: ExternalEventModel) -> ExternalEventRecord:
    return ExternalEventRecord(
        id=model.id,
        calendar_source_id=model.calendar_source_id,
        source_key=model.source_key,
        provider_event_id=model.provider_event_id,
        occurrence_id=model.occurrence_id,
        series_key=model.series_key,
        original_start_key=model.original_start_key,
        source_title=model.source_title,
        source_description=model.source_description,
        is_all_day=model.is_all_day,
        starts_at=model.starts_at,
        ends_at=model.ends_at,
        starts_on=model.starts_on,
        ends_on=model.ends_on,
        source_timezone=model.source_timezone,
        status=ExternalEventStatus(model.status),
        etag=model.etag,
        provider_updated_at=model.provider_updated_at,
        last_synced_at=model.last_synced_at,
        deleted_at=model.deleted_at,
    )


def _event_override_record(model: EventOverrideModel) -> EventOverrideRecord:
    return EventOverrideRecord(
        external_event_id=model.external_event_id,
        public_title=model.public_title,
        description_state=DescriptionState(model.description_state),
        public_description=model.public_description,
        inclusion_decision=InclusionDecision(model.inclusion_decision),
        version=model.version,
        updated_by_user_id=model.updated_by_user_id,
    )


def _event_series_override_record(
    model: EventSeriesOverrideModel,
) -> EventSeriesOverrideRecord:
    return EventSeriesOverrideRecord(
        id=model.id,
        calendar_source_id=model.calendar_source_id,
        series_key=model.series_key,
        effective_from_key=model.effective_from_key,
        effective_all_day=model.effective_all_day,
        effective_from_at=model.effective_from_at,
        effective_from_date=model.effective_from_date,
        public_title=model.public_title,
        description_state=DescriptionState(model.description_state),
        public_description=model.public_description,
        version=model.version,
        updated_by_user_id=model.updated_by_user_id,
    )


def _manual_event_record(model: ManualEventModel) -> ManualEventRecord:
    return ManualEventRecord(
        id=model.id,
        guild_id=model.guild_id,
        title=model.title,
        description=model.description,
        is_all_day=model.is_all_day,
        starts_at=model.starts_at,
        ends_at=model.ends_at,
        starts_on=model.starts_on,
        ends_on=model.ends_on,
        timezone=model.timezone,
        link_url=model.link_url,
        active=model.active,
        created_by_user_id=model.created_by_user_id,
        updated_by_user_id=model.updated_by_user_id,
        deleted_at=model.deleted_at,
        version=model.version,
    )


def _publication_run_record(model: PublicationRunModel) -> PublicationRunRecord:
    return PublicationRunRecord(
        id=model.id,
        guild_id=model.guild_id,
        slot_key=model.slot_key,
        scheduled_for=model.scheduled_for,
        mode=PublicationMode(model.mode),
        initiated_by_user_id=model.initiated_by_user_id,
        state=PublicationState(model.state),
        attempt=model.attempt,
        idempotency_key=model.idempotency_key,
        composer_version=model.composer_version,
        intro_text=model.intro_text,
        intro_prompt_version=model.intro_prompt_version,
        intro_used_fallback=model.intro_used_fallback,
        outro_text=model.outro_text,
        warning_codes=tuple(model.warning_codes),
        started_at=model.started_at,
        completed_at=model.completed_at,
        error_code=model.error_code,
        error_detail=model.error_detail,
    )


def _publication_item_record(model: PublicationItemModel) -> PublicationItemRecord:
    return PublicationItemRecord(
        id=model.id,
        publication_run_id=model.publication_run_id,
        item_type=PublicationItemType(model.item_type),
        position=model.position,
        external_event_id=model.external_event_id,
        manual_event_id=model.manual_event_id,
        info_announcement_id=model.info_announcement_id,
        final_title=model.final_title,
        final_description=model.final_description,
        display_time=model.display_time,
        day_emoji=model.day_emoji,
        starts_at=model.starts_at,
        ends_at=model.ends_at,
        starts_on=model.starts_on,
        ends_on=model.ends_on,
        is_all_day=model.is_all_day,
        link_url=model.link_url,
        image_url=model.image_url,
    )


def _publication_message_record(model: PublicationMessageModel) -> PublicationMessageRecord:
    return PublicationMessageRecord(
        id=model.id,
        publication_run_id=model.publication_run_id,
        position=model.position,
        discord_channel_id=model.discord_channel_id,
        discord_message_id=model.discord_message_id,
        state=PublicationMessageState(model.state),
        part_key=model.part_key,
        nonce=model.nonce,
        content=model.content,
        embeds=tuple(model.embeds),
        allowed_mentions=tuple(model.allowed_mentions),
        seen_target=model.seen_target,
        reaction_emoji=model.reaction_emoji,
        attempt_count=model.attempt_count,
        error_detail=model.error_detail,
        reaction_error=model.reaction_error,
        last_attempt_at=model.last_attempt_at,
        sent_at=model.sent_at,
    )


def _integration_task_record(model: IntegrationTaskModel) -> IntegrationTaskRecord:
    return IntegrationTaskRecord(
        id=model.id,
        guild_id=model.guild_id,
        task_type=model.task_type,
        deduplication_key=model.deduplication_key or "",
        state=IntegrationTaskState(model.state),
        scheduled_for=model.scheduled_for,
        attempt=model.attempt,
        result_value=model.result_value,
        started_at=model.started_at,
        completed_at=model.completed_at,
        error_code=model.error_code,
        error_detail=model.error_detail,
    )


def _archive_request_record(model: ChannelArchiveRequestModel) -> ChannelArchiveRequestRecord:
    return ChannelArchiveRequestRecord(
        id=model.id,
        guild_id=model.guild_id,
        discord_channel_id=model.discord_channel_id,
        original_channel_name=model.original_channel_name,
        archive_category_id=model.archive_category_id,
        requested_by_user_id=model.requested_by_user_id,
        reason=model.reason,
        state=ArchiveState(model.state),
        expires_at=model.expires_at,
        decided_by_user_id=model.decided_by_user_id,
        discord_approval_message_id=model.discord_approval_message_id,
        decided_at=model.decided_at,
    )


def _info_announcement_record(model: InfoAnnouncementModel) -> InfoAnnouncementRecord:
    return InfoAnnouncementRecord(
        id=model.id,
        guild_id=model.guild_id,
        title=model.title,
        description=model.description,
        link_url=model.link_url,
        image_url=model.image_url,
        valid_from=model.valid_from,
        valid_until=model.valid_until,
        active=model.active,
        created_by_user_id=model.created_by_user_id,
        updated_by_user_id=model.updated_by_user_id,
        deleted_at=model.deleted_at,
        version=model.version,
    )


def _web_session_record(model: WebSessionModel) -> WebSessionRecord:
    return WebSessionRecord(
        id=model.id,
        guild_id=model.guild_id,
        discord_user_id=model.discord_user_id,
        session_token_hash=model.session_token_hash,
        csrf_token_hash=model.csrf_token_hash,
        created_at=model.created_at,
        last_seen_at=model.last_seen_at,
        expires_at=model.expires_at,
        revoked_at=model.revoked_at,
    )


def _audit_record(model: AuditLogModel) -> AuditLogRecord:
    return AuditLogRecord(
        id=model.id,
        guild_id=model.guild_id,
        actor_user_id=model.actor_user_id,
        action=model.action,
        object_type=model.object_type,
        object_id=model.object_id,
        before_value=model.before_value,
        after_value=model.after_value,
        result=AuditResult(model.result),
        correlation_id=model.correlation_id,
        created_at=model.created_at,
    )


class SqlAlchemyGuildConfigRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, guild_id: int) -> GuildConfigRecord | None:
        model = await self._session.get(GuildConfigModel, guild_id)
        return None if model is None else _guild_record(model)

    async def add(self, record: GuildConfigRecord) -> None:
        self._session.add(GuildConfigModel(**_record_values(record)))
        await self._session.flush()

    async def list_all(self) -> list[GuildConfigRecord]:
        result = await self._session.scalars(
            select(GuildConfigModel).order_by(GuildConfigModel.guild_id)
        )
        return [_guild_record(model) for model in result]

    async def update(self, record: GuildConfigRecord, *, expected_version: int) -> int:
        model = await self._session.get(GuildConfigModel, record.guild_id)
        if model is None:
            raise LookupError("guild config not found")
        if model.version != expected_version:
            raise OptimisticLockError("guild config changed since it was loaded")
        for key, value in _record_values(record).items():
            if key not in {"guild_id", "version"}:
                setattr(model, key, value)
        await self._session.flush()
        return model.version

    async def lock_role_mutations(self, guild_id: int) -> None:
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": f"carlo:role-mutation:{guild_id}"},
        )


class SqlAlchemyCalendarSourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, source_id: uuid.UUID) -> CalendarSourceRecord | None:
        model = await self._session.get(CalendarSourceModel, source_id)
        return None if model is None else _calendar_source_record(model)

    async def add(self, record: CalendarSourceRecord) -> None:
        values = _record_values(record)
        values["sync_status"] = record.sync_status.value
        self._session.add(CalendarSourceModel(**values))
        await self._session.flush()

    async def list_for_guild(self, guild_id: int) -> list[CalendarSourceRecord]:
        result = await self._session.scalars(
            select(CalendarSourceModel)
            .where(CalendarSourceModel.guild_id == guild_id)
            .order_by(CalendarSourceModel.priority, CalendarSourceModel.id)
        )
        return [_calendar_source_record(model) for model in result]

    async def update(self, record: CalendarSourceRecord, *, expected_version: int) -> int:
        model = await self._session.get(CalendarSourceModel, record.id)
        if model is None:
            raise LookupError("calendar source not found")
        if model.version != expected_version:
            raise OptimisticLockError("calendar source changed since it was loaded")
        values = _record_values(record)
        values["sync_status"] = record.sync_status.value
        for key, value in values.items():
            if key not in {"id", "version"}:
                setattr(model, key, value)
        await self._session.flush()
        return model.version

    async def try_acquire_sync(
        self,
        source_id: uuid.UUID,
        *,
        attempted_at: datetime,
        stale_before: datetime,
    ) -> bool:
        result = cast(
            CursorResult[Any],
            await self._session.execute(
                update(CalendarSourceModel)
                .where(
                    CalendarSourceModel.id == source_id,
                    or_(
                        CalendarSourceModel.sync_status != SyncStatus.RUNNING.value,
                        CalendarSourceModel.last_sync_attempt_at.is_(None),
                        CalendarSourceModel.last_sync_attempt_at < stale_before,
                    ),
                )
                .values(
                    sync_status=SyncStatus.RUNNING.value,
                    last_sync_attempt_at=attempted_at,
                    last_sync_error=None,
                    version=CalendarSourceModel.version + 1,
                )
            ),
        )
        return result.rowcount == 1

    async def mark_sync_succeeded(
        self,
        source_id: uuid.UUID,
        *,
        sync_token: str,
        sync_token_query_key: str,
        completed_at: datetime,
        was_full_sync: bool,
    ) -> None:
        values: dict[str, Any] = {
            "sync_status": SyncStatus.SUCCEEDED.value,
            "sync_token": sync_token,
            "sync_token_query_key": sync_token_query_key,
            "last_sync_attempt_at": completed_at,
            "last_sync_success_at": completed_at,
            "last_sync_error": None,
        }
        if was_full_sync:
            values["last_full_sync_at"] = completed_at
        await self._update_required(source_id, **values)

    async def mark_sync_failed(
        self, source_id: uuid.UUID, *, attempted_at: datetime, error_code: str
    ) -> None:
        await self._update_required(
            source_id,
            sync_status=SyncStatus.FAILED.value,
            last_sync_attempt_at=attempted_at,
            last_sync_error=error_code,
        )

    async def _update_required(self, source_id: uuid.UUID, **values: Any) -> None:
        result = cast(
            CursorResult[Any],
            await self._session.execute(
                update(CalendarSourceModel)
                .where(CalendarSourceModel.id == source_id)
                .values(**values, version=CalendarSourceModel.version + 1)
            ),
        )
        if result.rowcount != 1:
            raise LookupError(f"calendar source not found: {source_id}")


class SqlAlchemyReactionConfigRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, guild_id: int) -> ReactionConfigRecord | None:
        model = await self._session.get(ReactionConfigModel, guild_id)
        if model is None:
            return None
        result = await self._session.scalars(
            select(ReactionConfigChannelModel.discord_channel_id)
            .where(ReactionConfigChannelModel.guild_id == guild_id)
            .order_by(ReactionConfigChannelModel.discord_channel_id)
        )
        return _reaction_config_record(model, tuple(result))

    async def add(self, record: ReactionConfigRecord) -> None:
        values = _record_values(record)
        channels = values.pop("auto_reaction_channel_ids")
        self._session.add(ReactionConfigModel(**values))
        await self._session.flush()
        self._session.add_all(
            ReactionConfigChannelModel(guild_id=record.guild_id, discord_channel_id=channel_id)
            for channel_id in channels
        )
        await self._session.flush()

    async def update(self, record: ReactionConfigRecord, *, expected_version: int) -> int:
        model = await self._session.get(ReactionConfigModel, record.guild_id)
        if model is None:
            raise LookupError("reaction config not found")
        if model.version != expected_version:
            raise OptimisticLockError("reaction config changed since it was loaded")
        values = _record_values(record)
        channels = values.pop("auto_reaction_channel_ids")
        for key, value in values.items():
            if key not in {"guild_id", "version"}:
                setattr(model, key, value)
        await self._session.execute(
            delete(ReactionConfigChannelModel).where(
                ReactionConfigChannelModel.guild_id == record.guild_id
            )
        )
        self._session.add_all(
            ReactionConfigChannelModel(guild_id=record.guild_id, discord_channel_id=channel_id)
            for channel_id in channels
        )
        await self._session.flush()
        return model.version


class SqlAlchemyExternalEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, event_id: uuid.UUID) -> ExternalEventRecord | None:
        model = await self._session.get(ExternalEventModel, event_id)
        return None if model is None else _external_event_record(model)

    async def get_by_source_key(self, source_key: str) -> ExternalEventRecord | None:
        result = await self._session.scalars(
            select(ExternalEventModel).where(ExternalEventModel.source_key == source_key)
        )
        model = result.one_or_none()
        return None if model is None else _external_event_record(model)

    async def add(self, record: ExternalEventRecord) -> None:
        values = _record_values(record)
        values["status"] = record.status.value
        self._session.add(ExternalEventModel(**values))
        await self._session.flush()

    async def list_for_source(self, source_id: uuid.UUID) -> list[ExternalEventRecord]:
        result = await self._session.scalars(
            select(ExternalEventModel).where(ExternalEventModel.calendar_source_id == source_id)
        )
        return [_external_event_record(model) for model in result]

    async def list_for_sources(
        self, source_ids: tuple[uuid.UUID, ...]
    ) -> list[ExternalEventRecord]:
        if not source_ids:
            return []
        result = await self._session.scalars(
            select(ExternalEventModel)
            .where(ExternalEventModel.calendar_source_id.in_(source_ids))
            .order_by(ExternalEventModel.calendar_source_id, ExternalEventModel.source_key)
        )
        return [_external_event_record(model) for model in result]

    async def upsert_from_sync(self, record: ExternalEventRecord) -> bool:
        result = await self._session.scalars(
            select(ExternalEventModel).where(ExternalEventModel.source_key == record.source_key)
        )
        model = result.one_or_none()
        values = _external_event_values(record)
        if model is None:
            self._session.add(ExternalEventModel(**values))
            await self._session.flush()
            return True

        for field_name, value in values.items():
            if field_name != "id":
                setattr(model, field_name, value)
        await self._session.flush()
        return False

    async def cancel_by_provider_event_id(
        self,
        source_id: uuid.UUID,
        provider_event_id: str,
        *,
        synced_at: datetime,
    ) -> bool:
        result = cast(
            CursorResult[Any],
            await self._session.execute(
                update(ExternalEventModel)
                .where(
                    ExternalEventModel.calendar_source_id == source_id,
                    ExternalEventModel.provider_event_id == provider_event_id,
                )
                .values(
                    status=ExternalEventStatus.CANCELLED.value,
                    last_synced_at=synced_at,
                    deleted_at=synced_at,
                )
            ),
        )
        if result.rowcount > 1:
            raise RuntimeError("provider event identity is not unique within calendar source")
        return result.rowcount == 1

    async def mark_missing_deleted(
        self,
        source_id: uuid.UUID,
        seen_source_keys: set[str],
        *,
        deleted_at: datetime,
    ) -> int:
        statement = update(ExternalEventModel).where(
            ExternalEventModel.calendar_source_id == source_id,
            ExternalEventModel.deleted_at.is_(None),
        )
        if seen_source_keys:
            statement = statement.where(ExternalEventModel.source_key.not_in(seen_source_keys))
        result = cast(
            CursorResult[Any],
            await self._session.execute(statement.values(deleted_at=deleted_at)),
        )
        return result.rowcount

    async def mark_deleted(self, event_id: uuid.UUID, deleted_at: datetime) -> bool:
        result = cast(
            CursorResult[Any],
            await self._session.execute(
                update(ExternalEventModel)
                .where(ExternalEventModel.id == event_id)
                .values(deleted_at=deleted_at)
            ),
        )
        return bool(result.rowcount)


class SqlAlchemyEventOverrideRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, external_event_id: uuid.UUID) -> EventOverrideRecord | None:
        model = await self._session.get(EventOverrideModel, external_event_id)
        return None if model is None else _event_override_record(model)

    async def add(self, record: EventOverrideRecord) -> None:
        self._session.add(EventOverrideModel(**_override_values(record)))
        await self._session.flush()

    async def update(self, record: EventOverrideRecord, *, expected_version: int) -> int:
        next_version = expected_version + 1
        values = _override_values(record)
        values.pop("external_event_id")
        values["version"] = next_version
        result = cast(
            CursorResult[Any],
            await self._session.execute(
                update(EventOverrideModel)
                .where(
                    EventOverrideModel.external_event_id == record.external_event_id,
                    EventOverrideModel.version == expected_version,
                )
                .values(**values)
            ),
        )
        if result.rowcount != 1:
            raise OptimisticLockError("event override changed since it was loaded")
        return next_version

    async def list_for_events(self, event_ids: tuple[uuid.UUID, ...]) -> list[EventOverrideRecord]:
        if not event_ids:
            return []
        result = await self._session.scalars(
            select(EventOverrideModel)
            .where(EventOverrideModel.external_event_id.in_(event_ids))
            .order_by(EventOverrideModel.external_event_id)
        )
        return [_event_override_record(model) for model in result]


class SqlAlchemyEventSeriesOverrideRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_effective(
        self,
        source_id: uuid.UUID,
        series_key: str,
        effective_from_key: str,
    ) -> EventSeriesOverrideRecord | None:
        result = await self._session.scalars(
            select(EventSeriesOverrideModel).where(
                EventSeriesOverrideModel.calendar_source_id == source_id,
                EventSeriesOverrideModel.series_key == series_key,
                EventSeriesOverrideModel.effective_from_key == effective_from_key,
            )
        )
        model = result.one_or_none()
        return None if model is None else _event_series_override_record(model)

    async def add(self, record: EventSeriesOverrideRecord) -> None:
        values = _record_values(record)
        values["description_state"] = record.description_state.value
        self._session.add(EventSeriesOverrideModel(**values))
        await self._session.flush()

    async def update(self, record: EventSeriesOverrideRecord, *, expected_version: int) -> int:
        next_version = expected_version + 1
        values = _record_values(record)
        values.pop("id")
        values["description_state"] = record.description_state.value
        values["version"] = next_version
        result = cast(
            CursorResult[Any],
            await self._session.execute(
                update(EventSeriesOverrideModel)
                .where(
                    EventSeriesOverrideModel.id == record.id,
                    EventSeriesOverrideModel.version == expected_version,
                )
                .values(**values)
            ),
        )
        if result.rowcount != 1:
            raise OptimisticLockError("series override changed since it was loaded")
        return next_version

    async def list_for_sources(
        self, source_ids: tuple[uuid.UUID, ...]
    ) -> list[EventSeriesOverrideRecord]:
        if not source_ids:
            return []
        result = await self._session.scalars(
            select(EventSeriesOverrideModel)
            .where(EventSeriesOverrideModel.calendar_source_id.in_(source_ids))
            .order_by(
                EventSeriesOverrideModel.calendar_source_id,
                EventSeriesOverrideModel.series_key,
                EventSeriesOverrideModel.effective_from_key,
                EventSeriesOverrideModel.id,
            )
        )
        return [_event_series_override_record(model) for model in result]


class SqlAlchemyManualEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, event_id: uuid.UUID) -> ManualEventRecord | None:
        model = await self._session.get(ManualEventModel, event_id)
        return None if model is None else _manual_event_record(model)

    async def add(self, record: ManualEventRecord) -> None:
        self._session.add(ManualEventModel(**_record_values(record)))
        await self._session.flush()

    async def update(self, record: ManualEventRecord, *, expected_version: int) -> int:
        next_version = expected_version + 1
        values = _record_values(record)
        values.pop("id")
        values["version"] = next_version
        result = cast(
            CursorResult[Any],
            await self._session.execute(
                update(ManualEventModel)
                .where(
                    ManualEventModel.id == record.id,
                    ManualEventModel.version == expected_version,
                )
                .values(**values)
            ),
        )
        if result.rowcount != 1:
            raise OptimisticLockError("manual event changed since it was loaded")
        return next_version

    async def list_for_guild(self, guild_id: int) -> list[ManualEventRecord]:
        result = await self._session.scalars(
            select(ManualEventModel)
            .where(ManualEventModel.guild_id == guild_id)
            .order_by(ManualEventModel.starts_on, ManualEventModel.starts_at, ManualEventModel.id)
        )
        return [_manual_event_record(model) for model in result]


class SqlAlchemyInfoAnnouncementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, announcement_id: uuid.UUID) -> InfoAnnouncementRecord | None:
        model = await self._session.get(InfoAnnouncementModel, announcement_id)
        return None if model is None else _info_announcement_record(model)

    async def add(self, record: InfoAnnouncementRecord) -> None:
        self._session.add(InfoAnnouncementModel(**_record_values(record)))
        await self._session.flush()

    async def update(self, record: InfoAnnouncementRecord, *, expected_version: int) -> int:
        next_version = expected_version + 1
        values = _record_values(record)
        values.pop("id")
        values["version"] = next_version
        result = cast(
            CursorResult[Any],
            await self._session.execute(
                update(InfoAnnouncementModel)
                .where(
                    InfoAnnouncementModel.id == record.id,
                    InfoAnnouncementModel.version == expected_version,
                )
                .values(**values)
            ),
        )
        if result.rowcount != 1:
            raise OptimisticLockError("INFO announcement changed since it was loaded")
        return next_version

    async def list_for_guild(self, guild_id: int) -> list[InfoAnnouncementRecord]:
        result = await self._session.scalars(
            select(InfoAnnouncementModel)
            .where(InfoAnnouncementModel.guild_id == guild_id)
            .order_by(
                InfoAnnouncementModel.valid_from,
                InfoAnnouncementModel.title,
                InfoAnnouncementModel.id,
            )
        )
        return [_info_announcement_record(model) for model in result]


class SqlAlchemyPublicationRunRepository:
    _COMPLETED_STATES = (
        PublicationState.SUCCEEDED_AUTOMATIC.value,
        PublicationState.SUCCEEDED_MANUAL.value,
        PublicationState.SKIPPED_AFTER_MANUAL.value,
    )

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def completed_slot_keys(self, guild_id: int) -> frozenset[str]:
        result = await self._session.scalars(
            select(PublicationRunModel.slot_key).where(
                PublicationRunModel.guild_id == guild_id,
                PublicationRunModel.state.in_(self._COMPLETED_STATES),
            )
        )
        return frozenset(result)

    async def lock_slot(self, guild_id: int, slot_key: str) -> None:
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
            {"lock_key": f"publication:{guild_id}:{slot_key}"},
        )

    async def get(self, run_id: uuid.UUID) -> PublicationRunRecord | None:
        model = await self._session.get(PublicationRunModel, run_id)
        return None if model is None else _publication_run_record(model)

    async def get_for_slot(self, guild_id: int, slot_key: str) -> PublicationRunRecord | None:
        model = (
            await self._session.scalars(
                select(PublicationRunModel).where(
                    PublicationRunModel.guild_id == guild_id,
                    PublicationRunModel.slot_key == slot_key,
                )
            )
        ).one_or_none()
        return None if model is None else _publication_run_record(model)

    async def list_for_guild(self, guild_id: int, *, limit: int = 50) -> list[PublicationRunRecord]:
        result = await self._session.scalars(
            select(PublicationRunModel)
            .where(PublicationRunModel.guild_id == guild_id)
            .order_by(PublicationRunModel.scheduled_for.desc(), PublicationRunModel.id.desc())
            .limit(limit)
        )
        return [_publication_run_record(model) for model in result]

    async def list_items(self, run_id: uuid.UUID) -> list[PublicationItemRecord]:
        result = await self._session.scalars(
            select(PublicationItemModel)
            .where(PublicationItemModel.publication_run_id == run_id)
            .order_by(PublicationItemModel.position)
        )
        return [_publication_item_record(model) for model in result]

    async def add_snapshot(
        self,
        run: PublicationRunRecord,
        items: tuple[PublicationItemRecord, ...],
        messages: tuple[PublicationMessageRecord, ...],
    ) -> None:
        self._session.add(
            PublicationRunModel(
                id=run.id,
                guild_id=run.guild_id,
                slot_key=run.slot_key,
                scheduled_for=run.scheduled_for,
                mode=run.mode.value,
                initiated_by_user_id=run.initiated_by_user_id,
                state=run.state.value,
                attempt=run.attempt,
                idempotency_key=run.idempotency_key,
                composer_version=run.composer_version,
                intro_text=run.intro_text,
                intro_prompt_version=run.intro_prompt_version,
                intro_used_fallback=run.intro_used_fallback,
                outro_text=run.outro_text,
                warning_codes=list(run.warning_codes),
                started_at=run.started_at,
                completed_at=run.completed_at,
                error_code=run.error_code,
                error_detail=run.error_detail,
            )
        )
        # These models deliberately expose no ORM relationships; flush the parent
        # explicitly so PostgreSQL can validate child foreign keys deterministically.
        await self._session.flush()
        self._session.add_all(
            [
                PublicationItemModel(
                    id=item.id,
                    publication_run_id=item.publication_run_id,
                    item_type=item.item_type.value,
                    position=item.position,
                    external_event_id=item.external_event_id,
                    manual_event_id=item.manual_event_id,
                    info_announcement_id=item.info_announcement_id,
                    final_title=item.final_title,
                    final_description=item.final_description,
                    display_time=item.display_time,
                    day_emoji=item.day_emoji,
                    starts_at=item.starts_at,
                    ends_at=item.ends_at,
                    starts_on=item.starts_on,
                    ends_on=item.ends_on,
                    is_all_day=item.is_all_day,
                    link_url=item.link_url,
                    image_url=item.image_url,
                )
                for item in items
            ]
        )
        self._session.add_all(
            [
                PublicationMessageModel(
                    id=message.id,
                    publication_run_id=message.publication_run_id,
                    position=message.position,
                    discord_channel_id=message.discord_channel_id,
                    discord_message_id=message.discord_message_id,
                    state=message.state.value,
                    part_key=message.part_key,
                    nonce=message.nonce,
                    content=message.content,
                    embeds=list(message.embeds),
                    allowed_mentions=list(message.allowed_mentions),
                    seen_target=message.seen_target,
                    reaction_emoji=message.reaction_emoji,
                    attempt_count=message.attempt_count,
                    error_detail=message.error_detail,
                    reaction_error=message.reaction_error,
                    last_attempt_at=message.last_attempt_at,
                    sent_at=message.sent_at,
                )
                for message in messages
            ]
        )
        await self._session.flush()

    async def list_messages(self, run_id: uuid.UUID) -> list[PublicationMessageRecord]:
        result = await self._session.scalars(
            select(PublicationMessageModel)
            .where(PublicationMessageModel.publication_run_id == run_id)
            .order_by(PublicationMessageModel.position)
        )
        return [_publication_message_record(model) for model in result]

    async def claim_message(self, message_id: uuid.UUID, *, attempted_at: datetime) -> bool:
        result = cast(
            CursorResult[Any],
            await self._session.execute(
                update(PublicationMessageModel)
                .where(
                    PublicationMessageModel.id == message_id,
                    PublicationMessageModel.discord_message_id.is_(None),
                    PublicationMessageModel.state.in_(
                        (
                            PublicationMessageState.PENDING.value,
                            PublicationMessageState.FAILED.value,
                        )
                    ),
                )
                .values(
                    state=PublicationMessageState.SENDING.value,
                    attempt_count=PublicationMessageModel.attempt_count + 1,
                    last_attempt_at=attempted_at,
                    error_detail=None,
                )
            ),
        )
        return result.rowcount == 1

    async def increment_message_attempt(
        self, message_id: uuid.UUID, *, attempted_at: datetime
    ) -> None:
        await self._session.execute(
            update(PublicationMessageModel)
            .where(PublicationMessageModel.id == message_id)
            .values(
                attempt_count=PublicationMessageModel.attempt_count + 1,
                last_attempt_at=attempted_at,
            )
        )

    async def mark_message_sent(
        self, message_id: uuid.UUID, *, discord_message_id: int, sent_at: datetime
    ) -> None:
        await self._session.execute(
            update(PublicationMessageModel)
            .where(PublicationMessageModel.id == message_id)
            .values(
                state=PublicationMessageState.SENT.value,
                discord_message_id=discord_message_id,
                sent_at=sent_at,
                error_detail=None,
            )
        )

    async def mark_message_failed(self, message_id: uuid.UUID, *, detail: str) -> None:
        await self._session.execute(
            update(PublicationMessageModel)
            .where(PublicationMessageModel.id == message_id)
            .values(state=PublicationMessageState.FAILED.value, error_detail=detail)
        )

    async def mark_reaction_warning(self, message_id: uuid.UUID, *, detail: str) -> None:
        await self._session.execute(
            update(PublicationMessageModel)
            .where(PublicationMessageModel.id == message_id)
            .values(reaction_error=detail)
        )

    async def reset_uncertain_message(self, message_id: uuid.UUID) -> None:
        await self._session.execute(
            update(PublicationMessageModel)
            .where(
                PublicationMessageModel.id == message_id,
                PublicationMessageModel.state == PublicationMessageState.UNCERTAIN.value,
                PublicationMessageModel.discord_message_id.is_(None),
            )
            .values(state=PublicationMessageState.PENDING.value, error_detail=None)
        )

    async def resolve_incidents(
        self,
        run_id: uuid.UUID,
        *,
        resolution: str,
        resolved_by_user_id: int,
        resolved_at: datetime,
    ) -> None:
        await self._session.execute(
            update(PublicationIncidentModel)
            .where(
                PublicationIncidentModel.publication_run_id == run_id,
                PublicationIncidentModel.state == PublicationIncidentState.OPEN.value,
            )
            .values(
                state=PublicationIncidentState.RESOLVED.value,
                resolution=resolution,
                resolved_by_user_id=resolved_by_user_id,
                resolved_at=resolved_at,
            )
        )

    async def count_open_incidents(self, guild_id: int) -> int:
        result = await self._session.scalar(
            select(func.count(PublicationIncidentModel.id))
            .join(
                PublicationRunModel,
                PublicationRunModel.id == PublicationIncidentModel.publication_run_id,
            )
            .where(
                PublicationRunModel.guild_id == guild_id,
                PublicationIncidentModel.state == PublicationIncidentState.OPEN.value,
            )
        )
        return int(result or 0)

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
    ) -> None:
        values: dict[str, object] = {
            "state": state.value,
            "completed_at": completed_at,
            "error_code": error_code,
            "error_detail": error_detail,
        }
        if increment_attempt:
            values["attempt"] = PublicationRunModel.attempt + 1
        if warning_codes is not None:
            values["warning_codes"] = list(warning_codes)
        await self._session.execute(
            update(PublicationRunModel).where(PublicationRunModel.id == run_id).values(**values)
        )

    async def mark_uncertain(
        self,
        run_id: uuid.UUID,
        message_id: uuid.UUID,
        *,
        correlation_id: str,
        summary: str,
    ) -> None:
        guild_id = await self._session.scalar(
            select(PublicationRunModel.guild_id).where(PublicationRunModel.id == run_id)
        )
        if guild_id is None:
            raise LookupError(f"publication run not found: {run_id}")
        await self._session.execute(
            update(PublicationMessageModel)
            .where(PublicationMessageModel.id == message_id)
            .values(state=PublicationMessageState.UNCERTAIN.value, error_detail=summary)
        )
        await self.set_state(
            run_id,
            PublicationState.PARTIALLY_PUBLISHED,
            error_code="discord_effect_uncertain",
            error_detail=summary,
        )
        self._session.add(
            PublicationIncidentModel(
                id=uuid.uuid4(),
                guild_id=guild_id,
                publication_run_id=run_id,
                publication_message_id=message_id,
                kind="discord_effect_uncertain",
                state=PublicationIncidentState.OPEN.value,
                correlation_id=correlation_id,
                summary=summary,
            )
        )
        await self._session.flush()

    async def mark_delivery_exhausted(
        self,
        run_id: uuid.UUID,
        message_id: uuid.UUID,
        *,
        correlation_id: str,
        summary: str,
    ) -> None:
        guild_id = await self._session.scalar(
            select(PublicationRunModel.guild_id).where(PublicationRunModel.id == run_id)
        )
        if guild_id is None:
            raise LookupError(f"publication run not found: {run_id}")
        await self.mark_message_failed(message_id, detail=summary)
        await self.set_state(
            run_id,
            PublicationState.FAILED,
            completed_at=datetime.now(UTC),
            error_code="discord_delivery_exhausted",
            error_detail=summary,
        )
        existing = await self._session.scalar(
            select(PublicationIncidentModel.id).where(
                PublicationIncidentModel.publication_run_id == run_id,
                PublicationIncidentModel.kind == "discord_delivery_exhausted",
                PublicationIncidentModel.state == PublicationIncidentState.OPEN.value,
            )
        )
        if existing is None:
            self._session.add(
                PublicationIncidentModel(
                    id=uuid.uuid4(),
                    guild_id=guild_id,
                    publication_run_id=run_id,
                    publication_message_id=message_id,
                    kind="discord_delivery_exhausted",
                    state=PublicationIncidentState.OPEN.value,
                    correlation_id=correlation_id,
                    summary=summary,
                )
            )
        await self._session.flush()

    async def list_recoverable(self, *, attempted_before: datetime) -> list[PublicationRunRecord]:
        fresh_active_send = (
            select(PublicationMessageModel.id)
            .where(
                PublicationMessageModel.publication_run_id == PublicationRunModel.id,
                PublicationMessageModel.state == PublicationMessageState.SENDING.value,
                or_(
                    PublicationMessageModel.last_attempt_at.is_(None),
                    PublicationMessageModel.last_attempt_at >= attempted_before,
                ),
            )
            .exists()
        )
        result = await self._session.scalars(
            select(PublicationRunModel)
            .where(
                PublicationRunModel.state.in_(
                    (
                        PublicationState.PREPARING.value,
                        PublicationState.PUBLISHING.value,
                        PublicationState.RETRY_PENDING.value,
                    )
                ),
                ~fresh_active_send,
            )
            .order_by(PublicationRunModel.scheduled_for)
        )
        return [_publication_run_record(model) for model in result]


class SqlAlchemyShadowPublicationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, capture: ShadowPublicationRecord) -> ShadowPublicationRecord:
        values = asdict(capture)
        values["warning_codes"] = list(capture.warning_codes)
        statement = (
            postgresql_insert(ShadowPublicationModel)
            .values(**values)
            .on_conflict_do_update(
                index_elements=(
                    ShadowPublicationModel.guild_id,
                    ShadowPublicationModel.slot_key,
                ),
                set_={
                    "scheduled_for": capture.scheduled_for,
                    "last_observed_at": capture.last_observed_at,
                    "observation_count": ShadowPublicationModel.observation_count + 1,
                    "draft_sha256": capture.draft_sha256,
                    "draft_json": capture.draft_json,
                    "item_count": capture.item_count,
                    "message_count": capture.message_count,
                    "calendar_sync_valid": capture.calendar_sync_valid,
                    "calendar_sync_evidence": capture.calendar_sync_evidence,
                    "warning_codes": list(capture.warning_codes),
                },
            )
            .returning(ShadowPublicationModel)
        )
        model = (await self._session.scalars(statement)).one()
        return _shadow_publication_record(model)

    async def list_for_guild(
        self, guild_id: int, *, limit: int = 20
    ) -> list[ShadowPublicationRecord]:
        result = await self._session.scalars(
            select(ShadowPublicationModel)
            .where(ShadowPublicationModel.guild_id == guild_id)
            .order_by(
                ShadowPublicationModel.scheduled_for.desc(),
                ShadowPublicationModel.id.desc(),
            )
            .limit(limit)
        )
        return [_shadow_publication_record(model) for model in result]


class SqlAlchemyRuntimeHeartbeatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, heartbeat: RuntimeHeartbeatRecord) -> None:
        await self._session.execute(
            postgresql_insert(RuntimeHeartbeatModel)
            .values(**asdict(heartbeat))
            .on_conflict_do_update(
                index_elements=(RuntimeHeartbeatModel.id,),
                set_={
                    "state": heartbeat.state,
                    "last_seen_at": heartbeat.last_seen_at,
                    "details": heartbeat.details,
                },
            )
        )

    async def list_for_guild(
        self, guild_id: int, *, limit: int = 50
    ) -> list[RuntimeHeartbeatRecord]:
        result = await self._session.scalars(
            select(RuntimeHeartbeatModel)
            .where(RuntimeHeartbeatModel.guild_id == guild_id)
            .order_by(RuntimeHeartbeatModel.last_seen_at.desc())
            .limit(limit)
        )
        return [_runtime_heartbeat_record(model) for model in result]


class SqlAlchemyIntegrationTaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim(self, record: IntegrationTaskRecord) -> IntegrationTaskRecord:
        statement = (
            postgresql_insert(IntegrationTaskModel)
            .values(
                id=record.id,
                guild_id=record.guild_id,
                task_type=record.task_type,
                deduplication_key=record.deduplication_key,
                state=record.state.value,
                scheduled_for=record.scheduled_for,
                attempt=record.attempt,
                result_value=record.result_value,
                started_at=record.started_at,
                completed_at=record.completed_at,
                error_code=record.error_code,
                error_detail=record.error_detail,
            )
            .on_conflict_do_nothing(constraint="deduplication")
            .returning(IntegrationTaskModel.id)
        )
        inserted_id = await self._session.scalar(statement)
        if inserted_id is not None:
            await self._session.flush()
            return record
        model = (
            await self._session.scalars(
                select(IntegrationTaskModel).where(
                    IntegrationTaskModel.guild_id == record.guild_id,
                    IntegrationTaskModel.task_type == record.task_type,
                    IntegrationTaskModel.deduplication_key == record.deduplication_key,
                )
            )
        ).one()
        return _integration_task_record(model)

    async def set_result(
        self,
        task_id: uuid.UUID,
        *,
        state: IntegrationTaskState,
        completed_at: datetime,
        result_value: dict[str, object] | None = None,
        error_code: str | None = None,
        error_detail: str | None = None,
    ) -> None:
        await self._session.execute(
            update(IntegrationTaskModel)
            .where(IntegrationTaskModel.id == task_id)
            .values(
                state=state.value,
                completed_at=completed_at,
                result_value=result_value,
                error_code=error_code,
                error_detail=error_detail,
            )
        )

    async def restart(self, task_id: uuid.UUID, *, started_at: datetime) -> None:
        await self._session.execute(
            update(IntegrationTaskModel)
            .where(IntegrationTaskModel.id == task_id)
            .values(
                state=IntegrationTaskState.RUNNING.value,
                attempt=IntegrationTaskModel.attempt + 1,
                started_at=started_at,
                completed_at=None,
                error_code=None,
                error_detail=None,
            )
        )

    async def list_for_guild(
        self, guild_id: int, *, limit: int = 20
    ) -> list[IntegrationTaskRecord]:
        result = await self._session.scalars(
            select(IntegrationTaskModel)
            .where(IntegrationTaskModel.guild_id == guild_id)
            .order_by(IntegrationTaskModel.scheduled_for.desc(), IntegrationTaskModel.id.desc())
            .limit(limit)
        )
        return [_integration_task_record(model) for model in result]


class SqlAlchemyChannelArchiveRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, request_id: uuid.UUID) -> ChannelArchiveRequestRecord | None:
        model = await self._session.get(ChannelArchiveRequestModel, request_id)
        return None if model is None else _archive_request_record(model)

    async def add(self, record: ChannelArchiveRequestRecord) -> None:
        self._session.add(
            ChannelArchiveRequestModel(
                id=record.id,
                guild_id=record.guild_id,
                discord_channel_id=record.discord_channel_id,
                original_channel_name=record.original_channel_name,
                archive_category_id=record.archive_category_id,
                requested_by_user_id=record.requested_by_user_id,
                reason=record.reason,
                state=record.state.value,
                expires_at=record.expires_at,
                decided_by_user_id=record.decided_by_user_id,
                discord_approval_message_id=record.discord_approval_message_id,
                decided_at=record.decided_at,
            )
        )
        await self._session.flush()

    async def list_pending(self, guild_id: int) -> list[ChannelArchiveRequestRecord]:
        result = await self._session.scalars(
            select(ChannelArchiveRequestModel)
            .where(
                ChannelArchiveRequestModel.guild_id == guild_id,
                ChannelArchiveRequestModel.state.in_(
                    (
                        ArchiveState.PENDING.value,
                        ArchiveState.ARCHIVING.value,
                        ArchiveState.FAILED.value,
                    )
                ),
            )
            .order_by(ChannelArchiveRequestModel.created_at)
        )
        return [_archive_request_record(model) for model in result]

    async def list_recoverable(self, guild_id: int) -> list[ChannelArchiveRequestRecord]:
        result = await self._session.scalars(
            select(ChannelArchiveRequestModel)
            .where(
                ChannelArchiveRequestModel.guild_id == guild_id,
                ChannelArchiveRequestModel.state.in_(
                    (ArchiveState.ARCHIVING.value, ArchiveState.FAILED.value)
                ),
            )
            .order_by(ChannelArchiveRequestModel.decided_at, ChannelArchiveRequestModel.created_at)
        )
        return [_archive_request_record(model) for model in result]

    async def get_pending_for_channel(
        self, guild_id: int, channel_id: int
    ) -> ChannelArchiveRequestRecord | None:
        model = (
            await self._session.scalars(
                select(ChannelArchiveRequestModel).where(
                    ChannelArchiveRequestModel.guild_id == guild_id,
                    ChannelArchiveRequestModel.discord_channel_id == channel_id,
                    ChannelArchiveRequestModel.state.in_(
                        (ArchiveState.PENDING.value, ArchiveState.ARCHIVING.value)
                    ),
                )
            )
        ).one_or_none()
        return None if model is None else _archive_request_record(model)

    async def set_approval_message(self, request_id: uuid.UUID, message_id: int) -> None:
        await self._session.execute(
            update(ChannelArchiveRequestModel)
            .where(
                ChannelArchiveRequestModel.id == request_id,
                ChannelArchiveRequestModel.state == ArchiveState.PENDING.value,
            )
            .values(discord_approval_message_id=message_id)
        )

    async def decide(
        self,
        request_id: uuid.UUID,
        *,
        state: ArchiveState,
        decided_by_user_id: int,
        decided_at: datetime,
    ) -> bool:
        result = cast(
            CursorResult[Any],
            await self._session.execute(
                update(ChannelArchiveRequestModel)
                .where(
                    ChannelArchiveRequestModel.id == request_id,
                    ChannelArchiveRequestModel.state == ArchiveState.PENDING.value,
                )
                .values(
                    state=state.value,
                    decided_by_user_id=decided_by_user_id,
                    decided_at=decided_at,
                )
            ),
        )
        return result.rowcount == 1

    async def mark_execution(
        self,
        request_id: uuid.UUID,
        *,
        state: ArchiveState,
        expected_states: tuple[ArchiveState, ...] = (ArchiveState.ARCHIVING,),
    ) -> bool:
        result = cast(
            CursorResult[Any],
            await self._session.execute(
                update(ChannelArchiveRequestModel)
                .where(
                    ChannelArchiveRequestModel.id == request_id,
                    ChannelArchiveRequestModel.state.in_(
                        tuple(expected.value for expected in expected_states)
                    ),
                )
                .values(state=state.value)
            ),
        )
        return result.rowcount == 1


class SqlAlchemyWebSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: WebSessionRecord) -> None:
        self._session.add(WebSessionModel(**_record_values(record)))
        await self._session.flush()

    async def get_active_by_token_hash(
        self, token_hash: str, *, now: datetime
    ) -> WebSessionRecord | None:
        result = await self._session.scalars(
            select(WebSessionModel).where(
                WebSessionModel.session_token_hash == token_hash,
                WebSessionModel.revoked_at.is_(None),
                WebSessionModel.expires_at > now,
            )
        )
        model = result.one_or_none()
        return None if model is None else _web_session_record(model)

    async def touch(self, session_id: uuid.UUID, *, seen_at: datetime) -> None:
        await self._session.execute(
            update(WebSessionModel)
            .where(WebSessionModel.id == session_id, WebSessionModel.revoked_at.is_(None))
            .values(last_seen_at=seen_at)
        )

    async def revoke(self, session_id: uuid.UUID, *, revoked_at: datetime) -> bool:
        result = cast(
            CursorResult[Any],
            await self._session.execute(
                update(WebSessionModel)
                .where(WebSessionModel.id == session_id, WebSessionModel.revoked_at.is_(None))
                .values(revoked_at=revoked_at)
            ),
        )
        return result.rowcount == 1


class SqlAlchemyAuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: AuditLogRecord) -> None:
        values = _record_values(record)
        values["result"] = record.result.value
        if record.created_at is None:
            values.pop("created_at")
        self._session.add(AuditLogModel(**values))
        await self._session.flush()

    async def list_for_object(self, object_type: str, object_id: str) -> list[AuditLogRecord]:
        result = await self._session.scalars(
            select(AuditLogModel)
            .where(
                AuditLogModel.object_type == object_type,
                AuditLogModel.object_id == object_id,
            )
            .order_by(AuditLogModel.created_at, AuditLogModel.id)
        )
        return [_audit_record(model) for model in result]

    async def list_for_guild(
        self,
        guild_id: int,
        *,
        limit: int,
        object_types: tuple[str, ...] | None = None,
    ) -> list[AuditLogRecord]:
        query = select(AuditLogModel).where(AuditLogModel.guild_id == guild_id)
        if object_types is not None:
            query = query.where(AuditLogModel.object_type.in_(object_types))
        result = await self._session.scalars(
            query.order_by(AuditLogModel.created_at.desc(), AuditLogModel.id.desc()).limit(limit)
        )
        return [_audit_record(model) for model in result]


PersistenceRecord = (
    GuildConfigRecord
    | CalendarSourceRecord
    | ExternalEventRecord
    | EventOverrideRecord
    | EventSeriesOverrideRecord
    | ManualEventRecord
    | InfoAnnouncementRecord
    | WebSessionRecord
    | AuditLogRecord
    | ReactionConfigRecord
)


def _record_values(record: PersistenceRecord) -> dict[str, Any]:
    return asdict(record)


def _override_values(record: EventOverrideRecord) -> dict[str, Any]:
    values = _record_values(record)
    values["description_state"] = record.description_state.value
    values["inclusion_decision"] = record.inclusion_decision.value
    return values


def _external_event_values(record: ExternalEventRecord) -> dict[str, Any]:
    values = _record_values(record)
    values["status"] = record.status.value
    return values
