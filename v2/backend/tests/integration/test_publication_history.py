from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from domcek_bot.application.auth.authorization import (
    AppRole,
    AuthorizationDenied,
    Principal,
)
from domcek_bot.application.publication.history import PublicationHistoryService
from domcek_bot.application.records import (
    CalendarSourceRecord,
    ChannelArchiveRequestRecord,
    GuildConfigRecord,
    PublicationItemRecord,
    PublicationMessageRecord,
    PublicationRunRecord,
)
from domcek_bot.config import AppEnvironment, Settings
from domcek_bot.domain.enums import (
    ArchiveState,
    PublicationItemType,
    PublicationMessageState,
    PublicationMode,
    PublicationState,
    SyncStatus,
)
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.models import Base
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.skipif(
    "TEST_DATABASE_URL" not in os.environ,
    reason="integration database not configured",
)

GUILD_ID = 1535774834955391047
OTHER_GUILD_ID = 1535774834955391999
NOW = datetime(2026, 8, 10, 18, 0, tzinfo=UTC)


@pytest.fixture
async def database() -> AsyncIterator[Database]:
    database = Database(
        Settings(app_env=AppEnvironment.TEST, database_url=os.environ["TEST_DATABASE_URL"])
    )
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    async with database.transaction() as connection:
        await connection.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))
    try:
        yield database
    finally:
        async with database.transaction() as connection:
            await connection.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))
        await database.close()


def _principal(role: AppRole | None, *, guild_id: int = GUILD_ID) -> Principal:
    return Principal(
        guild_id=guild_id,
        user_id=42,
        username="tester",
        display_name="Tester",
        avatar_url=None,
        discord_role_ids=frozenset(),
        app_roles=frozenset() if role is None else frozenset({role}),
    )


def _snapshot(
    guild_id: int,
    *,
    scheduled_for: datetime,
    title: str,
    state: PublicationState = PublicationState.SUCCEEDED_AUTOMATIC,
) -> tuple[
    PublicationRunRecord,
    tuple[PublicationItemRecord, ...],
    tuple[PublicationMessageRecord, ...],
]:
    run_id = uuid.uuid4()
    run = PublicationRunRecord(
        id=run_id,
        guild_id=guild_id,
        slot_key=scheduled_for.isoformat(),
        scheduled_for=scheduled_for,
        mode=PublicationMode.AUTOMATIC,
        state=state,
        attempt=1,
        idempotency_key=f"history:{guild_id}:{scheduled_for.isoformat()}",
        composer_version="test-v1",
        intro_text="Úvod",
        intro_prompt_version="fallback-v1",
        intro_used_fallback=True,
        completed_at=scheduled_for + timedelta(seconds=5),
    )
    item = PublicationItemRecord(
        id=uuid.uuid4(),
        publication_run_id=run_id,
        item_type=PublicationItemType.MANUAL_EVENT,
        position=0,
        final_title=title,
        final_description="Nemenný redakčný snapshot",
        display_time="utorok 18:00",
    )
    message = PublicationMessageRecord(
        id=uuid.uuid4(),
        publication_run_id=run_id,
        position=0,
        discord_channel_id=999,
        part_key="part-0",
        nonce=run_id.hex[:24],
        content="@everyone",
        embeds=({"title": title, "description": item.final_description},),
        allowed_mentions=("everyone",),
        seen_target=True,
        reaction_emoji="👀",
        state=PublicationMessageState.SENT,
        discord_message_id=int(run_id.hex[:12], 16),
        attempt_count=1,
        sent_at=scheduled_for + timedelta(seconds=4),
    )
    return run, (item,), (message,)


async def test_history_returns_ordered_immutable_snapshots_and_is_guild_isolated(
    database: Database,
) -> None:
    uow = SqlAlchemyUnitOfWork(database)
    older = _snapshot(GUILD_ID, scheduled_for=NOW - timedelta(days=7), title="Staršia")
    latest = _snapshot(GUILD_ID, scheduled_for=NOW, title="Najnovšia")
    foreign = _snapshot(OTHER_GUILD_ID, scheduled_for=NOW + timedelta(days=7), title="Cudzia")
    async with uow.transaction() as repositories:
        await repositories.guild_configs.add(GuildConfigRecord(guild_id=GUILD_ID))
        await repositories.guild_configs.add(GuildConfigRecord(guild_id=OTHER_GUILD_ID))
        for snapshot in (older, latest, foreign):
            await repositories.publication_runs.add_snapshot(*snapshot)

    service = PublicationHistoryService(uow)
    entries = await service.list(_principal(AppRole.PUBLISHER))

    assert [entry.run.id for entry in entries] == [latest[0].id, older[0].id]
    assert entries[0].items[0].final_title == "Najnovšia"
    assert entries[0].messages[0].discord_message_id == latest[2][0].discord_message_id
    assert entries[0].messages[0].reaction_emoji == "👀"
    assert await service.get(foreign[0].id, _principal(AppRole.ADMIN)) is None
    assert (await service.get(latest[0].id, _principal(AppRole.ADMIN))) == entries[0]

    with pytest.raises(AuthorizationDenied):
        await service.list(_principal(None))


async def test_dashboard_uses_live_configuration_latest_sync_run_and_pending_archives(
    database: Database,
) -> None:
    uow = SqlAlchemyUnitOfWork(database)
    latest_sync = NOW - timedelta(minutes=3)
    latest = _snapshot(GUILD_ID, scheduled_for=NOW, title="Posledná publikácia")
    async with uow.transaction() as repositories:
        await repositories.guild_configs.add(
            GuildConfigRecord(guild_id=GUILD_ID, automatic_publication_enabled=False)
        )
        await repositories.calendar_sources.add(
            CalendarSourceRecord(
                id=uuid.uuid4(),
                guild_id=GUILD_ID,
                provider="google",
                external_calendar_id="older@example.test",
                display_name="Starší sync",
                sync_status=SyncStatus.SUCCEEDED,
                last_sync_success_at=NOW - timedelta(hours=2),
            )
        )
        await repositories.calendar_sources.add(
            CalendarSourceRecord(
                id=uuid.uuid4(),
                guild_id=GUILD_ID,
                provider="google",
                external_calendar_id="latest@example.test",
                display_name="Čerstvý sync",
                sync_status=SyncStatus.SUCCEEDED,
                last_sync_success_at=latest_sync,
            )
        )
        await repositories.calendar_sources.add(
            CalendarSourceRecord(
                id=uuid.uuid4(),
                guild_id=GUILD_ID,
                provider="google",
                external_calendar_id="failed@example.test",
                display_name="Nikdy nesynchronizovaný",
                sync_status=SyncStatus.FAILED,
                last_sync_error="permission denied",
            )
        )
        await repositories.publication_runs.add_snapshot(*latest)
        await repositories.channel_archive_requests.add(
            ChannelArchiveRequestRecord(
                id=uuid.uuid4(),
                guild_id=GUILD_ID,
                discord_channel_id=777,
                original_channel_name="projekt",
                archive_category_id=888,
                requested_by_user_id=42,
                reason="hotovo",
                state=ArchiveState.PENDING,
                expires_at=NOW + timedelta(hours=1),
            )
        )

    summary = await PublicationHistoryService(uow, clock=lambda: NOW).dashboard(
        _principal(AppRole.ADMIN)
    )

    assert not summary.automatic_publication_enabled
    assert summary.last_calendar_sync_at == latest_sync
    assert summary.last_publication == latest[0]
    assert summary.pending_archive_count == 1
    assert not summary.discord_places_configured
    calendar_states = {
        calendar.display_name: calendar.freshness.value for calendar in summary.active_calendars
    }
    assert calendar_states == {
        "Starší sync": "fresh",
        "Čerstvý sync": "fresh",
        "Nikdy nesynchronizovaný": "unsafe",
    }
