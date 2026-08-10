"""Async Google Calendar v3 read-only adapter with service-account OAuth."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Protocol, cast
from urllib.parse import quote

import httpx
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials

from domcek_bot.application.calendar.contracts import (
    CalendarAccessError,
    CalendarAuthenticationError,
    CalendarClient,
    CalendarEventPage,
    CalendarEventTime,
    CalendarIntegrationError,
    CalendarMetadata,
    CalendarNotFoundError,
    CalendarPayloadError,
    CalendarRateLimitError,
    CalendarSyncTokenExpired,
    CalendarTemporaryError,
    ProviderCalendarEvent,
)
from domcek_bot.domain.enums import ExternalEventStatus

GOOGLE_CALENDAR_READONLY_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
GOOGLE_CALENDAR_API_BASE_URL = "https://www.googleapis.com/calendar/v3"
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class AccessTokenProvider(Protocol):
    async def get_token(self, *, force_refresh: bool = False) -> str: ...


class GoogleServiceAccountTokenProvider:
    """Refresh a scoped service-account token outside the async event loop."""

    def __init__(self, credentials: Credentials) -> None:
        self._credentials = credentials
        self._lock = asyncio.Lock()

    @classmethod
    def from_file(cls, path: Path) -> GoogleServiceAccountTokenProvider:
        credentials = Credentials.from_service_account_file(  # type: ignore[no-untyped-call]
            str(path), scopes=[GOOGLE_CALENDAR_READONLY_SCOPE]
        )
        return cls(credentials)

    async def get_token(self, *, force_refresh: bool = False) -> str:
        async with self._lock:
            if force_refresh or not self._credentials.valid:
                try:
                    await asyncio.to_thread(self._credentials.refresh, Request())
                except Exception as exc:
                    raise CalendarAuthenticationError(
                        "Google service-account authentication failed"
                    ) from exc
            token = self._credentials.token
            if not isinstance(token, str) or not token:
                raise CalendarAuthenticationError("Google did not provide an access token")
            return token


class GoogleCalendarClient(CalendarClient):
    def __init__(
        self,
        token_provider: AccessTokenProvider,
        *,
        page_size: int = 250,
        timeout_seconds: float = 15.0,
        retry_attempts: int = 3,
        retry_base_seconds: float = 0.5,
        timezone: str = "Europe/Bratislava",
        http_client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if not 1 <= page_size <= 2500:
            raise ValueError("Google Calendar page size must be between 1 and 2500")
        if retry_attempts < 1:
            raise ValueError("retry_attempts must be positive")
        if retry_base_seconds < 0:
            raise ValueError("retry_base_seconds cannot be negative")
        self._token_provider = token_provider
        self._page_size = page_size
        self._retry_attempts = retry_attempts
        self._retry_base_seconds = retry_base_seconds
        self._timezone = timezone
        self._sleep = sleep
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(
            base_url=GOOGLE_CALENDAR_API_BASE_URL,
            timeout=timeout_seconds,
            headers={"User-Agent": "domcek-bot-v2-calendar-sync"},
        )
        compatible_query = {
            "maxResults": str(page_size),
            "showDeleted": "true",
            "singleEvents": "true",
            "timeZone": timezone,
        }
        canonical = json.dumps(compatible_query, sort_keys=True, separators=(",", ":"))
        self._sync_query_key = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @property
    def sync_query_key(self) -> str:
        return self._sync_query_key

    async def get_calendar(self, calendar_id: str) -> CalendarMetadata:
        encoded_id = quote(_nonempty(calendar_id, "calendar id"), safe="")
        # Events.list returns the effective accessRole and also works for a
        # calendar explicitly shared with a service account even when that
        # calendar has not been inserted into the account's calendarList.
        payload = await self._get_json(
            f"/calendars/{encoded_id}/events",
            params={"maxResults": "1", "showDeleted": "false", "singleEvents": "true"},
        )
        return CalendarMetadata(
            calendar_id=calendar_id,
            display_name=_string(payload, "summary"),
            timezone=_string(payload, "timeZone"),
            access_role=_string(payload, "accessRole"),
        )

    async def list_events(
        self,
        calendar_id: str,
        *,
        page_token: str | None = None,
        sync_token: str | None = None,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
    ) -> CalendarEventPage:
        if sync_token is not None and (time_min is not None or time_max is not None):
            raise ValueError("Google syncToken cannot be combined with timeMin or timeMax")
        if (time_min is None) != (time_max is None):
            raise ValueError("full sync bounds must be supplied together")

        params = {
            "maxResults": str(self._page_size),
            "showDeleted": "true",
            "singleEvents": "true",
            "timeZone": self._timezone,
        }
        if page_token:
            params["pageToken"] = page_token
        if sync_token:
            params["syncToken"] = sync_token
        if time_min is not None and time_max is not None:
            params["timeMin"] = _rfc3339(time_min)
            params["timeMax"] = _rfc3339(time_max)

        encoded_id = quote(_nonempty(calendar_id, "calendar id"), safe="")
        payload = await self._get_json(f"/calendars/{encoded_id}/events", params=params)
        calendar_timezone = _optional_string(payload, "timeZone") or self._timezone
        raw_items = payload.get("items", [])
        if not isinstance(raw_items, list):
            raise CalendarPayloadError("Google events response has invalid items")
        events = tuple(
            _parse_event(_mapping(item, "event"), calendar_timezone) for item in raw_items
        )
        return CalendarEventPage(
            events=events,
            next_page_token=_optional_string(payload, "nextPageToken"),
            next_sync_token=_optional_string(payload, "nextSyncToken"),
        )

    async def close(self) -> None:
        if self._owns_http_client:
            await self._http_client.aclose()

    async def _get_json(self, path: str, *, params: Mapping[str, str]) -> dict[str, Any]:
        force_refresh = False
        last_retryable_status: int | None = None
        for attempt in range(self._retry_attempts):
            token = await self._token_provider.get_token(force_refresh=force_refresh)
            force_refresh = False
            try:
                response = await self._http_client.get(
                    path,
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt + 1 >= self._retry_attempts:
                    raise CalendarTemporaryError("Google Calendar request failed") from exc
                await self._sleep(self._retry_delay(attempt, None))
                continue

            if response.status_code == 401 and attempt + 1 < self._retry_attempts:
                force_refresh = True
                continue
            if response.status_code == 401:
                raise CalendarAuthenticationError("Google Calendar rejected authentication")
            if response.status_code == 403:
                raise CalendarAccessError("Google Calendar access was denied")
            if response.status_code == 404:
                raise CalendarNotFoundError("Google Calendar was not found")
            if response.status_code == 410:
                raise CalendarSyncTokenExpired("Google Calendar sync token expired")
            if response.status_code in RETRYABLE_STATUS_CODES:
                last_retryable_status = response.status_code
                if attempt + 1 < self._retry_attempts:
                    await self._sleep(self._retry_delay(attempt, response))
                    continue
                if response.status_code == 429:
                    raise CalendarRateLimitError("Google Calendar rate limit exceeded")
                raise CalendarTemporaryError(
                    f"Google Calendar temporary HTTP {response.status_code}"
                )
            if response.is_error:
                raise CalendarIntegrationError(
                    f"Google Calendar returned HTTP {response.status_code}"
                )

            try:
                payload = response.json()
            except ValueError as exc:
                raise CalendarPayloadError("Google Calendar returned invalid JSON") from exc
            if not isinstance(payload, dict):
                raise CalendarPayloadError("Google Calendar returned an invalid object")
            return cast(dict[str, Any], payload)

        raise CalendarTemporaryError(
            f"Google Calendar request exhausted retries ({last_retryable_status})"
        )

    def _retry_delay(self, attempt: int, response: httpx.Response | None) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after is not None:
                try:
                    return min(max(float(retry_after), 0.0), 60.0)
                except ValueError:
                    pass
        return float(min(self._retry_base_seconds * (2**attempt), 60.0))


def _parse_event(payload: Mapping[str, Any], calendar_timezone: str) -> ProviderCalendarEvent:
    status_value = _optional_string(payload, "status") or ExternalEventStatus.CONFIRMED.value
    try:
        status = ExternalEventStatus(status_value)
    except ValueError as exc:
        raise CalendarPayloadError(f"unsupported Google event status: {status_value}") from exc

    start = _optional_event_time(payload.get("start"), calendar_timezone)
    end = _optional_event_time(payload.get("end"), calendar_timezone)
    original_start = _optional_event_time(payload.get("originalStartTime"), calendar_timezone)
    updated_raw = _optional_string(payload, "updated")
    return ProviderCalendarEvent(
        provider_event_id=_string(payload, "id"),
        status=status,
        start=start,
        end=end,
        title=_optional_string(payload, "summary"),
        description=_optional_string(payload, "description"),
        etag=_optional_string(payload, "etag"),
        updated_at=None if updated_raw is None else _parse_datetime(updated_raw, "updated"),
        recurring_event_id=_optional_string(payload, "recurringEventId"),
        original_start=original_start,
        source_timezone=(start.timezone if start is not None else None) or calendar_timezone,
    )


def _optional_event_time(value: object, fallback_timezone: str) -> CalendarEventTime | None:
    if value is None:
        return None
    mapping = _mapping(value, "event time")
    date_raw = _optional_string(mapping, "date")
    datetime_raw = _optional_string(mapping, "dateTime")
    timezone = _optional_string(mapping, "timeZone") or fallback_timezone
    if date_raw is not None and datetime_raw is not None:
        raise CalendarPayloadError("Google event time mixes date and dateTime")
    if date_raw is not None:
        try:
            return CalendarEventTime(date_value=date.fromisoformat(date_raw), timezone=timezone)
        except ValueError as exc:
            raise CalendarPayloadError("Google event contains invalid date") from exc
    if datetime_raw is not None:
        return CalendarEventTime(
            date_time_value=_parse_datetime(datetime_raw, "event dateTime"),
            timezone=timezone,
        )
    raise CalendarPayloadError("Google event time has no date or dateTime")


def _parse_datetime(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CalendarPayloadError(f"Google {field} is not valid RFC3339") from exc
    if parsed.utcoffset() is None:
        raise CalendarPayloadError(f"Google {field} has no UTC offset")
    return parsed


def _rfc3339(value: datetime) -> str:
    if value.utcoffset() is None:
        raise ValueError("Google Calendar bounds must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise CalendarPayloadError(f"Google {field} must be an object")
    return cast(Mapping[str, Any], value)


def _string(payload: Mapping[str, Any], key: str) -> str:
    value = _optional_string(payload, key)
    if value is None:
        raise CalendarPayloadError(f"Google response is missing {key}")
    return value


def _optional_string(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise CalendarPayloadError(f"Google response field {key} must be a string")
    return value


def _nonempty(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field} cannot be empty")
    return normalized
