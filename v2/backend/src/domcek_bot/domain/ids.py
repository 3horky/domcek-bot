"""Validated external identifiers and stable provider keys."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Self

from domcek_bot.domain.errors import DomainValidationError

MAX_SIGNED_BIGINT = 2**63 - 1


class DiscordSnowflake(int):
    """Positive Discord snowflake that fits the selected PostgreSQL BIGINT."""

    def __new__(cls, value: int | str) -> Self:
        if isinstance(value, bool):
            raise DomainValidationError("Discord snowflake cannot be boolean")
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise DomainValidationError("Discord snowflake must be an integer") from exc
        if parsed <= 0 or parsed > MAX_SIGNED_BIGINT:
            raise DomainValidationError("Discord snowflake is outside the supported range")
        return super().__new__(cls, parsed)


class GuildId(DiscordSnowflake):
    pass


class RoleId(DiscordSnowflake):
    pass


class ChannelId(DiscordSnowflake):
    pass


def _required(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise DomainValidationError(f"{field} cannot be empty")
    return normalized


def _digest(parts: tuple[str, ...]) -> str:
    canonical = json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class EventSourceKey:
    provider: str
    calendar_id: str
    event_id: str
    occurrence_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider", _required(self.provider, "provider"))
        object.__setattr__(self, "calendar_id", _required(self.calendar_id, "calendar_id"))
        object.__setattr__(self, "event_id", _required(self.event_id, "event_id"))
        if self.occurrence_id is not None:
            object.__setattr__(
                self, "occurrence_id", _required(self.occurrence_id, "occurrence_id")
            )

    @property
    def value(self) -> str:
        return _digest((self.provider, self.calendar_id, self.event_id, self.occurrence_id or ""))


@dataclass(frozen=True, slots=True)
class RecurringSeriesKey:
    provider: str
    calendar_id: str
    series_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider", _required(self.provider, "provider"))
        object.__setattr__(self, "calendar_id", _required(self.calendar_id, "calendar_id"))
        object.__setattr__(self, "series_id", _required(self.series_id, "series_id"))

    @property
    def value(self) -> str:
        return _digest((self.provider, self.calendar_id, self.series_id))
