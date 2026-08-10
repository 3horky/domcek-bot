from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

import pytest

from domcek_bot.domain.errors import DomainValidationError
from domcek_bot.domain.ids import GuildId
from domcek_bot.domain.time import PublicationSchedule, PublicationWindow, info_is_valid_on


def test_default_schedule_finds_monday_at_20_in_bratislava() -> None:
    schedule = PublicationSchedule()
    slot = schedule.next_slot(GuildId(1), datetime(2026, 8, 9, 10, tzinfo=UTC))
    assert slot.local_datetime.isoformat() == "2026-08-10T20:00:00+02:00"
    assert slot.instant == datetime(2026, 8, 10, 18, tzinfo=UTC)
    assert slot.key == "1:2026-08-10T20:00:Europe/Bratislava"


def test_exact_slot_is_next_week_unless_inclusive() -> None:
    schedule = PublicationSchedule()
    exact = datetime(2026, 8, 10, 18, tzinfo=UTC)
    assert schedule.next_slot(GuildId(1), exact).local_datetime.date() == date(2026, 8, 17)
    assert schedule.next_slot(GuildId(1), exact, inclusive=True).local_datetime.date() == date(
        2026, 8, 10
    )


def test_nonexistent_spring_time_moves_to_first_valid_minute() -> None:
    schedule = PublicationSchedule(weekday=6, local_time=time(2, 30))
    slot = schedule.next_slot(GuildId(1), datetime(2026, 3, 28, 12, tzinfo=UTC))
    assert slot.local_datetime.isoformat() == "2026-03-29T03:00:00+02:00"


def test_ambiguous_autumn_time_uses_first_occurrence() -> None:
    schedule = PublicationSchedule(weekday=6, local_time=time(2, 30))
    slot = schedule.next_slot(GuildId(1), datetime(2026, 10, 24, 12, tzinfo=UTC))
    assert slot.local_datetime.isoformat() == "2026-10-25T02:30:00+02:00"
    assert slot.local_datetime.fold == 0


def test_window_keeps_fourteen_local_days_across_dst() -> None:
    schedule = PublicationSchedule()
    slot = schedule.next_slot(GuildId(1), datetime(2026, 3, 22, 12, tzinfo=UTC))
    window = PublicationWindow.from_slot(slot)
    assert window.starts_at.isoformat() == "2026-03-23T20:00:00+01:00"
    assert window.ends_at.isoformat() == "2026-04-06T20:00:00+02:00"
    assert window.ends_at.astimezone(UTC) - window.starts_at.astimezone(UTC) == timedelta(hours=335)


def test_window_uses_half_open_overlap_rules() -> None:
    slot = PublicationSchedule().next_slot(GuildId(1), datetime(2026, 8, 9, 12, tzinfo=UTC))
    window = PublicationWindow.from_slot(slot)
    assert window.overlaps_timed(
        window.starts_at - timedelta(hours=1), window.starts_at + timedelta(hours=1)
    )
    assert not window.overlaps_timed(window.starts_at - timedelta(hours=1), window.starts_at)
    assert not window.overlaps_timed(window.ends_at, window.ends_at + timedelta(hours=1))
    assert window.overlaps_all_day(date(2026, 8, 9), date(2026, 8, 11))
    assert not window.overlaps_all_day(date(2026, 8, 24), date(2026, 8, 25))


def test_invalid_ranges_are_rejected() -> None:
    slot = PublicationSchedule().next_slot(GuildId(1), datetime(2026, 8, 9, 12, tzinfo=UTC))
    window = PublicationWindow.from_slot(slot)
    with pytest.raises(DomainValidationError):
        window.overlaps_timed(window.starts_at, window.starts_at)
    with pytest.raises(DomainValidationError):
        window.overlaps_all_day(date(2026, 8, 12), date(2026, 8, 12))


def test_info_validity_includes_last_local_day() -> None:
    assert info_is_valid_on(date(2026, 8, 1), date(2026, 8, 8), date(2026, 8, 8))
    assert not info_is_valid_on(date(2026, 8, 1), date(2026, 8, 8), date(2026, 8, 9))
