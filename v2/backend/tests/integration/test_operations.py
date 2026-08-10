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
from domcek_bot.application.operations import RuntimeOperationsService
from domcek_bot.application.records import (
    CalendarSourceRecord,
    GuildConfigRecord,
    IntegrationTaskRecord,
    PublicationRunRecord,
)
from domcek_bot.config import AppEnvironment, Settings
from domcek_bot.domain.enums import (
    IntegrationTaskState,
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
NOW = datetime(2026, 8, 9, 10, tzinfo=UTC)


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


def _principal(role: AppRole | None, guild_id: int = GUILD_ID) -> Principal:
    return Principal(
        guild_id=guild_id,
        user_id=42,
        username="operator",
        display_name="Operator",
        avatar_url=None,
        discord_role_ids=frozenset(),
        app_roles=frozenset() if role is None else frozenset({role}),
    )


def _run(state: PublicationState, *, offset: int) -> PublicationRunRecord:
    run_id = uuid.uuid4()
    scheduled = NOW - timedelta(days=offset)
    return PublicationRunRecord(
        id=run_id,
        guild_id=GUILD_ID,
        slot_key=f"slot-{offset}",
        scheduled_for=scheduled,
        mode=PublicationMode.AUTOMATIC,
        state=state,
        attempt=1,
        idempotency_key=f"operations-{run_id}",
        composer_version="test-v1",
        intro_text="Úvod",
        intro_prompt_version="fallback-v1",
        intro_used_fallback=True,
        completed_at=scheduled if state is not PublicationState.RETRY_PENDING else None,
    )


async def test_operational_summary_is_persistent_fresh_and_guild_isolated(
    database: Database,
) -> None:
    unit_of_work = SqlAlchemyUnitOfWork(database)
    operations = RuntimeOperationsService(unit_of_work)
    bot_instance = uuid.uuid4()
    worker_instance = uuid.uuid4()
    second_worker_instance = uuid.uuid4()
    third_worker_instance = uuid.uuid4()
    task = IntegrationTaskRecord(
        id=uuid.uuid4(),
        guild_id=GUILD_ID,
        task_type="channel.create",
        deduplication_key="operations-task",
        state=IntegrationTaskState.QUEUED,
        scheduled_for=NOW - timedelta(minutes=2),
    )
    async with unit_of_work.transaction() as repositories:
        await repositories.guild_configs.add(GuildConfigRecord(guild_id=GUILD_ID))
        await repositories.guild_configs.add(GuildConfigRecord(guild_id=OTHER_GUILD_ID))
        await repositories.calendar_sources.add(
            CalendarSourceRecord(
                id=uuid.uuid4(),
                guild_id=GUILD_ID,
                provider="google",
                external_calendar_id="operations@example.test",
                display_name="Prevádzkový kalendár",
                sync_status=SyncStatus.FAILED,
                last_sync_attempt_at=NOW - timedelta(minutes=1),
                last_sync_error="calendar_unavailable",
            )
        )
        await repositories.publication_runs.add_snapshot(
            _run(PublicationState.SUCCEEDED_AUTOMATIC, offset=14), (), ()
        )
        await repositories.publication_runs.add_snapshot(
            _run(PublicationState.FAILED, offset=7), (), ()
        )
        await repositories.publication_runs.add_snapshot(
            _run(PublicationState.RETRY_PENDING, offset=1), (), ()
        )
        await repositories.integration_tasks.claim(task)

    await operations.heartbeat(
        guild_id=GUILD_ID,
        process_name="bot",
        instance_id=bot_instance,
        state="connected",
        started_at=NOW - timedelta(hours=1),
        observed_at=NOW - timedelta(seconds=10),
        details={"latency_ms": 25},
    )
    await operations.heartbeat(
        guild_id=GUILD_ID,
        process_name="worker",
        instance_id=worker_instance,
        state="running",
        started_at=NOW - timedelta(hours=1),
        observed_at=NOW - timedelta(minutes=5),
        details={"publication_execution_mode": "shadow"},
    )
    for instance_id, age_seconds in (
        (second_worker_instance, 20),
        (third_worker_instance, 30),
    ):
        await operations.heartbeat(
            guild_id=GUILD_ID,
            process_name="worker",
            instance_id=instance_id,
            state="running",
            started_at=NOW - timedelta(hours=1),
            observed_at=NOW - timedelta(seconds=age_seconds),
            details={"publication_execution_mode": "shadow"},
        )
    await operations.heartbeat(
        guild_id=OTHER_GUILD_ID,
        process_name="bot",
        instance_id=uuid.uuid4(),
        state="connected",
        started_at=NOW,
        observed_at=NOW,
    )

    summary = await operations.summary(_principal(AppRole.TEAM_MOD), now=NOW)

    assert [(item.process_name, item.healthy) for item in summary.processes] == [
        ("bot", True),
        ("worker", True),
    ]
    assert summary.active_instance_counts == {"bot": 1, "worker": 2}
    assert summary.processes[0].details == {"latency_ms": 25}
    assert [calendar.sync_status for calendar in summary.calendars] == [SyncStatus.FAILED]
    assert summary.publication_metrics.sample_size == 3
    assert summary.publication_metrics.successful == 1
    assert summary.publication_metrics.failed == 1
    assert summary.publication_metrics.in_progress == 1
    assert summary.recent_tasks[0].id == task.id
    assert summary.next_slot_key.startswith(f"{GUILD_ID}:2026-08-10T20:00")
    assert summary.next_scheduled_for == datetime(2026, 8, 10, 18, tzinfo=UTC)

    with pytest.raises(AuthorizationDenied):
        await operations.summary(_principal(None), now=NOW)


async def test_heartbeat_upsert_keeps_identity_and_updates_state(database: Database) -> None:
    unit_of_work = SqlAlchemyUnitOfWork(database)
    operations = RuntimeOperationsService(unit_of_work)
    instance_id = uuid.uuid4()
    async with unit_of_work.transaction() as repositories:
        await repositories.guild_configs.add(GuildConfigRecord(guild_id=GUILD_ID))

    for state, observed_at in (
        ("connected", NOW - timedelta(seconds=10)),
        ("disconnected", NOW),
    ):
        await operations.heartbeat(
            guild_id=GUILD_ID,
            process_name="bot",
            instance_id=instance_id,
            state=state,
            started_at=NOW - timedelta(hours=1),
            observed_at=observed_at,
        )

    async with unit_of_work.transaction() as repositories:
        heartbeats = await repositories.runtime_heartbeats.list_for_guild(GUILD_ID)
    assert len(heartbeats) == 1
    assert heartbeats[0].state == "disconnected"
    assert heartbeats[0].last_seen_at == NOW


async def test_heartbeat_rejects_naive_timestamps(database: Database) -> None:
    operations = RuntimeOperationsService(SqlAlchemyUnitOfWork(database))
    with pytest.raises(ValueError, match="timezone-aware"):
        await operations.heartbeat(
            guild_id=GUILD_ID,
            process_name="bot",
            instance_id=uuid.uuid4(),
            state="connected",
            started_at=datetime(2026, 8, 9, 10),
            observed_at=NOW,
        )


async def test_process_health_accepts_one_ready_bot_and_matching_worker(
    database: Database,
) -> None:
    unit_of_work = SqlAlchemyUnitOfWork(database)
    operations = RuntimeOperationsService(unit_of_work)
    async with unit_of_work.transaction() as repositories:
        await repositories.guild_configs.add(GuildConfigRecord(guild_id=GUILD_ID))
    for process_name, state, details in (
        ("bot", "connected", {}),
        ("worker", "running", {"publication_execution_mode": "shadow"}),
    ):
        await operations.heartbeat(
            guild_id=GUILD_ID,
            process_name=process_name,
            instance_id=uuid.uuid4(),
            state=state,
            started_at=NOW - timedelta(hours=1),
            observed_at=NOW - timedelta(seconds=10),
            details=details,
        )

    bot_health = await operations.process_health(
        guild_id=GUILD_ID,
        process_name="bot",
        expected_state="connected",
        now=NOW,
    )
    worker_health = await operations.process_health(
        guild_id=GUILD_ID,
        process_name="worker",
        expected_state="running",
        expected_execution_mode="shadow",
        now=NOW,
    )

    assert bot_health.healthy is True
    assert bot_health.reason == "ready"
    assert bot_health.active_instances == 1
    assert worker_health.healthy is True
    assert worker_health.reason == "ready"


async def test_process_health_rejects_duplicate_and_stale_instances(database: Database) -> None:
    unit_of_work = SqlAlchemyUnitOfWork(database)
    operations = RuntimeOperationsService(unit_of_work)
    async with unit_of_work.transaction() as repositories:
        await repositories.guild_configs.add(GuildConfigRecord(guild_id=GUILD_ID))
    for age_seconds in (5, 10):
        await operations.heartbeat(
            guild_id=GUILD_ID,
            process_name="bot",
            instance_id=uuid.uuid4(),
            state="connected",
            started_at=NOW - timedelta(hours=1),
            observed_at=NOW - timedelta(seconds=age_seconds),
        )

    duplicate = await operations.process_health(
        guild_id=GUILD_ID,
        process_name="bot",
        expected_state="connected",
        now=NOW,
    )
    stale = await operations.process_health(
        guild_id=GUILD_ID,
        process_name="bot",
        expected_state="connected",
        now=NOW + timedelta(minutes=2),
    )

    assert duplicate.healthy is False
    assert duplicate.reason == "duplicate_active_instances"
    assert duplicate.active_instances == 2
    assert stale.healthy is False
    assert stale.reason == "no_fresh_instance"
    assert stale.active_instances == 0


async def test_process_health_rejects_wrong_state_mode_and_invalid_freshness(
    database: Database,
) -> None:
    unit_of_work = SqlAlchemyUnitOfWork(database)
    operations = RuntimeOperationsService(unit_of_work)
    async with unit_of_work.transaction() as repositories:
        await repositories.guild_configs.add(GuildConfigRecord(guild_id=GUILD_ID))
    instance_id = uuid.uuid4()
    await operations.heartbeat(
        guild_id=GUILD_ID,
        process_name="worker",
        instance_id=instance_id,
        state="starting",
        started_at=NOW - timedelta(minutes=1),
        observed_at=NOW,
        details={"publication_execution_mode": "paused"},
    )

    wrong_state = await operations.process_health(
        guild_id=GUILD_ID,
        process_name="worker",
        expected_state="running",
        expected_execution_mode="shadow",
        now=NOW,
    )
    assert wrong_state.healthy is False
    assert wrong_state.reason == "unexpected_state"

    await operations.heartbeat(
        guild_id=GUILD_ID,
        process_name="worker",
        instance_id=instance_id,
        state="running",
        started_at=NOW - timedelta(minutes=1),
        observed_at=NOW,
        details={"publication_execution_mode": "paused"},
    )
    wrong_mode = await operations.process_health(
        guild_id=GUILD_ID,
        process_name="worker",
        expected_state="running",
        expected_execution_mode="shadow",
        now=NOW,
    )
    assert wrong_mode.healthy is False
    assert wrong_mode.reason == "unexpected_execution_mode"

    with pytest.raises(ValueError, match="freshness"):
        await operations.process_health(
            guild_id=GUILD_ID,
            process_name="worker",
            expected_state="running",
            now=NOW,
            stale_after=timedelta(0),
        )
