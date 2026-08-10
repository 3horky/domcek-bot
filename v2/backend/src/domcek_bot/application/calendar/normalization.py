"""Map provider-neutral calendar events into persistence-neutral E2 records."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from domcek_bot.application.calendar.contracts import ProviderCalendarEvent
from domcek_bot.application.records import CalendarSourceRecord, ExternalEventRecord
from domcek_bot.domain.enums import ExternalEventStatus
from domcek_bot.domain.errors import DomainValidationError
from domcek_bot.domain.ids import EventSourceKey, RecurringSeriesKey


def canonical_occurrence_key(event: ProviderCalendarEvent) -> str | None:
    original = event.original_start
    if original is None:
        return None
    if original.date_value is not None:
        return original.date_value.isoformat()
    date_time_value = original.date_time_value
    if date_time_value is None:
        raise DomainValidationError("original start has no usable value")
    return date_time_value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def normalize_provider_event(
    event: ProviderCalendarEvent,
    source: CalendarSourceRecord,
    *,
    synced_at: datetime,
    event_id: uuid.UUID | None = None,
) -> ExternalEventRecord:
    """Normalize a non-cancelled provider event into the strict E2 event shape."""

    if synced_at.utcoffset() is None:
        raise DomainValidationError("synced_at must be timezone-aware")
    if event.status is ExternalEventStatus.CANCELLED:
        raise DomainValidationError("cancelled events require update of an existing record")
    if event.start is None or event.end is None:
        raise DomainValidationError("active calendar event requires start and end")
    if event.start.is_all_day != event.end.is_all_day:
        raise DomainValidationError("calendar event start and end must use the same shape")

    provider_event_id = event.provider_event_id.strip()
    if not provider_event_id:
        raise DomainValidationError("provider event id cannot be empty")

    occurrence_key = canonical_occurrence_key(event)
    source_key = EventSourceKey(
        provider=source.provider,
        calendar_id=source.external_calendar_id,
        event_id=provider_event_id,
    ).value
    series_key = None
    if event.recurring_event_id:
        series_key = RecurringSeriesKey(
            provider=source.provider,
            calendar_id=source.external_calendar_id,
            series_id=event.recurring_event_id,
        ).value

    internal_id = event_id or uuid.uuid4()
    source_timezone = event.source_timezone or event.start.timezone
    if event.start.is_all_day:
        starts_on = event.start.date_value
        ends_on = event.end.date_value
        if starts_on is None or ends_on is None:
            raise DomainValidationError("all-day event has no date values")
        if ends_on <= starts_on:
            raise DomainValidationError("all-day event end must be after start")
        return ExternalEventRecord(
            id=internal_id,
            calendar_source_id=source.id,
            source_key=source_key,
            provider_event_id=provider_event_id,
            is_all_day=True,
            last_synced_at=synced_at,
            occurrence_id=occurrence_key,
            series_key=series_key,
            original_start_key=occurrence_key,
            source_title=event.title,
            source_description=event.description,
            starts_on=starts_on,
            ends_on=ends_on,
            source_timezone=source_timezone,
            status=event.status,
            etag=event.etag,
            provider_updated_at=event.updated_at,
        )

    starts_at = event.start.date_time_value
    ends_at = event.end.date_time_value
    if starts_at is None or ends_at is None:
        raise DomainValidationError("timed event has no date-time values")
    if ends_at <= starts_at:
        raise DomainValidationError("timed event end must be after start")
    return ExternalEventRecord(
        id=internal_id,
        calendar_source_id=source.id,
        source_key=source_key,
        provider_event_id=provider_event_id,
        is_all_day=False,
        last_synced_at=synced_at,
        occurrence_id=occurrence_key,
        series_key=series_key,
        original_start_key=occurrence_key,
        source_title=event.title,
        source_description=event.description,
        starts_at=starts_at,
        ends_at=ends_at,
        source_timezone=source_timezone,
        status=event.status,
        etag=event.etag,
        provider_updated_at=event.updated_at,
    )
