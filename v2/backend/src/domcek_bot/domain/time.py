"""Timezone-aware publication scheduling and half-open window rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from domcek_bot.domain.errors import DomainValidationError
from domcek_bot.domain.ids import GuildId

DEFAULT_TIMEZONE = "Europe/Bratislava"


def timezone(value: str) -> ZoneInfo:
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise DomainValidationError(f"Unknown IANA timezone: {value}") from exc


def require_aware(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DomainValidationError(f"{field} must be timezone-aware")
    return value


def _valid_local_candidates(local_value: datetime, zone: ZoneInfo) -> list[datetime]:
    candidates: list[datetime] = []
    seen_offsets: set[timedelta | None] = set()
    for fold in (0, 1):
        candidate = local_value.replace(tzinfo=zone, fold=fold)
        round_trip = candidate.astimezone(UTC).astimezone(zone)
        if round_trip.replace(tzinfo=None) != local_value:
            continue
        if candidate.utcoffset() in seen_offsets:
            continue
        seen_offsets.add(candidate.utcoffset())
        candidates.append(candidate)
    return candidates


def resolve_local_datetime(local_value: datetime, zone: ZoneInfo) -> datetime:
    """Resolve wall time deterministically across DST gaps and folds."""

    if local_value.tzinfo is not None:
        raise DomainValidationError("local datetime must not already contain timezone information")
    candidate = local_value
    for _ in range(181):
        valid = _valid_local_candidates(candidate, zone)
        if valid:
            return valid[0]
        candidate += timedelta(minutes=1)
    raise DomainValidationError("local datetime cannot be resolved within three hours")


@dataclass(frozen=True, slots=True)
class PublicationSlot:
    guild_id: GuildId
    local_datetime: datetime
    timezone_name: str

    def __post_init__(self) -> None:
        aware = require_aware(self.local_datetime, "local_datetime")
        zone = timezone(self.timezone_name)
        object.__setattr__(self, "local_datetime", aware.astimezone(zone))

    @property
    def instant(self) -> datetime:
        return self.local_datetime.astimezone(UTC)

    @property
    def key(self) -> str:
        return (
            f"{int(self.guild_id)}:"
            f"{self.local_datetime.strftime('%Y-%m-%dT%H:%M')}:{self.timezone_name}"
        )


@dataclass(frozen=True, slots=True)
class PublicationSchedule:
    weekday: int = 0
    local_time: time = time(20, 0)
    timezone_name: str = DEFAULT_TIMEZONE

    def __post_init__(self) -> None:
        if not 0 <= self.weekday <= 6:
            raise DomainValidationError("weekday must be between 0 and 6")
        if self.local_time.tzinfo is not None:
            raise DomainValidationError("publication local_time must not include timezone")
        timezone(self.timezone_name)

    def next_slot(
        self, guild_id: GuildId, after: datetime, *, inclusive: bool = False
    ) -> PublicationSlot:
        reference = require_aware(after, "after")
        zone = timezone(self.timezone_name)
        local_reference = reference.astimezone(zone)
        days_ahead = (self.weekday - local_reference.weekday()) % 7
        candidate_date = local_reference.date() + timedelta(days=days_ahead)
        candidate = resolve_local_datetime(datetime.combine(candidate_date, self.local_time), zone)
        if candidate < local_reference or (candidate == local_reference and not inclusive):
            candidate_date += timedelta(days=7)
            candidate = resolve_local_datetime(
                datetime.combine(candidate_date, self.local_time), zone
            )
        return PublicationSlot(guild_id, candidate, self.timezone_name)


@dataclass(frozen=True, slots=True)
class PublicationWindow:
    starts_at: datetime
    ends_at: datetime
    timezone_name: str = DEFAULT_TIMEZONE

    def __post_init__(self) -> None:
        start = require_aware(self.starts_at, "starts_at")
        end = require_aware(self.ends_at, "ends_at")
        if end <= start:
            raise DomainValidationError("publication window end must be after start")

    @classmethod
    def from_slot(cls, slot: PublicationSlot) -> PublicationWindow:
        zone = timezone(slot.timezone_name)
        end_wall = slot.local_datetime.replace(tzinfo=None) + timedelta(days=14)
        end = resolve_local_datetime(end_wall, zone)
        return cls(slot.local_datetime, end, slot.timezone_name)

    def contains(self, instant: datetime) -> bool:
        value = require_aware(instant, "instant")
        return self.starts_at <= value < self.ends_at

    def overlaps_timed(self, starts_at: datetime, ends_at: datetime | None) -> bool:
        start = require_aware(starts_at, "starts_at")
        if ends_at is None:
            return self.contains(start)
        end = require_aware(ends_at, "ends_at")
        if end <= start:
            raise DomainValidationError("event end must be after start")
        return start < self.ends_at and end > self.starts_at

    def overlaps_all_day(self, starts_on: date, ends_on: date | None) -> bool:
        end = ends_on or starts_on + timedelta(days=1)
        if end <= starts_on:
            raise DomainValidationError("all-day event end must be after start")
        zone = timezone(self.timezone_name)
        window_start_date = self.starts_at.astimezone(zone).date()
        window_end_date = self.ends_at.astimezone(zone).date()
        return starts_on < window_end_date and end > window_start_date


def info_is_valid_on(valid_from: date, valid_until: date, day: date) -> bool:
    if valid_until < valid_from:
        raise DomainValidationError("INFO validity end cannot precede start")
    return valid_from <= day <= valid_until
