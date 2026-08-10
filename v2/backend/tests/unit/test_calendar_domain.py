from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest

from domcek_bot.application.calendar.contracts import CalendarEventTime, ProviderCalendarEvent
from domcek_bot.application.calendar.normalization import normalize_provider_event
from domcek_bot.application.records import CalendarSourceRecord
from domcek_bot.domain.calendar import (
    CalendarFreshnessState,
    assess_calendar_freshness,
    parse_calendar_description,
)
from domcek_bot.domain.enums import ExternalEventStatus
from domcek_bot.domain.errors import DomainValidationError

NOW = datetime(2026, 8, 9, 18, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("description", "stop_carlo", "public_candidate"),
    [
        (None, False, None),
        ("Bežný popis", False, "Bežný popis"),
        ("STOP CARLO", True, None),
        ("Úvod\n stop   carlo \nZáver", True, "Úvod\nZáver"),
        (
            "Organizačná poznámka. STOP CARLO",
            True,
            "Organizačná poznámka.",
        ),
        (
            "<p>Organizačná poznámka. STOP CARLO</p>",
            True,
            "<p>Organizačná poznámka.</p>",
        ),
        ("<p>STOP CARLO</p>", True, None),
        ("Toto nie je stop carlo príkaz", False, "Toto nie je stop carlo príkaz"),
        ("stop carlo!", False, "stop carlo!"),
    ],
)
def test_stop_carlo_is_a_standalone_case_insensitive_control_sentence(
    description: str | None,
    stop_carlo: bool,
    public_candidate: str | None,
) -> None:
    parsed = parse_calendar_description(description)

    assert parsed.raw == description
    assert parsed.stop_carlo is stop_carlo
    assert parsed.public_candidate == public_candidate


def test_calendar_freshness_has_warning_and_blocking_thresholds() -> None:
    warning_after = timedelta(hours=2)
    unsafe_after = timedelta(hours=6)

    assert (
        assess_calendar_freshness(
            NOW - timedelta(hours=1),
            now=NOW,
            warning_after=warning_after,
            unsafe_after=unsafe_after,
        ).state
        is CalendarFreshnessState.FRESH
    )
    assert (
        assess_calendar_freshness(
            NOW - timedelta(hours=3),
            now=NOW,
            warning_after=warning_after,
            unsafe_after=unsafe_after,
        ).state
        is CalendarFreshnessState.STALE_WARNING
    )
    unsafe = assess_calendar_freshness(
        NOW - timedelta(hours=7),
        now=NOW,
        warning_after=warning_after,
        unsafe_after=unsafe_after,
    )
    assert unsafe.state is CalendarFreshnessState.UNSAFE
    assert not unsafe.publication_safe
    assert (
        assess_calendar_freshness(
            None,
            now=NOW,
            warning_after=warning_after,
            unsafe_after=unsafe_after,
        ).state
        is CalendarFreshnessState.UNSAFE
    )


def test_calendar_freshness_rejects_invalid_threshold_order() -> None:
    with pytest.raises(DomainValidationError):
        assess_calendar_freshness(
            NOW,
            now=NOW,
            warning_after=timedelta(hours=6),
            unsafe_after=timedelta(hours=2),
        )


def test_normalize_timed_recurring_event_preserves_moved_occurrence_identity() -> None:
    source = CalendarSourceRecord(
        id=uuid.uuid4(),
        guild_id=1,
        provider="google",
        external_calendar_id="calendar@example.test",
        display_name="Test",
    )
    original_start = datetime(2026, 8, 10, 16, 0, tzinfo=UTC)
    moved_start = datetime(2026, 8, 10, 18, 0, tzinfo=UTC)
    event = ProviderCalendarEvent(
        provider_event_id="instance-id",
        status=ExternalEventStatus.CONFIRMED,
        title="Presunutý výskyt",
        description="Raw Google popis",
        start=CalendarEventTime(
            date_time_value=moved_start,
            timezone="Europe/Prague",
        ),
        end=CalendarEventTime(
            date_time_value=moved_start + timedelta(hours=1),
            timezone="Europe/Prague",
        ),
        recurring_event_id="series-id",
        original_start=CalendarEventTime(
            date_time_value=original_start,
            timezone="Europe/Prague",
        ),
        updated_at=NOW,
        etag="etag-1",
    )

    normalized = normalize_provider_event(event, source, synced_at=NOW)
    normalized_again = normalize_provider_event(event, source, synced_at=NOW)

    assert normalized.starts_at == moved_start
    assert normalized.original_start_key == "2026-08-10T16:00:00Z"
    assert normalized.occurrence_id == normalized.original_start_key
    assert normalized.series_key is not None
    assert normalized.source_key == normalized_again.source_key
    assert normalized.series_key == normalized_again.series_key
    assert normalized.source_description == "Raw Google popis"
    assert normalized.source_timezone == "Europe/Prague"


def test_normalize_all_day_event_uses_exclusive_date_end() -> None:
    source = CalendarSourceRecord(
        id=uuid.uuid4(),
        guild_id=1,
        provider="google",
        external_calendar_id="calendar@example.test",
        display_name="Test",
    )
    event = ProviderCalendarEvent(
        provider_event_id="all-day-id",
        status=ExternalEventStatus.CONFIRMED,
        start=CalendarEventTime(date_value=date(2026, 8, 10)),
        end=CalendarEventTime(date_value=date(2026, 8, 12)),
    )

    normalized = normalize_provider_event(event, source, synced_at=NOW)

    assert normalized.is_all_day
    assert normalized.starts_on == date(2026, 8, 10)
    assert normalized.ends_on == date(2026, 8, 12)
    assert normalized.starts_at is None


def test_cancelled_event_is_not_normalized_as_new_database_row() -> None:
    source = CalendarSourceRecord(
        id=uuid.uuid4(),
        guild_id=1,
        provider="google",
        external_calendar_id="calendar@example.test",
        display_name="Test",
    )
    event = ProviderCalendarEvent(
        provider_event_id="cancelled-id",
        status=ExternalEventStatus.CANCELLED,
        start=None,
        end=None,
    )

    with pytest.raises(DomainValidationError, match="cancelled"):
        normalize_provider_event(event, source, synced_at=NOW)
