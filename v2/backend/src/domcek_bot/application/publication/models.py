"""Serializable, persistence-neutral contracts for publication composition."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Any

from domcek_bot.application.records import (
    CalendarSourceRecord,
    EventOverrideRecord,
    ExternalEventRecord,
    GuildConfigRecord,
)
from domcek_bot.domain.enums import DescriptionState, InclusionDecision

COMPOSER_VERSION = "e4-v2"


class DraftItemKind(StrEnum):
    INFO = "info"
    EXTERNAL_EVENT = "external_event"
    MANUAL_EVENT = "manual_event"


class ValueOrigin(StrEnum):
    INSTANCE = "instance"
    SERIES = "series"
    GOOGLE = "google"
    MANUAL = "manual"
    INFO = "info"
    FALLBACK = "fallback"
    NONE = "none"


class ExclusionReason(StrEnum):
    FORCE_EXCLUDE = "force_exclude"
    STOP_CARLO = "stop_carlo"


class DraftWarningCode(StrEnum):
    MISSING_TITLE = "missing_title"
    INVALID_LINK_URL = "invalid_link_url"
    INVALID_IMAGE_URL = "invalid_image_url"


@dataclass(frozen=True, slots=True)
class EventSeriesOverrideInput:
    id: uuid.UUID
    calendar_source_id: uuid.UUID
    series_key: str
    effective_from_key: str
    effective_all_day: bool
    effective_from_at: datetime | None
    effective_from_date: date | None
    public_title: str | None
    description_state: DescriptionState
    public_description: str | None
    version: int = 1


@dataclass(frozen=True, slots=True)
class ManualEventInput:
    id: uuid.UUID
    guild_id: int
    title: str
    is_all_day: bool
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    timezone: str = "Europe/Bratislava"
    description: str | None = None
    link_url: str | None = None
    active: bool = True
    deleted_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class InfoAnnouncementInput:
    id: uuid.UUID
    guild_id: int
    title: str
    description: str
    valid_from: date
    valid_until: date
    link_url: str | None = None
    image_url: str | None = None
    active: bool = True
    deleted_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PublicationComposeSnapshot:
    guild: GuildConfigRecord
    reference_time: datetime
    calendar_sources: tuple[CalendarSourceRecord, ...] = ()
    external_events: tuple[ExternalEventRecord, ...] = ()
    event_overrides: tuple[EventOverrideRecord, ...] = ()
    series_overrides: tuple[EventSeriesOverrideInput, ...] = ()
    manual_events: tuple[ManualEventInput, ...] = ()
    info_announcements: tuple[InfoAnnouncementInput, ...] = ()
    completed_slot_keys: frozenset[str] = frozenset()
    intro_text: str = "Ahojte, prinášame prehľad udalostí na najbližšie dva týždne."


@dataclass(frozen=True, slots=True)
class DraftWarning:
    code: DraftWarningCode
    item_kind: DraftItemKind
    source_id: str


@dataclass(frozen=True, slots=True)
class PublicationDraftItem:
    kind: DraftItemKind
    source_id: str
    title: str
    description: str | None
    title_origin: ValueOrigin
    description_origin: ValueOrigin
    included: bool
    exclusion_reason: ExclusionReason | None
    display_time: str | None
    day_name: str | None
    day_emoji: str | None
    is_all_day: bool | None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    link_url: str | None = None
    image_url: str | None = None
    source_priority: int = 0
    source_title: str | None = None
    source_description: str | None = None
    is_recurring: bool = False
    instance_override_version: int = 0
    instance_public_title: str | None = None
    instance_description_state: DescriptionState = DescriptionState.INHERIT
    instance_public_description: str | None = None
    inclusion_decision: InclusionDecision = InclusionDecision.AUTO
    series_override_version: int = 0
    series_public_title: str | None = None
    series_description_state: DescriptionState = DescriptionState.INHERIT
    series_public_description: str | None = None


@dataclass(frozen=True, slots=True)
class DiscordEmbedPlan:
    item_kind: DraftItemKind
    source_id: str
    color: int
    title: str
    description: str | None
    author_name: str | None
    author_icon_url: str | None
    link_url: str | None
    thumbnail_url: str | None

    @property
    def character_count(self) -> int:
        return len(self.title) + len(self.description or "") + len(self.author_name or "")


@dataclass(frozen=True, slots=True)
class DiscordMessagePlan:
    position: int
    part_key: str
    nonce: str
    content: str | None
    embeds: tuple[DiscordEmbedPlan, ...]
    allowed_mentions: tuple[str, ...]
    seen_target: bool

    @property
    def embed_character_count(self) -> int:
        return sum(embed.character_count for embed in self.embeds)


@dataclass(frozen=True, slots=True)
class PublicationDraft:
    composer_version: str
    guild_id: int
    slot_key: str
    scheduled_for: datetime
    scheduled_local: datetime
    timezone: str
    window_starts_at: datetime
    window_ends_at: datetime
    intro_text: str
    outro_text: str | None
    editor_events: tuple[PublicationDraftItem, ...]
    public_items: tuple[PublicationDraftItem, ...]
    warnings: tuple[DraftWarning, ...]
    messages: tuple[DiscordMessagePlan, ...]

    def canonical_json(self) -> str:
        return json.dumps(
            _json_value(asdict(self)),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )


def _json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (StrEnum, uuid.UUID)):
        return str(value)
    return value
