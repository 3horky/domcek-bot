from __future__ import annotations

import pytest

from domcek_bot.domain.errors import DomainValidationError
from domcek_bot.domain.ids import ChannelId, EventSourceKey, GuildId, RecurringSeriesKey, RoleId


def test_discord_ids_accept_positive_signed_bigints() -> None:
    assert GuildId("1535774834955391047") == 1535774834955391047
    assert RoleId(1) == 1
    assert ChannelId(2**63 - 1) == 2**63 - 1


@pytest.mark.parametrize("value", [0, -1, 2**63, True, "not-a-number"])
def test_discord_ids_reject_invalid_values(value: object) -> None:
    with pytest.raises(DomainValidationError):
        GuildId(value)  # type: ignore[arg-type]


def test_event_source_key_is_stable_and_occurrence_specific() -> None:
    first = EventSourceKey("google", "calendar", "event", "2026-08-10T18:00:00Z")
    same = EventSourceKey("google", "calendar", "event", "2026-08-10T18:00:00Z")
    another_occurrence = EventSourceKey("google", "calendar", "event", "2026-08-17T18:00:00Z")
    assert first.value == same.value
    assert first.value != another_occurrence.value
    assert len(first.value) == 64


def test_series_key_is_stable_and_provider_scoped() -> None:
    google = RecurringSeriesKey("google", "calendar", "series")
    another_provider = RecurringSeriesKey("other", "calendar", "series")
    assert google.value == RecurringSeriesKey("google", "calendar", "series").value
    assert google.value != another_provider.value
