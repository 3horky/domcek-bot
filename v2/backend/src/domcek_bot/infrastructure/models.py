"""SQLAlchemy models for the normalized E2 PostgreSQL schema."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

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
    UndoState,
)

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def enum_check(column: str, enum_type: type[StrEnum]) -> str:
    values = ", ".join(f"'{item.value}'" for item in enum_type)
    return f"{column} IN ({values})"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class GuildConfigModel(TimestampMixin, Base):
    __tablename__ = "guild_config"
    __table_args__ = (
        CheckConstraint("publication_weekday BETWEEN 0 AND 6", name="publication_weekday"),
        CheckConstraint(
            "publication_grace_seconds BETWEEN 0 AND 300",
            name="publication_grace_seconds",
        ),
        CheckConstraint("everyone_mention_enabled", name="everyone_mention_required"),
        CheckConstraint("version >= 1", name="positive_version"),
    )

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    admin_role_id: Mapped[int | None] = mapped_column(BigInteger)
    team_mod_role_id: Mapped[int | None] = mapped_column(BigInteger)
    publisher_role_id: Mapped[int | None] = mapped_column(BigInteger)
    announcement_channel_id: Mapped[int | None] = mapped_column(BigInteger)
    command_channel_id: Mapped[int | None] = mapped_column(BigInteger)
    moderator_channel_id: Mapped[int | None] = mapped_column(BigInteger)
    projects_category_id: Mapped[int | None] = mapped_column(BigInteger)
    archive_category_id: Mapped[int | None] = mapped_column(BigInteger)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Bratislava")
    publication_weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    publication_time: Mapped[time] = mapped_column(
        Time(timezone=False), nullable=False, default=time(20)
    )
    automatic_publication_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    publish_google_descriptions: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    generated_intro_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    everyone_mention_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_stale_calendar_cache: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    publication_grace_seconds: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=30)
    publication_guard_recipient_ids: Mapped[list[int]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    alert_calendar_sync_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    alert_publication_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    alert_channel_operations_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    alert_role_operations_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    alert_publication_reminder_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    closing_message: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__: dict[str, Any] = {  # noqa: RUF012
        "version_id_col": version,
        "version_id_generator": lambda current: (current or 0) + 1,
    }


class CalendarSourceModel(TimestampMixin, Base):
    __tablename__ = "calendar_source"
    __table_args__ = (
        UniqueConstraint("guild_id", "provider", "external_calendar_id", name="calendar_identity"),
        CheckConstraint(enum_check("sync_status", SyncStatus), name="sync_status"),
        Index("ix_calendar_source_guild_active_priority", "guild_id", "active", "priority"),
        CheckConstraint("version >= 1", name="positive_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guild_config.guild_id", ondelete="RESTRICT"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    external_calendar_id: Mapped[str] = mapped_column(String(512), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sync_token: Mapped[str | None] = mapped_column(Text)
    sync_token_query_key: Mapped[str | None] = mapped_column(String(64))
    sync_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default=SyncStatus.NEVER.value
    )
    last_sync_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_full_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_error: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__: dict[str, Any] = {  # noqa: RUF012
        "version_id_col": version,
        "version_id_generator": lambda current: (current or 0) + 1,
    }


class ExternalEventModel(TimestampMixin, Base):
    __tablename__ = "external_event"
    __table_args__ = (
        UniqueConstraint("source_key", name="source_key"),
        CheckConstraint(enum_check("status", ExternalEventStatus), name="status"),
        CheckConstraint(
            "(is_all_day AND starts_on IS NOT NULL AND ends_on IS NOT NULL "
            "AND starts_at IS NULL AND ends_at IS NULL AND ends_on > starts_on) OR "
            "(NOT is_all_day AND starts_at IS NOT NULL AND starts_on IS NULL "
            "AND ends_on IS NULL AND (ends_at IS NULL OR ends_at > starts_at))",
            name="time_shape",
        ),
        Index(
            "ix_external_event_source_deleted_starts_at",
            "calendar_source_id",
            "deleted_at",
            "starts_at",
        ),
        Index(
            "ix_external_event_source_deleted_starts_on",
            "calendar_source_id",
            "deleted_at",
            "starts_on",
        ),
        Index(
            "ix_external_event_series_original",
            "calendar_source_id",
            "series_key",
            "original_start_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    calendar_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calendar_source.id", ondelete="RESTRICT"), nullable=False
    )
    source_key: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(1024), nullable=False)
    occurrence_id: Mapped[str | None] = mapped_column(String(1024))
    series_key: Mapped[str | None] = mapped_column(String(64))
    original_start_key: Mapped[str | None] = mapped_column(String(128))
    source_title: Mapped[str | None] = mapped_column(String(1024))
    source_description: Mapped[str | None] = mapped_column(Text)
    is_all_day: Mapped[bool] = mapped_column(Boolean, nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    starts_on: Mapped[date | None] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    source_timezone: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default=ExternalEventStatus.CONFIRMED.value
    )
    etag: Mapped[str | None] = mapped_column(String(512))
    provider_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EventOverrideModel(TimestampMixin, Base):
    __tablename__ = "event_override"
    __table_args__ = (
        CheckConstraint(
            enum_check("description_state", DescriptionState), name="description_state"
        ),
        CheckConstraint(
            enum_check("inclusion_decision", InclusionDecision), name="inclusion_decision"
        ),
        CheckConstraint(
            "(description_state = 'custom' AND public_description IS NOT NULL) OR "
            "(description_state <> 'custom' AND public_description IS NULL)",
            name="description_value",
        ),
        CheckConstraint("version >= 1", name="positive_version"),
    )

    external_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("external_event.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    public_title: Mapped[str | None] = mapped_column(String(1024))
    description_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=DescriptionState.INHERIT.value
    )
    public_description: Mapped[str | None] = mapped_column(Text)
    inclusion_decision: Mapped[str] = mapped_column(
        String(32), nullable=False, default=InclusionDecision.AUTO.value
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_by_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __mapper_args__: dict[str, Any] = {  # noqa: RUF012 - SQLAlchemy declarative setting
        "version_id_col": version,
        "version_id_generator": lambda current: (current or 0) + 1,
    }


class EventSeriesOverrideModel(TimestampMixin, Base):
    __tablename__ = "event_series_override"
    __table_args__ = (
        UniqueConstraint(
            "calendar_source_id", "series_key", "effective_from_key", name="series_effective"
        ),
        CheckConstraint(
            enum_check("description_state", DescriptionState), name="description_state"
        ),
        CheckConstraint(
            "(description_state = 'custom' AND public_description IS NOT NULL) OR "
            "(description_state <> 'custom' AND public_description IS NULL)",
            name="description_value",
        ),
        CheckConstraint(
            "(effective_all_day AND effective_from_date IS NOT NULL "
            "AND effective_from_at IS NULL) OR "
            "(NOT effective_all_day AND effective_from_at IS NOT NULL "
            "AND effective_from_date IS NULL)",
            name="effective_shape",
        ),
        CheckConstraint("version >= 1", name="positive_version"),
        Index(
            "ix_event_series_override_lookup",
            "calendar_source_id",
            "series_key",
            "effective_from_at",
            "effective_from_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    calendar_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calendar_source.id", ondelete="RESTRICT"), nullable=False
    )
    series_key: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_from_key: Mapped[str] = mapped_column(String(128), nullable=False)
    effective_all_day: Mapped[bool] = mapped_column(Boolean, nullable=False)
    effective_from_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_from_date: Mapped[date | None] = mapped_column(Date)
    public_title: Mapped[str | None] = mapped_column(String(1024))
    description_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=DescriptionState.INHERIT.value
    )
    public_description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_by_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __mapper_args__: dict[str, Any] = {  # noqa: RUF012 - SQLAlchemy declarative setting
        "version_id_col": version,
        "version_id_generator": lambda current: (current or 0) + 1,
    }


class ManualEventModel(TimestampMixin, Base):
    __tablename__ = "manual_event"
    __table_args__ = (
        CheckConstraint(
            "(is_all_day AND starts_on IS NOT NULL AND ends_on IS NOT NULL "
            "AND starts_at IS NULL AND ends_at IS NULL AND ends_on > starts_on) OR "
            "(NOT is_all_day AND starts_at IS NOT NULL AND starts_on IS NULL "
            "AND ends_on IS NULL AND (ends_at IS NULL OR ends_at > starts_at))",
            name="time_shape",
        ),
        Index("ix_manual_event_guild_active_starts_at", "guild_id", "active", "starts_at"),
        Index("ix_manual_event_guild_active_starts_on", "guild_id", "active", "starts_on"),
        CheckConstraint("version >= 1", name="positive_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guild_config.guild_id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_all_day: Mapped[bool] = mapped_column(Boolean, nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    starts_on: Mapped[date | None] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Bratislava")
    link_url: Mapped[str | None] = mapped_column(String(2048))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_by_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class InfoAnnouncementModel(TimestampMixin, Base):
    __tablename__ = "info_announcement"
    __table_args__ = (
        CheckConstraint("valid_until >= valid_from", name="validity_order"),
        Index(
            "ix_info_announcement_guild_active_validity",
            "guild_id",
            "active",
            "valid_from",
            "valid_until",
        ),
        CheckConstraint("version >= 1", name="positive_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guild_config.guild_id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    link_url: Mapped[str | None] = mapped_column(String(2048))
    image_url: Mapped[str | None] = mapped_column(String(2048))
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_by_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class PublicationRunModel(TimestampMixin, Base):
    __tablename__ = "publication_run"
    __table_args__ = (
        UniqueConstraint("guild_id", "slot_key", name="guild_slot"),
        UniqueConstraint("idempotency_key", name="idempotency_key"),
        CheckConstraint(enum_check("mode", PublicationMode), name="mode"),
        CheckConstraint(enum_check("state", PublicationState), name="state"),
        CheckConstraint("attempt >= 1", name="positive_attempt"),
        Index("ix_publication_run_state_scheduled", "state", "scheduled_for"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guild_config.guild_id", ondelete="RESTRICT"), nullable=False
    )
    slot_key: Mapped[str] = mapped_column(String(160), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    mode: Mapped[str] = mapped_column(String(24), nullable=False)
    initiated_by_user_id: Mapped[int | None] = mapped_column(BigInteger)
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=PublicationState.PREPARING.value
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_detail: Mapped[str | None] = mapped_column(Text)
    composer_version: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    intro_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    intro_prompt_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default="fallback-v1"
    )
    intro_used_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    outro_text: Mapped[str | None] = mapped_column(Text)
    warning_codes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    release_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_by_user_id: Mapped[int | None] = mapped_column(BigInteger)
    decision_reason: Mapped[str | None] = mapped_column(String(64))


class PublicationGuardNoticeModel(TimestampMixin, Base):
    __tablename__ = "publication_guard_notice"
    __table_args__ = (
        UniqueConstraint("publication_run_id", "recipient_user_id", name="run_recipient"),
        CheckConstraint("state IN ('pending', 'sent', 'failed', 'deleted')", name="state"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    publication_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("publication_run.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    nonce: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    discord_channel_id: Mapped[int | None] = mapped_column(BigInteger)
    discord_message_id: Mapped[int | None] = mapped_column(BigInteger)
    error_detail: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PublicationItemModel(Base):
    __tablename__ = "publication_item"
    __table_args__ = (
        UniqueConstraint("publication_run_id", "position", name="publication_item_run_position"),
        CheckConstraint(enum_check("item_type", PublicationItemType), name="item_type"),
        CheckConstraint("position >= 0", name="nonnegative_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    publication_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("publication_run.id", ondelete="CASCADE"), nullable=False
    )
    item_type: Mapped[str] = mapped_column(String(32), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    external_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("external_event.id", ondelete="SET NULL")
    )
    manual_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("manual_event.id", ondelete="SET NULL")
    )
    info_announcement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("info_announcement.id", ondelete="SET NULL")
    )
    final_title: Mapped[str | None] = mapped_column(String(1024))
    final_description: Mapped[str | None] = mapped_column(Text)
    display_time: Mapped[str | None] = mapped_column(String(200))
    day_emoji: Mapped[str | None] = mapped_column(String(200))
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    starts_on: Mapped[date | None] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    is_all_day: Mapped[bool | None] = mapped_column(Boolean)
    link_url: Mapped[str | None] = mapped_column(String(2048))
    image_url: Mapped[str | None] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ShadowPublicationModel(Base):
    __tablename__ = "shadow_publication"
    __table_args__ = (
        UniqueConstraint("guild_id", "slot_key", name="shadow_publication_guild_slot"),
        CheckConstraint("observation_count >= 1", name="positive_observation_count"),
        CheckConstraint("item_count >= 0", name="nonnegative_item_count"),
        CheckConstraint("message_count >= 0", name="nonnegative_message_count"),
        Index("ix_shadow_publication_guild_scheduled", "guild_id", "scheduled_for"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guild_config.guild_id", ondelete="CASCADE"), nullable=False
    )
    slot_key: Mapped[str] = mapped_column(String(160), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    draft_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    draft_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False)
    calendar_sync_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    calendar_sync_evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    warning_codes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)


class RuntimeHeartbeatModel(Base):
    __tablename__ = "runtime_heartbeat"
    __table_args__ = (
        UniqueConstraint(
            "guild_id", "process_name", "instance_id", name="runtime_process_instance"
        ),
        Index(
            "ix_runtime_heartbeat_guild_process_seen",
            "guild_id",
            "process_name",
            "last_seen_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guild_config.guild_id", ondelete="CASCADE"), nullable=False
    )
    process_name: Mapped[str] = mapped_column(String(32), nullable=False)
    instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class PublicationMessageModel(Base):
    __tablename__ = "publication_message"
    __table_args__ = (
        UniqueConstraint("publication_run_id", "position", name="publication_message_run_position"),
        UniqueConstraint("discord_channel_id", "discord_message_id", name="discord_message"),
        CheckConstraint(enum_check("state", PublicationMessageState), name="state"),
        CheckConstraint("position >= 0", name="nonnegative_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    publication_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("publication_run.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    discord_channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discord_message_id: Mapped[int | None] = mapped_column(BigInteger)
    state: Mapped[str] = mapped_column(
        String(24), nullable=False, default=PublicationMessageState.PENDING.value
    )
    error_detail: Mapped[str | None] = mapped_column(Text)
    part_key: Mapped[str] = mapped_column(String(64), nullable=False)
    nonce: Mapped[str] = mapped_column(String(25), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    embeds: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    allowed_mentions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    seen_target: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reaction_emoji: Mapped[str | None] = mapped_column(String(200))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reaction_error: Mapped[str | None] = mapped_column(Text)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PublicationIncidentModel(TimestampMixin, Base):
    __tablename__ = "publication_incident"
    __table_args__ = (
        CheckConstraint(enum_check("state", PublicationIncidentState), name="state"),
        Index("ix_publication_incident_guild_state", "guild_id", "state"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guild_config.guild_id", ondelete="RESTRICT"), nullable=False
    )
    publication_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("publication_run.id", ondelete="CASCADE"), nullable=False
    )
    publication_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("publication_message.id", ondelete="SET NULL")
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(
        String(24), nullable=False, default=PublicationIncidentState.OPEN.value
    )
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    resolution: Mapped[str | None] = mapped_column(Text)
    resolved_by_user_id: Mapped[int | None] = mapped_column(BigInteger)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ChannelArchiveRequestModel(TimestampMixin, Base):
    __tablename__ = "channel_archive_request"
    __table_args__ = (
        CheckConstraint(enum_check("state", ArchiveState), name="state"),
        Index("ix_channel_archive_request_state_expires", "state", "expires_at"),
        Index(
            "uq_channel_archive_request_pending_channel",
            "guild_id",
            "discord_channel_id",
            unique=True,
            postgresql_where=text("state IN ('pending', 'archiving')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guild_config.guild_id", ondelete="RESTRICT"), nullable=False
    )
    discord_channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    original_channel_name: Mapped[str] = mapped_column(String(100), nullable=False)
    archive_category_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    requested_by_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(
        String(24), nullable=False, default=ArchiveState.PENDING.value
    )
    decided_by_user_id: Mapped[int | None] = mapped_column(BigInteger)
    discord_approval_message_id: Mapped[int | None] = mapped_column(BigInteger)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    restore_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    archived_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    undo_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class UndoOperationModel(Base):
    __tablename__ = "undo_operation"
    __table_args__ = (
        CheckConstraint(enum_check("state", UndoState), name="state"),
        CheckConstraint(
            "operation_type IN ('role_change', 'channel_create', 'channel_archive')",
            name="operation_type",
        ),
        Index("ix_undo_operation_guild_state_created", "guild_id", "state", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guild_config.guild_id", ondelete="RESTRICT"), nullable=False
    )
    operation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    object_id: Mapped[str] = mapped_column(String(160), nullable=False)
    actor_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    before_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    after_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    state: Mapped[str] = mapped_column(
        String(24), nullable=False, default=UndoState.AVAILABLE.value
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    undone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    undone_by_user_id: Mapped[int | None] = mapped_column(BigInteger)
    last_block_reason: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReactionConfigModel(TimestampMixin, Base):
    __tablename__ = "reaction_config"
    __table_args__ = (CheckConstraint("version >= 1", name="positive_version"),)

    guild_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guild_config.guild_id", ondelete="CASCADE"),
        primary_key=True,
        autoincrement=False,
    )
    seen_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    seen_emoji_id: Mapped[int | None] = mapped_column(BigInteger)
    seen_emoji_unicode: Mapped[str | None] = mapped_column(String(32))
    auto_reaction_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    auto_reaction_emoji_id: Mapped[int | None] = mapped_column(BigInteger)
    auto_reaction_emoji_unicode: Mapped[str | None] = mapped_column(String(32))
    mention_reaction_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mention_reaction_emoji_id: Mapped[int | None] = mapped_column(BigInteger)
    mention_reaction_emoji_unicode: Mapped[str | None] = mapped_column(String(32))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__: dict[str, Any] = {  # noqa: RUF012
        "version_id_col": version,
        "version_id_generator": lambda current: (current or 0) + 1,
    }


class ReactionConfigChannelModel(Base):
    __tablename__ = "reaction_config_channel"

    guild_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("reaction_config.guild_id", ondelete="CASCADE"),
        primary_key=True,
        autoincrement=False,
    )
    discord_channel_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False
    )


class WebSessionModel(Base):
    __tablename__ = "web_session"
    __table_args__ = (
        UniqueConstraint("session_token_hash", name="session_token_hash"),
        Index("ix_web_session_expires_revoked", "expires_at", "revoked_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guild_config.guild_id", ondelete="CASCADE"), nullable=False
    )
    discord_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    session_token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    csrf_token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLogModel(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        CheckConstraint(enum_check("result", AuditResult), name="result"),
        Index("ix_audit_log_guild_created", "guild_id", "created_at"),
        Index("ix_audit_log_object", "object_type", "object_id"),
        Index("ix_audit_log_correlation", "correlation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guild_config.guild_id", ondelete="RESTRICT"), nullable=False
    )
    actor_user_id: Mapped[int | None] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    object_id: Mapped[str] = mapped_column(String(160), nullable=False)
    before_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    result: Mapped[str] = mapped_column(String(24), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class IntegrationTaskModel(TimestampMixin, Base):
    __tablename__ = "integration_task"
    __table_args__ = (
        UniqueConstraint("guild_id", "task_type", "deduplication_key", name="deduplication"),
        CheckConstraint(enum_check("state", IntegrationTaskState), name="state"),
        CheckConstraint("attempt >= 0", name="nonnegative_attempt"),
        Index("ix_integration_task_state_scheduled", "state", "scheduled_for"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guild_config.guild_id", ondelete="RESTRICT"), nullable=False
    )
    calendar_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calendar_source.id", ondelete="RESTRICT")
    )
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    deduplication_key: Mapped[str | None] = mapped_column(String(160))
    state: Mapped[str] = mapped_column(
        String(24), nullable=False, default=IntegrationTaskState.QUEUED.value
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    leased_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_detail: Mapped[str | None] = mapped_column(Text)
    result_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
