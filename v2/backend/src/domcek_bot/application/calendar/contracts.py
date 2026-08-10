"""Provider-neutral contracts used by calendar synchronization services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from domcek_bot.domain.enums import ExternalEventStatus
from domcek_bot.domain.errors import DomainValidationError


class CalendarIntegrationError(RuntimeError):
    """Base error safe to map without exposing provider credentials or payloads."""


class CalendarAuthenticationError(CalendarIntegrationError):
    pass


class CalendarAccessError(CalendarIntegrationError):
    pass


class CalendarNotFoundError(CalendarIntegrationError):
    pass


class CalendarRateLimitError(CalendarIntegrationError):
    pass


class CalendarTemporaryError(CalendarIntegrationError):
    pass


class CalendarPayloadError(CalendarIntegrationError):
    pass


class CalendarSyncTokenExpired(CalendarIntegrationError):
    pass


@dataclass(frozen=True, slots=True)
class CalendarEventTime:
    """Exactly one provider event time shape: local date or aware instant."""

    date_value: date | None = None
    date_time_value: datetime | None = None
    timezone: str | None = None

    def __post_init__(self) -> None:
        has_date = self.date_value is not None
        has_datetime = self.date_time_value is not None
        if has_date == has_datetime:
            raise DomainValidationError("calendar time must contain exactly one value shape")
        if self.date_time_value is not None and self.date_time_value.utcoffset() is None:
            raise DomainValidationError("calendar date-time must include a UTC offset")

    @property
    def is_all_day(self) -> bool:
        return self.date_value is not None


@dataclass(frozen=True, slots=True)
class ProviderCalendarEvent:
    provider_event_id: str
    status: ExternalEventStatus
    start: CalendarEventTime | None
    end: CalendarEventTime | None
    title: str | None = None
    description: str | None = None
    etag: str | None = None
    updated_at: datetime | None = None
    recurring_event_id: str | None = None
    original_start: CalendarEventTime | None = None
    source_timezone: str | None = None


@dataclass(frozen=True, slots=True)
class CalendarEventPage:
    events: tuple[ProviderCalendarEvent, ...]
    next_page_token: str | None
    next_sync_token: str | None


@dataclass(frozen=True, slots=True)
class CalendarMetadata:
    calendar_id: str
    display_name: str
    timezone: str
    access_role: str


class CalendarClient(Protocol):
    @property
    def sync_query_key(self) -> str: ...

    async def get_calendar(self, calendar_id: str) -> CalendarMetadata: ...

    async def list_events(
        self,
        calendar_id: str,
        *,
        page_token: str | None = None,
        sync_token: str | None = None,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
    ) -> CalendarEventPage: ...

    async def close(self) -> None: ...
