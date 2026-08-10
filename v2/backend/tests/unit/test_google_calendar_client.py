from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import httpx
import pytest

from domcek_bot.application.calendar.contracts import (
    CalendarAccessError,
    CalendarSyncTokenExpired,
)
from domcek_bot.domain.enums import ExternalEventStatus
from domcek_bot.infrastructure.google_calendar import GoogleCalendarClient


class FakeTokenProvider:
    def __init__(self) -> None:
        self.calls: list[bool] = []

    async def get_token(self, *, force_refresh: bool = False) -> str:
        self.calls.append(force_refresh)
        return "test-access-token"


def _client(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    token_provider: FakeTokenProvider | None = None,
    attempts: int = 3,
    sleep: Callable[[float], Awaitable[None]] | None = None,
) -> tuple[GoogleCalendarClient, FakeTokenProvider]:
    provider = token_provider or FakeTokenProvider()
    http_client = httpx.AsyncClient(
        base_url="https://www.googleapis.com/calendar/v3",
        transport=httpx.MockTransport(handler),
    )
    return (
        GoogleCalendarClient(
            provider,
            page_size=5,
            retry_attempts=attempts,
            retry_base_seconds=0,
            http_client=http_client,
            sleep=sleep or _no_sleep,
        ),
        provider,
    )


async def _no_sleep(_: float) -> None:
    return None


async def test_calendar_metadata_uses_encoded_id_and_bearer_token() -> None:
    observed: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["raw_path"] = request.url.raw_path.split(b"?", maxsplit=1)[0].decode("ascii")
        observed["authorization"] = request.headers["Authorization"]
        observed.update(dict(request.url.params))
        return httpx.Response(
            200,
            json={
                "summary": "Test",
                "timeZone": "Europe/Prague",
                "accessRole": "reader",
            },
        )

    client, _ = _client(handler)
    try:
        metadata = await client.get_calendar("calendar/id@example.test")
    finally:
        await client.close()

    assert observed["raw_path"] == ("/calendar/v3/calendars/calendar%2Fid%40example.test/events")
    assert observed["authorization"] == "Bearer test-access-token"
    assert observed["maxResults"] == "1"
    assert observed["singleEvents"] == "true"
    assert metadata.calendar_id == "calendar/id@example.test"
    assert metadata.access_role == "reader"


async def test_full_event_page_parses_timed_recurring_and_all_day_events() -> None:
    observed_params: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed_params.update(dict(request.url.params))
        return httpx.Response(
            200,
            json={
                "timeZone": "Europe/Prague",
                "nextSyncToken": "next-token",
                "items": [
                    {
                        "id": "instance-id",
                        "status": "confirmed",
                        "summary": "Recurring",
                        "description": "STOP CARLO",
                        "etag": "etag-1",
                        "updated": "2026-08-09T18:00:00Z",
                        "recurringEventId": "series-id",
                        "originalStartTime": {"dateTime": "2026-08-10T18:00:00+02:00"},
                        "start": {"dateTime": "2026-08-10T19:00:00+02:00"},
                        "end": {"dateTime": "2026-08-10T20:00:00+02:00"},
                    },
                    {
                        "id": "all-day-id",
                        "status": "tentative",
                        "start": {"date": "2026-08-11"},
                        "end": {"date": "2026-08-13"},
                    },
                ],
            },
        )

    client, _ = _client(handler)
    try:
        page = await client.list_events(
            "calendar@example.test",
            time_min=datetime(2026, 8, 1, tzinfo=UTC),
            time_max=datetime(2027, 8, 1, tzinfo=UTC),
        )
    finally:
        await client.close()

    assert observed_params["singleEvents"] == "true"
    assert observed_params["showDeleted"] == "true"
    assert observed_params["maxResults"] == "5"
    assert observed_params["timeMin"] == "2026-08-01T00:00:00Z"
    assert page.next_sync_token == "next-token"
    assert page.events[0].recurring_event_id == "series-id"
    assert page.events[0].original_start is not None
    assert page.events[1].status is ExternalEventStatus.TENTATIVE
    assert page.events[1].start is not None and page.events[1].start.is_all_day


async def test_incremental_request_keeps_sync_token_and_page_token() -> None:
    observed_params: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed_params.update(dict(request.url.params))
        return httpx.Response(
            200,
            json={
                "nextSyncToken": "new-token",
                "items": [{"id": "deleted-id", "status": "cancelled"}],
            },
        )

    client, _ = _client(handler)
    try:
        page = await client.list_events(
            "calendar@example.test",
            sync_token="old-token",
            page_token="page-2",
        )
    finally:
        await client.close()

    assert observed_params["syncToken"] == "old-token"
    assert observed_params["pageToken"] == "page-2"
    assert "timeMin" not in observed_params
    assert page.events[0].start is None
    assert page.events[0].status is ExternalEventStatus.CANCELLED


async def test_410_maps_to_expired_sync_token_without_retry() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(410, json={"error": {"code": 410}})

    client, _ = _client(handler)
    try:
        with pytest.raises(CalendarSyncTokenExpired):
            await client.list_events("calendar@example.test", sync_token="expired")
    finally:
        await client.close()
    assert calls == 1


async def test_429_retries_with_retry_after_then_succeeds() -> None:
    calls = 0
    sleeps: list[float] = []

    async def capture_sleep(delay: float) -> None:
        sleeps.append(delay)

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "2"})
        return httpx.Response(200, json={"nextSyncToken": "ok", "items": []})

    client, _ = _client(handler, sleep=capture_sleep)
    try:
        page = await client.list_events("calendar@example.test", sync_token="token")
    finally:
        await client.close()

    assert page.next_sync_token == "ok"
    assert calls == 2
    assert sleeps == [2.0]


async def test_401_forces_token_refresh_before_retry() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(401)
        return httpx.Response(200, json={"nextSyncToken": "ok", "items": []})

    client, token_provider = _client(handler)
    try:
        page = await client.list_events("calendar@example.test", sync_token="token")
    finally:
        await client.close()

    assert page.next_sync_token == "ok"
    assert token_provider.calls == [False, True]


async def test_access_denial_is_not_retried_or_leaked() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            403,
            content=json.dumps({"error": {"message": "sensitive provider detail"}}).encode(),
        )

    client, _ = _client(handler)
    try:
        with pytest.raises(CalendarAccessError) as captured:
            await client.get_calendar("calendar@example.test")
    finally:
        await client.close()

    assert calls == 1
    assert "sensitive provider detail" not in str(captured.value)
