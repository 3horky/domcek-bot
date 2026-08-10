from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import text

from domcek_bot.application.calendar.contracts import (
    CalendarClient,
    CalendarEventPage,
    CalendarEventTime,
    CalendarIntegrationError,
    CalendarMetadata,
    CalendarSyncTokenExpired,
    CalendarTemporaryError,
    ProviderCalendarEvent,
)
from domcek_bot.application.calendar.normalization import normalize_provider_event
from domcek_bot.application.calendar.sync import (
    CalendarSyncAlreadyRunning,
    CalendarSyncMode,
    CalendarSyncPolicy,
    CalendarSyncService,
)
from domcek_bot.application.records import (
    CalendarSourceRecord,
    EventOverrideRecord,
    GuildConfigRecord,
)
from domcek_bot.config import Settings
from domcek_bot.domain.enums import DescriptionState, ExternalEventStatus, SyncStatus
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.models import Base
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.skipif(
    "TEST_DATABASE_URL" not in os.environ,
    reason="integration database not configured",
)

GUILD_ID = 1535774834955391047
USER_ID = 1535771583841439765
NOW = datetime(2026, 8, 9, 18, 0, tzinfo=UTC)


@pytest.fixture
async def database() -> AsyncIterator[Database]:
    database = Database(Settings(database_url=os.environ["TEST_DATABASE_URL"]))
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    async with database.transaction() as connection:
        await connection.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))
    try:
        yield database
    finally:
        async with database.transaction() as connection:
            await connection.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))
        await database.close()


class ScriptedCalendarClient(CalendarClient):
    def __init__(
        self,
        script: list[CalendarEventPage | Exception],
        *,
        sync_query_key: str = "query-key-v1",
        access_role: str = "reader",
    ) -> None:
        self._script = list(script)
        self._sync_query_key = sync_query_key
        self._access_role = access_role
        self.requests: list[dict[str, object]] = []

    @property
    def sync_query_key(self) -> str:
        return self._sync_query_key

    async def get_calendar(self, calendar_id: str) -> CalendarMetadata:
        return CalendarMetadata(
            calendar_id=calendar_id,
            display_name="Test calendar",
            timezone="Europe/Prague",
            access_role=self._access_role,
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
        self.requests.append(
            {
                "calendar_id": calendar_id,
                "page_token": page_token,
                "sync_token": sync_token,
                "time_min": time_min,
                "time_max": time_max,
            }
        )
        if not self._script:
            raise AssertionError("calendar client script exhausted")
        result = self._script.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    async def close(self) -> None:
        return None


class CapturingAlerts:
    def __init__(self) -> None:
        self.alerts: list[tuple[int, uuid.UUID, str]] = []
        self.series_alerts: list[tuple[int, uuid.UUID, uuid.UUID]] = []

    async def calendar_sync_blocked(
        self, *, guild_id: int, source_id: uuid.UUID, error_code: str
    ) -> None:
        self.alerts.append((guild_id, source_id, error_code))

    async def calendar_series_identity_changed(
        self, *, guild_id: int, source_id: uuid.UUID, event_id: uuid.UUID
    ) -> None:
        self.series_alerts.append((guild_id, source_id, event_id))


def _source(
    *,
    sync_token: str | None = None,
    sync_token_query_key: str | None = None,
    sync_status: SyncStatus = SyncStatus.NEVER,
    last_sync_attempt_at: datetime | None = None,
) -> CalendarSourceRecord:
    return CalendarSourceRecord(
        id=uuid.uuid4(),
        guild_id=GUILD_ID,
        provider="google",
        external_calendar_id="calendar@example.test",
        display_name="Test calendar",
        sync_token=sync_token,
        sync_token_query_key=sync_token_query_key,
        sync_status=sync_status,
        last_sync_attempt_at=last_sync_attempt_at,
    )


def _timed_event(
    event_id: str,
    *,
    title: str,
    start: datetime = NOW + timedelta(days=1),
    recurring_event_id: str | None = None,
    original_start: datetime | None = None,
) -> ProviderCalendarEvent:
    return ProviderCalendarEvent(
        provider_event_id=event_id,
        status=ExternalEventStatus.CONFIRMED,
        title=title,
        description="Google popis",
        start=CalendarEventTime(date_time_value=start, timezone="Europe/Prague"),
        end=CalendarEventTime(date_time_value=start + timedelta(hours=1), timezone="Europe/Prague"),
        recurring_event_id=recurring_event_id,
        original_start=(
            None
            if original_start is None
            else CalendarEventTime(
                date_time_value=original_start,
                timezone="Europe/Prague",
            )
        ),
        updated_at=NOW,
        etag=f"etag-{title}",
    )


def _all_day_event(event_id: str) -> ProviderCalendarEvent:
    return ProviderCalendarEvent(
        provider_event_id=event_id,
        status=ExternalEventStatus.CONFIRMED,
        title="Viacdňová",
        start=CalendarEventTime(date_value=date(2026, 8, 12)),
        end=CalendarEventTime(date_value=date(2026, 8, 14)),
    )


def _cancelled(event_id: str) -> ProviderCalendarEvent:
    return ProviderCalendarEvent(
        provider_event_id=event_id,
        status=ExternalEventStatus.CANCELLED,
        start=None,
        end=None,
    )


async def _seed_source(database: Database, source: CalendarSourceRecord) -> SqlAlchemyUnitOfWork:
    uow = SqlAlchemyUnitOfWork(database)
    async with uow.transaction() as transaction:
        await transaction.guild_configs.add(GuildConfigRecord(guild_id=GUILD_ID))
        await transaction.calendar_sources.add(source)
    return uow


async def test_full_sync_is_paginated_atomic_and_marks_missing_after_success(
    database: Database,
) -> None:
    source = _source()
    uow = await _seed_source(database, source)
    stale = normalize_provider_event(
        _timed_event("stale-id", title="Stará"), source, synced_at=NOW - timedelta(days=1)
    )
    async with uow.transaction() as transaction:
        await transaction.external_events.add(stale)

    client = ScriptedCalendarClient(
        [
            CalendarEventPage(
                events=(_timed_event("event-1", title="Prvá"),),
                next_page_token="page-2",
                next_sync_token=None,
            ),
            CalendarEventPage(
                events=(_all_day_event("event-2"),),
                next_page_token=None,
                next_sync_token="sync-token-1",
            ),
        ]
    )
    service = CalendarSyncService(
        uow,
        client,
        clock=lambda: NOW,
        policy=CalendarSyncPolicy(
            past_horizon=timedelta(days=30), future_horizon=timedelta(days=400)
        ),
    )

    result = await service.synchronize(source.id)

    assert result.mode is CalendarSyncMode.FULL
    assert result.pages == 2
    assert result.created == 2
    assert result.missing_marked_deleted == 1
    assert client.requests[0]["page_token"] is None
    assert client.requests[1]["page_token"] == "page-2"
    assert client.requests[0]["sync_token"] is None
    assert client.requests[0]["time_min"] == NOW - timedelta(days=30)

    async with uow.transaction() as transaction:
        stored_source = await transaction.calendar_sources.get(source.id)
        events = await transaction.external_events.list_for_source(source.id)
    assert stored_source is not None
    assert stored_source.sync_status is SyncStatus.SUCCEEDED
    assert stored_source.sync_token == "sync-token-1"
    assert stored_source.sync_token_query_key == client.sync_query_key
    assert stored_source.last_full_sync_at == NOW
    by_provider_id = {event.provider_event_id: event for event in events}
    assert by_provider_id["stale-id"].deleted_at == NOW
    assert by_provider_id["event-1"].deleted_at is None
    assert by_provider_id["event-2"].starts_on == date(2026, 8, 12)


async def test_repeat_full_sync_preserves_internal_uuid_and_editor_override(
    database: Database,
) -> None:
    source = _source()
    uow = await _seed_source(database, source)
    first_event = _timed_event(
        "instance-id",
        title="Pôvodný titulok",
        recurring_event_id="series-id",
        original_start=NOW + timedelta(days=1),
    )
    first_client = ScriptedCalendarClient([CalendarEventPage((first_event,), None, "token-1")])
    await CalendarSyncService(uow, first_client, clock=lambda: NOW).synchronize(source.id)

    async with uow.transaction() as transaction:
        stored = (await transaction.external_events.list_for_source(source.id))[0]
        await transaction.event_overrides.add(
            EventOverrideRecord(
                external_event_id=stored.id,
                public_title="Redakčný titulok",
                description_state=DescriptionState.CUSTOM,
                public_description="Redakčný popis",
                updated_by_user_id=USER_ID,
            )
        )

    moved = _timed_event(
        "instance-id",
        title="Google zmenený titulok",
        start=NOW + timedelta(days=2),
        recurring_event_id="changed-series-id",
        original_start=NOW + timedelta(days=1),
    )
    second_client = ScriptedCalendarClient([CalendarEventPage((moved,), None, "token-2")])
    alerts = CapturingAlerts()
    result = await CalendarSyncService(
        uow,
        second_client,
        clock=lambda: NOW + timedelta(minutes=5),
        alerts=alerts,
    ).synchronize(source.id, force_full=True)

    async with uow.transaction() as transaction:
        updated = (await transaction.external_events.list_for_source(source.id))[0]
        override = await transaction.event_overrides.get(stored.id)
    assert result.updated == 1
    assert updated.id == stored.id
    assert updated.source_title == "Google zmenený titulok"
    assert updated.starts_at == NOW + timedelta(days=2)
    assert updated.original_start_key == stored.original_start_key
    assert updated.series_key != stored.series_key
    assert override is not None and override.public_title == "Redakčný titulok"
    assert result.series_identity_warnings == 1
    assert alerts.series_alerts == [(GUILD_ID, source.id, stored.id)]


async def test_incremental_sync_updates_only_received_and_handles_cancellations(
    database: Database,
) -> None:
    source = _source(sync_token="old-token", sync_token_query_key="query-key-v1")
    uow = await _seed_source(database, source)
    unchanged = normalize_provider_event(
        _timed_event("unchanged-id", title="Nezmenená"), source, synced_at=NOW
    )
    changed = normalize_provider_event(
        _timed_event("changed-id", title="Pôvodná"), source, synced_at=NOW
    )
    cancelled = normalize_provider_event(
        _timed_event("cancelled-id", title="Na zrušenie"), source, synced_at=NOW
    )
    async with uow.transaction() as transaction:
        await transaction.external_events.add(unchanged)
        await transaction.external_events.add(changed)
        await transaction.external_events.add(cancelled)

    client = ScriptedCalendarClient(
        [
            CalendarEventPage(
                events=(
                    _timed_event("changed-id", title="Aktualizovaná"),
                    _cancelled("cancelled-id"),
                    _cancelled("unknown-id"),
                ),
                next_page_token=None,
                next_sync_token="new-token",
            )
        ]
    )
    result = await CalendarSyncService(uow, client, clock=lambda: NOW).synchronize(source.id)

    assert result.mode is CalendarSyncMode.INCREMENTAL
    assert result.updated == 1
    assert result.cancelled == 1
    assert result.ignored_cancellations == 1
    assert result.missing_marked_deleted == 0
    assert client.requests[0]["sync_token"] == "old-token"
    assert client.requests[0]["time_min"] is None

    async with uow.transaction() as transaction:
        events = await transaction.external_events.list_for_source(source.id)
    by_id = {event.provider_event_id: event for event in events}
    assert by_id["unchanged-id"].deleted_at is None
    assert by_id["unchanged-id"].source_title == "Nezmenená"
    assert by_id["changed-id"].source_title == "Aktualizovaná"
    assert by_id["cancelled-id"].status is ExternalEventStatus.CANCELLED
    assert by_id["cancelled-id"].deleted_at == NOW


async def test_expired_token_falls_back_to_full_sync_without_preemptive_wipe(
    database: Database,
) -> None:
    source = _source(sync_token="expired", sync_token_query_key="query-key-v1")
    uow = await _seed_source(database, source)
    existing = normalize_provider_event(
        _timed_event("existing-id", title="Existujúca"), source, synced_at=NOW
    )
    async with uow.transaction() as transaction:
        await transaction.external_events.add(existing)

    client = ScriptedCalendarClient(
        [
            CalendarSyncTokenExpired("expired"),
            CalendarEventPage(
                events=(_timed_event("existing-id", title="Po full syncu"),),
                next_page_token=None,
                next_sync_token="replacement-token",
            ),
        ]
    )
    result = await CalendarSyncService(uow, client, clock=lambda: NOW).synchronize(source.id)

    assert result.mode is CalendarSyncMode.FULL_AFTER_EXPIRED_TOKEN
    assert client.requests[0]["sync_token"] == "expired"
    assert client.requests[1]["sync_token"] is None
    assert client.requests[1]["time_min"] is not None
    async with uow.transaction() as transaction:
        events = await transaction.external_events.list_for_source(source.id)
    assert len(events) == 1
    assert events[0].id == existing.id
    assert events[0].source_title == "Po full syncu"


async def test_failed_second_page_changes_no_events_or_token_and_emits_alert(
    database: Database,
) -> None:
    source = _source(sync_token="stable-token", sync_token_query_key="query-key-v1")
    uow = await _seed_source(database, source)
    existing = normalize_provider_event(
        _timed_event("existing-id", title="Pred chybou"), source, synced_at=NOW
    )
    async with uow.transaction() as transaction:
        await transaction.external_events.add(existing)

    alerts = CapturingAlerts()
    client = ScriptedCalendarClient(
        [
            CalendarEventPage(
                events=(_timed_event("existing-id", title="Nesmie sa uložiť"),),
                next_page_token="page-2",
                next_sync_token=None,
            ),
            CalendarTemporaryError("provider unavailable"),
        ]
    )
    service = CalendarSyncService(uow, client, clock=lambda: NOW, alerts=alerts)

    with pytest.raises(CalendarTemporaryError):
        await service.synchronize(source.id)

    async with uow.transaction() as transaction:
        stored_source = await transaction.calendar_sources.get(source.id)
        events = await transaction.external_events.list_for_source(source.id)
    assert stored_source is not None
    assert stored_source.sync_status is SyncStatus.FAILED
    assert stored_source.sync_token == "stable-token"
    assert stored_source.last_sync_error == "CalendarTemporaryError"
    assert events[0].source_title == "Pred chybou"
    assert alerts.alerts == [(GUILD_ID, source.id, "CalendarTemporaryError")]


async def test_changed_query_fingerprint_forces_full_sync(database: Database) -> None:
    source = _source(sync_token="old-token", sync_token_query_key="old-query-key")
    uow = await _seed_source(database, source)
    client = ScriptedCalendarClient(
        [CalendarEventPage(events=(), next_page_token=None, next_sync_token="new-token")],
        sync_query_key="new-query-key",
    )

    result = await CalendarSyncService(uow, client, clock=lambda: NOW).synchronize(source.id)

    assert result.mode is CalendarSyncMode.FULL
    assert client.requests[0]["sync_token"] is None
    assert client.requests[0]["time_min"] is not None


async def test_connection_check_requires_effective_event_read_access(
    database: Database,
) -> None:
    source = _source()
    uow = await _seed_source(database, source)

    reader = await CalendarSyncService(
        uow, ScriptedCalendarClient([], access_role="reader")
    ).verify_connection(source.id)
    assert reader.metadata.access_role == "reader"

    with pytest.raises(CalendarIntegrationError, match="event read access"):
        await CalendarSyncService(
            uow, ScriptedCalendarClient([], access_role="freeBusyReader")
        ).verify_connection(source.id)


async def test_recent_running_sync_is_rejected_but_expired_lease_can_be_taken_over(
    database: Database,
) -> None:
    running = _source(sync_status=SyncStatus.RUNNING, last_sync_attempt_at=NOW)
    uow = await _seed_source(database, running)
    blocked_client = ScriptedCalendarClient(
        [CalendarEventPage(events=(), next_page_token=None, next_sync_token="unused")]
    )

    with pytest.raises(CalendarSyncAlreadyRunning):
        await CalendarSyncService(uow, blocked_client, clock=lambda: NOW).synchronize(running.id)
    assert blocked_client.requests == []

    takeover_client = ScriptedCalendarClient(
        [CalendarEventPage(events=(), next_page_token=None, next_sync_token="taken-over")]
    )
    result = await CalendarSyncService(
        uow,
        takeover_client,
        clock=lambda: NOW + timedelta(minutes=16),
    ).synchronize(running.id)

    assert result.mode is CalendarSyncMode.FULL
    assert len(takeover_client.requests) == 1
