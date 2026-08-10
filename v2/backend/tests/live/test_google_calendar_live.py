"""Opt-in read-only tests against the isolated E0 Google calendars."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import text

from domcek_bot.application.calendar.sync import CalendarSyncMode, CalendarSyncService
from domcek_bot.application.records import (
    CalendarSourceRecord,
    EventOverrideRecord,
    GuildConfigRecord,
)
from domcek_bot.config import Settings
from domcek_bot.domain.calendar import parse_calendar_description
from domcek_bot.domain.enums import DescriptionState
from domcek_bot.infrastructure.calendar_factory import build_google_calendar_client
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.models import Base
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

RUN_LIVE = os.getenv("RUN_LIVE_GOOGLE_CALENDAR_TESTS") == "1"
REQUIRED_ENV = (
    "TEST_DATABASE_URL",
    "GOOGLE_SERVICE_ACCOUNT_FILE",
    "E3_TEST_PRIMARY_CALENDAR_ID",
    "E3_TEST_SECONDARY_CALENDAR_ID",
)
pytestmark = pytest.mark.skipif(
    not RUN_LIVE or any(not os.getenv(name) for name in REQUIRED_ENV),
    reason="opt-in Google Calendar live environment is not configured",
)

GUILD_ID = 1535774834955391047
EDITOR_USER_ID = 1535771583841439765


@pytest.fixture
async def live_database() -> AsyncIterator[Database]:
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


async def test_both_isolated_calendars_full_incremental_and_repeat_full(
    live_database: Database,
) -> None:
    settings = Settings(
        database_url=os.environ["TEST_DATABASE_URL"],
        google_service_account_file=Path(os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"]),
        calendar_sync_page_size=5,
    )
    client = build_google_calendar_client(settings)
    uow = SqlAlchemyUnitOfWork(live_database)
    primary = CalendarSourceRecord(
        id=uuid.uuid4(),
        guild_id=GUILD_ID,
        provider="google",
        external_calendar_id=os.environ["E3_TEST_PRIMARY_CALENDAR_ID"],
        display_name="E3 primary",
        priority=100,
    )
    secondary = CalendarSourceRecord(
        id=uuid.uuid4(),
        guild_id=GUILD_ID,
        provider="google",
        external_calendar_id=os.environ["E3_TEST_SECONDARY_CALENDAR_ID"],
        display_name="E3 secondary",
        priority=200,
    )
    async with uow.transaction() as transaction:
        await transaction.guild_configs.add(GuildConfigRecord(guild_id=GUILD_ID))
        await transaction.calendar_sources.add(primary)
        await transaction.calendar_sources.add(secondary)

    try:
        primary_service = CalendarSyncService(uow, client)
        secondary_service = CalendarSyncService(uow, client)
        primary_connection = await primary_service.verify_connection(primary.id)
        secondary_connection = await secondary_service.verify_connection(secondary.id)
        assert primary_connection.metadata.access_role in {"reader", "writer", "owner"}
        assert secondary_connection.metadata.access_role in {"reader", "writer", "owner"}

        primary_full = await primary_service.synchronize(primary.id)
        secondary_full = await secondary_service.synchronize(secondary.id)
        assert primary_full.mode is CalendarSyncMode.FULL
        assert primary_full.pages >= 4
        assert primary_full.received >= 16
        assert secondary_full.mode is CalendarSyncMode.FULL
        assert secondary_full.received >= 1

        async with uow.transaction() as transaction:
            primary_events = await transaction.external_events.list_for_source(primary.id)
            secondary_events = await transaction.external_events.list_for_source(secondary.id)
        assert len([event for event in primary_events if event.deleted_at is None]) >= 16
        assert len([event for event in secondary_events if event.deleted_at is None]) >= 1
        assert len([event for event in primary_events if event.is_all_day]) >= 2
        recurring_events = [event for event in primary_events if event.series_key is not None]
        assert len(recurring_events) >= 4
        assert any(event.original_start_key is not None for event in recurring_events)
        control_fixture_descriptions = [
            event.source_description
            for event in primary_events
            if event.source_title is not None and "Interná udalosť" in event.source_title
        ]
        assert any(
            parse_calendar_description(event.source_description).stop_carlo
            for event in primary_events
        ), control_fixture_descriptions

        overridden = recurring_events[0]
        async with uow.transaction() as transaction:
            await transaction.event_overrides.add(
                EventOverrideRecord(
                    external_event_id=overridden.id,
                    public_title="Live E3 redakčný titulok",
                    description_state=DescriptionState.CUSTOM,
                    public_description="Live E3 redakčný popis",
                    updated_by_user_id=EDITOR_USER_ID,
                )
            )

        primary_incremental = await primary_service.synchronize(primary.id)
        secondary_incremental = await secondary_service.synchronize(secondary.id)
        assert primary_incremental.mode is CalendarSyncMode.INCREMENTAL
        assert secondary_incremental.mode is CalendarSyncMode.INCREMENTAL

        repeated_full = await primary_service.synchronize(primary.id, force_full=True)
        assert repeated_full.mode is CalendarSyncMode.FULL
        async with uow.transaction() as transaction:
            refreshed_events = await transaction.external_events.list_for_source(primary.id)
            override = await transaction.event_overrides.get(overridden.id)
        refreshed_by_provider_id = {event.provider_event_id: event for event in refreshed_events}
        assert refreshed_by_provider_id[overridden.provider_event_id].id == overridden.id
        assert override is not None
        assert override.public_title == "Live E3 redakčný titulok"
    finally:
        await client.close()
