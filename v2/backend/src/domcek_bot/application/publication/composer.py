"""Pure deterministic publication draft composer."""

from __future__ import annotations

import hashlib
import unicodedata
import uuid
from datetime import UTC, date, datetime, timedelta

from domcek_bot.application.publication.formatting import (
    all_day_day,
    event_day,
    format_all_day_range,
    format_timed_range,
    google_html_to_text,
    neutralize_discord_mentions,
    valid_public_url,
)
from domcek_bot.application.publication.models import (
    COMPOSER_VERSION,
    DiscordEmbedPlan,
    DiscordMessagePlan,
    DraftItemKind,
    DraftWarning,
    DraftWarningCode,
    EventSeriesOverrideInput,
    ExclusionReason,
    InfoAnnouncementInput,
    ManualEventInput,
    PublicationComposeSnapshot,
    PublicationDraft,
    PublicationDraftItem,
    ValueOrigin,
)
from domcek_bot.application.records import EventOverrideRecord, ExternalEventRecord
from domcek_bot.domain.calendar import parse_calendar_description
from domcek_bot.domain.enums import DescriptionState, ExternalEventStatus, InclusionDecision
from domcek_bot.domain.errors import DomainValidationError
from domcek_bot.domain.ids import GuildId
from domcek_bot.domain.time import (
    PublicationSchedule,
    PublicationSlot,
    PublicationWindow,
    info_is_valid_on,
    require_aware,
    timezone,
)

DISCORD_CONTENT_LIMIT = 2000
DISCORD_EMBED_LIMIT = 10
DISCORD_EMBED_TOTAL_LIMIT = 6000
DISCORD_EMBED_TITLE_LIMIT = 256
DISCORD_EMBED_DESCRIPTION_LIMIT = 4096
DISCORD_EMBED_AUTHOR_LIMIT = 256
DISCORD_NONCE_LIMIT = 25
MISSING_TITLE = "Udalosť bez názvu"
MAX_SLOT_SEARCH_WEEKS = 520

# Zachovaná mesačná paleta pôvodného Carla: jemný odtieň pre INFO,
# sýty odtieň pre kalendárové a manuálne udalosti.
MONTH_COLORS: dict[int, tuple[int, int]] = {
    1: (0xD6EAF8, 0x21618C),
    2: (0xCCD1D1, 0x2E4053),
    3: (0xEAD1DC, 0x8E44AD),
    4: (0xFCF3CF, 0xF4D03F),
    5: (0xD5F5E3, 0x27AE60),
    6: (0xFDEBD0, 0xE67E22),
    7: (0xFADBD8, 0xC0392B),
    8: (0xF9E79F, 0xD68910),
    9: (0xFCF3CF, 0xB7950B),
    10: (0xF6DDCC, 0xCA6F1E),
    11: (0xD5DBDB, 0x566573),
    12: (0xFBEEE6, 0xB03A2E),
}


class PublicationCompositionError(DomainValidationError):
    pass


def compose_publication(snapshot: PublicationComposeSnapshot) -> PublicationDraft:
    reference_time = require_aware(snapshot.reference_time, "reference_time")
    schedule = PublicationSchedule(
        weekday=snapshot.guild.publication_weekday,
        local_time=snapshot.guild.publication_time,
        timezone_name=snapshot.guild.timezone,
    )
    slot = next_unprocessed_slot(
        schedule,
        GuildId(snapshot.guild.guild_id),
        reference_time,
        snapshot.completed_slot_keys,
    )
    window = PublicationWindow.from_slot(slot)
    source_by_id = {
        source.id: source
        for source in snapshot.calendar_sources
        if source.active and source.guild_id == snapshot.guild.guild_id
    }
    override_by_event = {
        override.external_event_id: override for override in snapshot.event_overrides
    }
    series_by_identity: dict[tuple[uuid.UUID, str], list[EventSeriesOverrideInput]] = {}
    for override in snapshot.series_overrides:
        series_by_identity.setdefault(
            (override.calendar_source_id, override.series_key), []
        ).append(override)

    warnings: list[DraftWarning] = []
    editor_events: list[PublicationDraftItem] = []
    for event in snapshot.external_events:
        source = source_by_id.get(event.calendar_source_id)
        if source is None or not _external_is_candidate(event, window):
            continue
        instance = override_by_event.get(event.id)
        series_candidates = series_by_identity.get(
            (event.calendar_source_id, event.series_key or ""), []
        )
        series = _effective_series_override(event, series_candidates)
        exact_series = _exact_series_override(event, series_candidates)
        item, item_warnings = _external_item(
            event,
            source.priority,
            snapshot.guild.timezone,
            snapshot.guild.publish_google_descriptions,
            instance,
            series,
            exact_series,
        )
        editor_events.append(item)
        warnings.extend(item_warnings)

    event_items: list[PublicationDraftItem] = [item for item in editor_events if item.included]
    for manual in snapshot.manual_events:
        if (
            manual.guild_id == snapshot.guild.guild_id
            and manual.active
            and manual.deleted_at is None
            and _manual_is_candidate(manual, window)
        ):
            item, item_warnings = _manual_item(manual, snapshot.guild.timezone)
            event_items.append(item)
            warnings.extend(item_warnings)

    publication_day = slot.local_datetime.date()
    info_items: list[PublicationDraftItem] = []
    for info in snapshot.info_announcements:
        if (
            info.guild_id == snapshot.guild.guild_id
            and info.active
            and info.deleted_at is None
            and info_is_valid_on(info.valid_from, info.valid_until, publication_day)
        ):
            item, item_warnings = _info_item(info)
            info_items.append(item)
            warnings.extend(item_warnings)

    editor_events.sort(key=lambda item: _event_sort_key(item, snapshot.guild.timezone))
    event_items.sort(key=lambda item: _event_sort_key(item, snapshot.guild.timezone))
    info_items.sort(key=_info_sort_key)
    public_items = tuple([*info_items, *event_items])
    intro = _safe_required_text(snapshot.intro_text, "intro text")
    outro = _safe_optional_text(snapshot.guild.closing_message)
    messages = plan_discord_messages(
        guild_id=snapshot.guild.guild_id,
        slot_key=slot.key,
        intro_text=intro,
        outro_text=outro,
        # Product invariant: every publication addresses @everyone exactly once.
        # The persisted flag remains for backwards-compatible configuration reads,
        # but cannot weaken the canonical message plan.
        everyone_enabled=True,
        items=public_items,
        palette_month=slot.local_datetime.month,
        seen_reaction_emoji=snapshot.seen_reaction_emoji,
    )
    return PublicationDraft(
        composer_version=COMPOSER_VERSION,
        guild_id=snapshot.guild.guild_id,
        slot_key=slot.key,
        scheduled_for=slot.instant,
        scheduled_local=slot.local_datetime,
        timezone=snapshot.guild.timezone,
        window_starts_at=window.starts_at,
        window_ends_at=window.ends_at,
        intro_text=intro,
        outro_text=outro,
        editor_events=tuple(editor_events),
        public_items=public_items,
        warnings=tuple(sorted(warnings, key=lambda warning: (warning.code, warning.source_id))),
        messages=messages,
    )


def next_unprocessed_slot(
    schedule: PublicationSchedule,
    guild_id: GuildId,
    reference_time: datetime,
    completed_slot_keys: frozenset[str],
) -> PublicationSlot:
    cursor = require_aware(reference_time, "reference_time")
    for _ in range(MAX_SLOT_SEARCH_WEEKS):
        slot = schedule.next_slot(guild_id, cursor, inclusive=True)
        if slot.key not in completed_slot_keys:
            return slot
        cursor = slot.instant + timedelta(microseconds=1)
    raise PublicationCompositionError("no unprocessed publication slot in safety horizon")


def plan_discord_messages(
    *,
    guild_id: int,
    slot_key: str,
    intro_text: str,
    outro_text: str | None,
    everyone_enabled: bool,
    items: tuple[PublicationDraftItem, ...],
    palette_month: int = 1,
    seen_reaction_emoji: str | None = "✅",
) -> tuple[DiscordMessagePlan, ...]:
    first_content = f"@everyone\n{intro_text}" if everyone_enabled else intro_text
    if len(first_content) > DISCORD_CONTENT_LIMIT:
        raise PublicationCompositionError("publication intro exceeds Discord content limit")
    if outro_text is not None and len(outro_text) > DISCORD_CONTENT_LIMIT:
        raise PublicationCompositionError("publication outro exceeds Discord content limit")

    embeds = tuple(_embed_for_item(item, palette_month) for item in items)
    batches: list[list[DiscordEmbedPlan]] = [[]]
    batch_characters = 0
    for embed in embeds:
        _validate_embed(embed)
        current = batches[-1]
        if current and (
            len(current) >= DISCORD_EMBED_LIMIT
            or batch_characters + embed.character_count > DISCORD_EMBED_TOTAL_LIMIT
        ):
            batches.append([])
            current = batches[-1]
            batch_characters = 0
        current.append(embed)
        batch_characters += embed.character_count

    if not embeds:
        batches = [[]]
    message_contents: list[str | None] = [None for _ in batches]
    message_contents[0] = first_content
    if outro_text is not None:
        last = len(message_contents) - 1
        if last == 0:
            combined = f"{first_content}\n\n{outro_text}"
            if len(combined) <= DISCORD_CONTENT_LIMIT:
                message_contents[0] = combined
            else:
                batches.append([])
                message_contents.append(outro_text)
        else:
            message_contents[last] = outro_text

    messages: list[DiscordMessagePlan] = []
    for position, (content, batch) in enumerate(zip(message_contents, batches, strict=True)):
        digest = hashlib.sha256(
            f"{COMPOSER_VERSION}:{guild_id}:{slot_key}:{position}".encode()
        ).hexdigest()
        messages.append(
            DiscordMessagePlan(
                position=position,
                part_key=digest,
                nonce=digest[:DISCORD_NONCE_LIMIT],
                content=content,
                embeds=tuple(batch),
                allowed_mentions=("everyone",) if position == 0 and everyone_enabled else (),
                seen_target=position == len(batches) - 1,
                reaction_emoji=seen_reaction_emoji if position == len(batches) - 1 else None,
            )
        )
    return tuple(messages)


def _external_is_candidate(event: ExternalEventRecord, window: PublicationWindow) -> bool:
    if event.deleted_at is not None or event.status is ExternalEventStatus.CANCELLED:
        return False
    if event.is_all_day:
        if event.starts_on is None:
            return False
        return window.overlaps_all_day(event.starts_on, event.ends_on)
    if event.starts_at is None:
        return False
    return window.overlaps_timed(event.starts_at, event.ends_at)


def _manual_is_candidate(event: ManualEventInput, window: PublicationWindow) -> bool:
    if event.is_all_day:
        if event.starts_on is None:
            raise PublicationCompositionError("manual all-day event has no start date")
        return window.overlaps_all_day(event.starts_on, event.ends_on)
    if event.starts_at is None:
        raise PublicationCompositionError("manual timed event has no start time")
    return window.overlaps_timed(event.starts_at, event.ends_at)


def _effective_series_override(
    event: ExternalEventRecord, candidates: list[EventSeriesOverrideInput]
) -> EventSeriesOverrideInput | None:
    applicable: list[EventSeriesOverrideInput] = []
    for override in candidates:
        if event.is_all_day:
            occurrence = _event_occurrence_date(event)
            if override.effective_all_day and override.effective_from_date is not None:
                if override.effective_from_date <= occurrence:
                    applicable.append(override)
        else:
            occurrence_at = _event_occurrence_datetime(event)
            if not override.effective_all_day and override.effective_from_at is not None:
                if override.effective_from_at <= occurrence_at:
                    applicable.append(override)
    if not applicable:
        return None
    return max(applicable, key=_series_effective_sort_key)


def _exact_series_override(
    event: ExternalEventRecord, candidates: list[EventSeriesOverrideInput]
) -> EventSeriesOverrideInput | None:
    occurrence_key = _event_occurrence_key(event)
    return next(
        (override for override in candidates if override.effective_from_key == occurrence_key),
        None,
    )


def _event_occurrence_key(event: ExternalEventRecord) -> str:
    if event.original_start_key:
        return event.original_start_key
    if event.is_all_day:
        if event.starts_on is None:
            raise PublicationCompositionError("all-day event has no occurrence date")
        return event.starts_on.isoformat()
    if event.starts_at is None:
        raise PublicationCompositionError("timed event has no occurrence time")
    return event.starts_at.isoformat()


def _event_occurrence_date(event: ExternalEventRecord) -> date:
    if event.original_start_key:
        try:
            return date.fromisoformat(event.original_start_key)
        except ValueError as exc:
            raise PublicationCompositionError("invalid all-day original occurrence key") from exc
    if event.starts_on is None:
        raise PublicationCompositionError("all-day event has no occurrence date")
    return event.starts_on


def _event_occurrence_datetime(event: ExternalEventRecord) -> datetime:
    if event.original_start_key:
        try:
            value = datetime.fromisoformat(event.original_start_key.replace("Z", "+00:00"))
        except ValueError as exc:
            raise PublicationCompositionError("invalid timed original occurrence key") from exc
        return require_aware(value, "original occurrence")
    if event.starts_at is None:
        raise PublicationCompositionError("timed event has no occurrence time")
    return require_aware(event.starts_at, "event start")


def _series_effective_sort_key(override: EventSeriesOverrideInput) -> tuple[datetime, str]:
    if override.effective_all_day:
        if override.effective_from_date is None:
            raise PublicationCompositionError("all-day series override has no effective date")
        instant = datetime.combine(override.effective_from_date, datetime.min.time(), tzinfo=UTC)
    else:
        if override.effective_from_at is None:
            raise PublicationCompositionError("timed series override has no effective time")
        instant = override.effective_from_at.astimezone(UTC)
    return instant, str(override.id)


def _external_item(
    event: ExternalEventRecord,
    source_priority: int,
    timezone_name: str,
    publish_google_descriptions: bool,
    instance: EventOverrideRecord | None,
    series: EventSeriesOverrideInput | None,
    exact_series: EventSeriesOverrideInput | None,
) -> tuple[PublicationDraftItem, list[DraftWarning]]:
    parsed_description = parse_calendar_description(event.source_description)
    inclusion = instance.inclusion_decision if instance else InclusionDecision.AUTO
    exclusion: ExclusionReason | None = None
    included = True
    if inclusion is InclusionDecision.FORCE_EXCLUDE:
        included = False
        exclusion = ExclusionReason.FORCE_EXCLUDE
    elif inclusion is not InclusionDecision.FORCE_INCLUDE and parsed_description.stop_carlo:
        included = False
        exclusion = ExclusionReason.STOP_CARLO

    title, title_origin = _resolve_title(
        instance.public_title if instance else None,
        series.public_title if series else None,
        event.source_title,
    )
    description, description_origin = _resolve_description(
        instance.description_state if instance else DescriptionState.INHERIT,
        instance.public_description if instance else None,
        series.description_state if series else DescriptionState.INHERIT,
        series.public_description if series else None,
        parsed_description.public_candidate,
        publish_google_descriptions,
    )
    title = _safe_required_text(title, "event title")
    description = _safe_optional_text(description)
    display_time, day_name, day_emoji = _event_display(event, timezone_name)
    warnings: list[DraftWarning] = []
    if title_origin is ValueOrigin.FALLBACK:
        warnings.append(
            DraftWarning(
                DraftWarningCode.MISSING_TITLE, DraftItemKind.EXTERNAL_EVENT, str(event.id)
            )
        )
    return (
        PublicationDraftItem(
            kind=DraftItemKind.EXTERNAL_EVENT,
            source_id=str(event.id),
            title=title,
            description=description,
            title_origin=title_origin,
            description_origin=description_origin,
            included=included,
            exclusion_reason=exclusion,
            display_time=display_time,
            day_name=day_name,
            day_emoji=day_emoji,
            is_all_day=event.is_all_day,
            starts_at=event.starts_at,
            ends_at=event.ends_at,
            starts_on=event.starts_on,
            ends_on=event.ends_on,
            source_priority=source_priority,
            source_title=_safe_optional_text(event.source_title),
            source_description=_safe_optional_text(
                google_html_to_text(parsed_description.public_candidate)
                if parsed_description.public_candidate
                else None
            ),
            is_recurring=event.series_key is not None,
            instance_override_version=instance.version if instance else 0,
            instance_public_title=instance.public_title if instance else None,
            instance_description_state=(
                instance.description_state if instance else DescriptionState.INHERIT
            ),
            instance_public_description=(instance.public_description if instance else None),
            inclusion_decision=inclusion,
            series_override_version=exact_series.version if exact_series else 0,
            series_public_title=series.public_title if series else None,
            series_description_state=(
                series.description_state if series else DescriptionState.INHERIT
            ),
            series_public_description=series.public_description if series else None,
        ),
        warnings,
    )


def _manual_item(
    event: ManualEventInput, timezone_name: str
) -> tuple[PublicationDraftItem, list[DraftWarning]]:
    title = _safe_required_text(event.title, "manual event title")
    description = _safe_optional_text(event.description)
    link, _, warnings = _validated_urls(
        event.link_url, None, DraftItemKind.MANUAL_EVENT, str(event.id)
    )
    if event.is_all_day:
        if event.starts_on is None:
            raise PublicationCompositionError("manual all-day event has no start date")
        _, day_name, day_emoji = all_day_day(event.starts_on)
        display_time = format_all_day_range(event.starts_on, event.ends_on)
    else:
        if event.starts_at is None:
            raise PublicationCompositionError("manual timed event has no start time")
        _, day_name, day_emoji = event_day(event.starts_at, timezone_name)
        display_time = format_timed_range(event.starts_at, event.ends_at, timezone_name)
    return (
        PublicationDraftItem(
            kind=DraftItemKind.MANUAL_EVENT,
            source_id=str(event.id),
            title=title,
            description=description,
            title_origin=ValueOrigin.MANUAL,
            description_origin=(
                ValueOrigin.MANUAL if description is not None else ValueOrigin.NONE
            ),
            included=True,
            exclusion_reason=None,
            display_time=display_time,
            day_name=day_name,
            day_emoji=day_emoji,
            is_all_day=event.is_all_day,
            starts_at=event.starts_at,
            ends_at=event.ends_at,
            starts_on=event.starts_on,
            ends_on=event.ends_on,
            link_url=link,
        ),
        warnings,
    )


def _info_item(info: InfoAnnouncementInput) -> tuple[PublicationDraftItem, list[DraftWarning]]:
    title = _safe_required_text(info.title, "INFO title")
    description = _safe_required_text(info.description, "INFO description")
    link, image, warnings = _validated_urls(
        info.link_url,
        info.image_url,
        DraftItemKind.INFO,
        str(info.id),
    )
    return (
        PublicationDraftItem(
            kind=DraftItemKind.INFO,
            source_id=str(info.id),
            title=title,
            description=description,
            title_origin=ValueOrigin.INFO,
            description_origin=ValueOrigin.INFO,
            included=True,
            exclusion_reason=None,
            display_time=None,
            day_name=None,
            day_emoji=None,
            is_all_day=None,
            link_url=link,
            image_url=image,
        ),
        warnings,
    )


def _resolve_title(
    instance_title: str | None, series_title: str | None, google_title: str | None
) -> tuple[str, ValueOrigin]:
    if instance_title is not None and instance_title.strip():
        return instance_title, ValueOrigin.INSTANCE
    if series_title is not None and series_title.strip():
        return series_title, ValueOrigin.SERIES
    if google_title is not None and google_title.strip():
        return google_title, ValueOrigin.GOOGLE
    return MISSING_TITLE, ValueOrigin.FALLBACK


def _resolve_description(
    instance_state: DescriptionState,
    instance_description: str | None,
    series_state: DescriptionState,
    series_description: str | None,
    google_description: str | None,
    publish_google_descriptions: bool,
) -> tuple[str | None, ValueOrigin]:
    if instance_state is DescriptionState.CUSTOM:
        if instance_description is None:
            raise PublicationCompositionError("custom instance description has no value")
        return instance_description, ValueOrigin.INSTANCE
    if instance_state is DescriptionState.INTENTIONALLY_EMPTY:
        return None, ValueOrigin.INSTANCE
    if series_state is DescriptionState.CUSTOM:
        if series_description is None:
            raise PublicationCompositionError("custom series description has no value")
        return series_description, ValueOrigin.SERIES
    if series_state is DescriptionState.INTENTIONALLY_EMPTY:
        return None, ValueOrigin.SERIES
    if publish_google_descriptions:
        text = google_html_to_text(google_description)
        if text is not None:
            return text, ValueOrigin.GOOGLE
    return None, ValueOrigin.NONE


def _event_display(event: ExternalEventRecord, timezone_name: str) -> tuple[str, str, str]:
    if event.is_all_day:
        if event.starts_on is None:
            raise PublicationCompositionError("all-day event has no start date")
        _, name, icon = all_day_day(event.starts_on)
        return format_all_day_range(event.starts_on, event.ends_on), name, icon
    if event.starts_at is None:
        raise PublicationCompositionError("timed event has no start time")
    _, name, icon = event_day(event.starts_at, timezone_name)
    return format_timed_range(event.starts_at, event.ends_at, timezone_name), name, icon


def _validated_urls(
    link_url: str | None,
    image_url: str | None,
    kind: DraftItemKind,
    source_id: str,
) -> tuple[str | None, str | None, list[DraftWarning]]:
    warnings: list[DraftWarning] = []
    link = link_url
    image = image_url
    if not valid_public_url(link):
        link = None
        warnings.append(DraftWarning(DraftWarningCode.INVALID_LINK_URL, kind, source_id))
    if not valid_public_url(image):
        image = None
        warnings.append(DraftWarning(DraftWarningCode.INVALID_IMAGE_URL, kind, source_id))
    return link, image, warnings


def _event_sort_key(item: PublicationDraftItem, timezone_name: str) -> tuple[object, ...]:
    if item.is_all_day:
        if item.starts_on is None:
            raise PublicationCompositionError("all-day draft item has no start date")
        local_day = item.starts_on
        start_key = datetime.min.time()
        all_day_rank = 0
    else:
        if item.starts_at is None:
            raise PublicationCompositionError("timed draft item has no start")
        local = item.starts_at.astimezone(timezone(timezone_name))
        local_day = local.date()
        start_key = local.timetz().replace(tzinfo=None)
        all_day_rank = 1
    return (
        local_day,
        all_day_rank,
        start_key,
        item.source_priority,
        _normalized_title(item.title),
        item.source_id,
    )


def _info_sort_key(item: PublicationDraftItem) -> tuple[str, str]:
    return _normalized_title(item.title), item.source_id


def _normalized_title(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def _safe_required_text(value: str, field: str) -> str:
    normalized = neutralize_discord_mentions(value.strip())
    if normalized is None or not normalized:
        raise PublicationCompositionError(f"{field} cannot be empty")
    return normalized


def _safe_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = neutralize_discord_mentions(value.strip())
    return normalized or None


def _embed_for_item(item: PublicationDraftItem, palette_month: int) -> DiscordEmbedPlan:
    info_color, event_color = MONTH_COLORS.get(palette_month, (0xDDDDDD, 0x999999))
    return DiscordEmbedPlan(
        item_kind=item.kind,
        source_id=item.source_id,
        color=info_color if item.kind is DraftItemKind.INFO else event_color,
        title=item.title,
        description=item.description,
        author_name=item.display_time,
        author_icon_url=item.day_emoji,
        link_url=item.link_url,
        thumbnail_url=item.image_url,
    )


def _validate_embed(embed: DiscordEmbedPlan) -> None:
    if len(embed.title) > DISCORD_EMBED_TITLE_LIMIT:
        raise PublicationCompositionError(f"embed title exceeds limit: {embed.source_id}")
    if len(embed.description or "") > DISCORD_EMBED_DESCRIPTION_LIMIT:
        raise PublicationCompositionError(f"embed description exceeds limit: {embed.source_id}")
    if len(embed.author_name or "") > DISCORD_EMBED_AUTHOR_LIMIT:
        raise PublicationCompositionError(f"embed author exceeds limit: {embed.source_id}")
    if embed.character_count > DISCORD_EMBED_TOTAL_LIMIT:
        raise PublicationCompositionError(f"embed exceeds total limit: {embed.source_id}")
