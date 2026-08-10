"""Persistence-neutral records crossing the application repository boundary."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

from domcek_bot.domain.enums import (
    ArchiveState,
    AuditResult,
    DescriptionState,
    ExternalEventStatus,
    InclusionDecision,
    IntegrationTaskState,
    PublicationItemType,
    PublicationMessageState,
    PublicationMode,
    PublicationState,
    SyncStatus,
)


@dataclass(frozen=True, slots=True)
class GuildConfigRecord:
    guild_id: int
    timezone: str = "Europe/Bratislava"
    publication_weekday: int = 0
    publication_time: time = time(20, 0)
    automatic_publication_enabled: bool = True
    publish_google_descriptions: bool = False
    generated_intro_enabled: bool = True
    everyone_mention_enabled: bool = True
    allow_stale_calendar_cache: bool = False
    alert_calendar_sync_enabled: bool = True
    alert_publication_enabled: bool = True
    alert_channel_operations_enabled: bool = True
    alert_role_operations_enabled: bool = True
    alert_publication_reminder_enabled: bool = False
    admin_role_id: int | None = None
    team_mod_role_id: int | None = None
    publisher_role_id: int | None = None
    announcement_channel_id: int | None = None
    command_channel_id: int | None = None
    moderator_channel_id: int | None = None
    projects_category_id: int | None = None
    archive_category_id: int | None = None
    closing_message: str | None = None
    version: int = 1


@dataclass(frozen=True, slots=True)
class CalendarSourceRecord:
    id: uuid.UUID
    guild_id: int
    provider: str
    external_calendar_id: str
    display_name: str
    priority: int = 100
    active: bool = True
    sync_status: SyncStatus = SyncStatus.NEVER
    sync_token: str | None = None
    sync_token_query_key: str | None = None
    last_sync_attempt_at: datetime | None = None
    last_sync_success_at: datetime | None = None
    last_full_sync_at: datetime | None = None
    last_sync_error: str | None = None
    version: int = 1


@dataclass(frozen=True, slots=True)
class ReactionConfigRecord:
    guild_id: int
    seen_enabled: bool = True
    seen_emoji_id: int | None = None
    seen_emoji_unicode: str | None = "✅"
    auto_reaction_enabled: bool = False
    auto_reaction_emoji_id: int | None = None
    auto_reaction_emoji_unicode: str | None = None
    mention_reaction_enabled: bool = False
    mention_reaction_emoji_id: int | None = None
    mention_reaction_emoji_unicode: str | None = None
    auto_reaction_channel_ids: tuple[int, ...] = ()
    version: int = 1


@dataclass(frozen=True, slots=True)
class ExternalEventRecord:
    id: uuid.UUID
    calendar_source_id: uuid.UUID
    source_key: str
    provider_event_id: str
    is_all_day: bool
    last_synced_at: datetime
    occurrence_id: str | None = None
    series_key: str | None = None
    original_start_key: str | None = None
    source_title: str | None = None
    source_description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    source_timezone: str | None = None
    status: ExternalEventStatus = ExternalEventStatus.CONFIRMED
    etag: str | None = None
    provider_updated_at: datetime | None = None
    deleted_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class EventOverrideRecord:
    external_event_id: uuid.UUID
    updated_by_user_id: int
    public_title: str | None = None
    description_state: DescriptionState = DescriptionState.INHERIT
    public_description: str | None = None
    inclusion_decision: InclusionDecision = InclusionDecision.AUTO
    version: int = 1


@dataclass(frozen=True, slots=True)
class EventSeriesOverrideRecord:
    id: uuid.UUID
    calendar_source_id: uuid.UUID
    series_key: str
    effective_from_key: str
    effective_all_day: bool
    effective_from_at: datetime | None
    effective_from_date: date | None
    updated_by_user_id: int
    public_title: str | None = None
    description_state: DescriptionState = DescriptionState.INHERIT
    public_description: str | None = None
    version: int = 1


@dataclass(frozen=True, slots=True)
class ManualEventRecord:
    id: uuid.UUID
    guild_id: int
    title: str
    is_all_day: bool
    created_by_user_id: int
    updated_by_user_id: int
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    timezone: str = "Europe/Bratislava"
    description: str | None = None
    link_url: str | None = None
    active: bool = True
    deleted_at: datetime | None = None
    version: int = 1


@dataclass(frozen=True, slots=True)
class InfoAnnouncementRecord:
    id: uuid.UUID
    guild_id: int
    title: str
    description: str
    valid_from: date
    valid_until: date
    created_by_user_id: int
    updated_by_user_id: int
    link_url: str | None = None
    image_url: str | None = None
    active: bool = True
    deleted_at: datetime | None = None
    version: int = 1


@dataclass(frozen=True, slots=True)
class PublicationRunRecord:
    id: uuid.UUID
    guild_id: int
    slot_key: str
    scheduled_for: datetime
    mode: PublicationMode
    state: PublicationState
    attempt: int
    idempotency_key: str
    composer_version: str
    intro_text: str
    intro_prompt_version: str
    intro_used_fallback: bool
    initiated_by_user_id: int | None = None
    outro_text: str | None = None
    warning_codes: tuple[str, ...] = ()
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_code: str | None = None
    error_detail: str | None = None


@dataclass(frozen=True, slots=True)
class PublicationItemRecord:
    id: uuid.UUID
    publication_run_id: uuid.UUID
    item_type: PublicationItemType
    position: int
    final_title: str | None
    final_description: str | None
    external_event_id: uuid.UUID | None = None
    manual_event_id: uuid.UUID | None = None
    info_announcement_id: uuid.UUID | None = None
    display_time: str | None = None
    day_emoji: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    is_all_day: bool | None = None
    link_url: str | None = None
    image_url: str | None = None


@dataclass(frozen=True, slots=True)
class PublicationMessageRecord:
    id: uuid.UUID
    publication_run_id: uuid.UUID
    position: int
    discord_channel_id: int
    part_key: str
    nonce: str
    content: str | None
    embeds: tuple[dict[str, Any], ...]
    allowed_mentions: tuple[str, ...]
    seen_target: bool
    state: PublicationMessageState = PublicationMessageState.PENDING
    discord_message_id: int | None = None
    attempt_count: int = 0
    error_detail: str | None = None
    reaction_error: str | None = None
    last_attempt_at: datetime | None = None
    sent_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ShadowPublicationRecord:
    id: uuid.UUID
    guild_id: int
    slot_key: str
    scheduled_for: datetime
    first_observed_at: datetime
    last_observed_at: datetime
    observation_count: int
    draft_sha256: str
    draft_json: dict[str, Any]
    item_count: int
    message_count: int
    calendar_sync_valid: bool
    calendar_sync_evidence: dict[str, Any]
    warning_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RuntimeHeartbeatRecord:
    id: uuid.UUID
    guild_id: int
    process_name: str
    instance_id: uuid.UUID
    state: str
    started_at: datetime
    last_seen_at: datetime
    details: dict[str, Any]


@dataclass(frozen=True, slots=True)
class IntegrationTaskRecord:
    id: uuid.UUID
    guild_id: int
    task_type: str
    deduplication_key: str
    state: IntegrationTaskState
    scheduled_for: datetime
    attempt: int = 0
    result_value: dict[str, Any] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_code: str | None = None
    error_detail: str | None = None


@dataclass(frozen=True, slots=True)
class ChannelArchiveRequestRecord:
    id: uuid.UUID
    guild_id: int
    discord_channel_id: int
    original_channel_name: str
    archive_category_id: int
    requested_by_user_id: int
    reason: str
    state: ArchiveState
    expires_at: datetime
    decided_by_user_id: int | None = None
    discord_approval_message_id: int | None = None
    decided_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class WebSessionRecord:
    id: uuid.UUID
    guild_id: int
    discord_user_id: int
    session_token_hash: str
    csrf_token_hash: str
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class AuditLogRecord:
    id: uuid.UUID
    guild_id: int
    action: str
    object_type: str
    object_id: str
    result: AuditResult
    correlation_id: str
    actor_user_id: int | None = None
    before_value: dict[str, Any] | None = None
    after_value: dict[str, Any] | None = None
    created_at: datetime | None = None
