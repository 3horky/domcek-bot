from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import delete, inspect, select, text
from sqlalchemy.exc import IntegrityError

from domcek_bot.application.records import (
    AuditLogRecord,
    CalendarSourceRecord,
    EventOverrideRecord,
    ExternalEventRecord,
    GuildConfigRecord,
)
from domcek_bot.config import Settings
from domcek_bot.domain.enums import (
    ArchiveState,
    AuditResult,
    DescriptionState,
    PublicationItemType,
    PublicationMode,
)
from domcek_bot.domain.errors import OptimisticLockError
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.models import (
    Base,
    ChannelArchiveRequestModel,
    ExternalEventModel,
    GuildConfigModel,
    InfoAnnouncementModel,
    PublicationItemModel,
    PublicationRunModel,
)
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


def _calendar(source_id: uuid.UUID | None = None) -> CalendarSourceRecord:
    return CalendarSourceRecord(
        id=source_id or uuid.uuid4(),
        guild_id=GUILD_ID,
        provider="google",
        external_calendar_id=f"calendar-{source_id or uuid.uuid4()}",
        display_name="Test calendar",
    )


def _event(source_id: uuid.UUID, event_id: uuid.UUID | None = None) -> ExternalEventRecord:
    identifier = event_id or uuid.uuid4()
    return ExternalEventRecord(
        id=identifier,
        calendar_source_id=source_id,
        source_key=f"source-{identifier.hex}",
        provider_event_id=f"google-{identifier.hex}",
        source_title="Test event",
        is_all_day=False,
        starts_at=NOW + timedelta(days=1),
        ends_at=NOW + timedelta(days=1, hours=1),
        source_timezone="Europe/Bratislava",
        last_synced_at=NOW,
    )


async def _seed_event(database: Database) -> tuple[CalendarSourceRecord, ExternalEventRecord]:
    source = _calendar()
    event = _event(source.id)
    uow = SqlAlchemyUnitOfWork(database)
    async with uow.transaction() as transaction:
        await transaction.guild_configs.add(GuildConfigRecord(guild_id=GUILD_ID))
        await transaction.calendar_sources.add(source)
        await transaction.external_events.add(event)
    return source, event


async def test_all_e2_tables_exist(database: Database) -> None:
    async with database.transaction() as connection:
        table_names = await connection.run_sync(lambda sync: set(inspect(sync).get_table_names()))

    assert set(Base.metadata.tables) <= table_names
    assert len(Base.metadata.tables) == 19


async def test_required_postgresql_constraints_and_indexes_exist(database: Database) -> None:
    async with database.transaction() as connection:
        catalog_rows = await connection.execute(
            text("SELECT tablename, indexname FROM pg_indexes WHERE schemaname = current_schema()")
        )
        indexes = {(row.tablename, row.indexname) for row in catalog_rows}

    required_indexes = {
        ("calendar_source", "calendar_identity"),
        ("external_event", "source_key"),
        ("external_event", "ix_external_event_source_deleted_starts_at"),
        ("external_event", "ix_external_event_source_deleted_starts_on"),
        ("event_series_override", "ix_event_series_override_lookup"),
        ("info_announcement", "ix_info_announcement_guild_active_validity"),
        ("publication_run", "guild_slot"),
        ("publication_run", "idempotency_key"),
        ("publication_run", "ix_publication_run_state_scheduled"),
        ("channel_archive_request", "uq_channel_archive_request_pending_channel"),
    }
    assert required_indexes <= indexes


async def test_change_and_audit_commit_and_rollback_together(database: Database) -> None:
    uow = SqlAlchemyUnitOfWork(database)
    audit_id = uuid.uuid4()
    audit = AuditLogRecord(
        id=audit_id,
        guild_id=GUILD_ID,
        actor_user_id=USER_ID,
        action="guild_config.created",
        object_type="guild_config",
        object_id=str(GUILD_ID),
        before_value=None,
        after_value={"timezone": "Europe/Bratislava"},
        result=AuditResult.SUCCEEDED,
        correlation_id="test-commit",
    )

    async with uow.transaction() as transaction:
        await transaction.guild_configs.add(GuildConfigRecord(guild_id=GUILD_ID))
        await transaction.audit_logs.add(audit)

    async with uow.transaction() as transaction:
        assert await transaction.guild_configs.get(GUILD_ID) is not None
        committed_audit = await transaction.audit_logs.list_for_object(
            "guild_config", str(GUILD_ID)
        )
    assert [entry.id for entry in committed_audit] == [audit_id]

    rollback_guild_id = GUILD_ID + 1
    with pytest.raises(RuntimeError, match="force rollback"):
        async with uow.transaction() as transaction:
            await transaction.guild_configs.add(GuildConfigRecord(guild_id=rollback_guild_id))
            await transaction.audit_logs.add(
                replace(
                    audit,
                    id=uuid.uuid4(),
                    guild_id=rollback_guild_id,
                    object_id=str(rollback_guild_id),
                    correlation_id="test-rollback",
                )
            )
            await transaction.audit_logs.list_for_object("guild_config", str(rollback_guild_id))
            raise RuntimeError("force rollback")

    async with uow.transaction() as transaction:
        assert await transaction.guild_configs.get(rollback_guild_id) is None
        assert (
            await transaction.audit_logs.list_for_object("guild_config", str(rollback_guild_id))
            == []
        )


async def test_optimistic_override_rejects_stale_update_and_audit(database: Database) -> None:
    _, event = await _seed_event(database)
    uow = SqlAlchemyUnitOfWork(database)
    original = EventOverrideRecord(
        external_event_id=event.id,
        public_title="Pôvodný titulok",
        description_state=DescriptionState.CUSTOM,
        public_description="Pôvodný popis",
        updated_by_user_id=USER_ID,
    )
    async with uow.transaction() as transaction:
        await transaction.event_overrides.add(original)

    async with uow.transaction() as transaction:
        first_editor = await transaction.event_overrides.get(event.id)
    async with uow.transaction() as transaction:
        second_editor = await transaction.event_overrides.get(event.id)
    assert first_editor is not None and second_editor is not None

    first_change = replace(first_editor, public_title="Prvá uložená zmena")
    async with uow.transaction() as transaction:
        version = await transaction.event_overrides.update(
            first_change, expected_version=first_editor.version
        )
        await transaction.audit_logs.add(
            AuditLogRecord(
                id=uuid.uuid4(),
                guild_id=GUILD_ID,
                actor_user_id=USER_ID,
                action="event_override.updated",
                object_type="event_override",
                object_id=str(event.id),
                before_value={"title": first_editor.public_title},
                after_value={"title": first_change.public_title},
                result=AuditResult.SUCCEEDED,
                correlation_id="first-editor",
            )
        )
    assert version == 2

    with pytest.raises(OptimisticLockError):
        async with uow.transaction() as transaction:
            await transaction.audit_logs.add(
                AuditLogRecord(
                    id=uuid.uuid4(),
                    guild_id=GUILD_ID,
                    actor_user_id=USER_ID,
                    action="event_override.updated",
                    object_type="event_override",
                    object_id=str(event.id),
                    before_value={"title": second_editor.public_title},
                    after_value={"title": "Zastaraná zmena"},
                    result=AuditResult.SUCCEEDED,
                    correlation_id="stale-editor",
                )
            )
            await transaction.event_overrides.update(
                replace(second_editor, public_title="Zastaraná zmena"),
                expected_version=second_editor.version,
            )

    async with uow.transaction() as transaction:
        current = await transaction.event_overrides.get(event.id)
        audit_entries = await transaction.audit_logs.list_for_object(
            "event_override", str(event.id)
        )
    assert current is not None
    assert current.public_title == "Prvá uložená zmena"
    assert current.version == 2
    assert [entry.correlation_id for entry in audit_entries] == ["first-editor"]


async def test_unique_source_key_and_timed_event_shape_are_enforced(database: Database) -> None:
    source, event = await _seed_event(database)

    with pytest.raises(IntegrityError):
        async with database.session() as session, session.begin():
            session.add(
                ExternalEventModel(
                    id=uuid.uuid4(),
                    calendar_source_id=source.id,
                    source_key=event.source_key,
                    provider_event_id="duplicate-provider-id",
                    is_all_day=False,
                    starts_at=NOW,
                    last_synced_at=NOW,
                )
            )

    with pytest.raises(IntegrityError):
        async with database.session() as session, session.begin():
            session.add(
                ExternalEventModel(
                    id=uuid.uuid4(),
                    calendar_source_id=source.id,
                    source_key="invalid-mixed-shape",
                    provider_event_id="invalid-mixed-shape",
                    is_all_day=False,
                    starts_at=NOW,
                    starts_on=date(2026, 8, 9),
                    last_synced_at=NOW,
                )
            )


async def test_publication_slot_idempotency_info_and_pending_archive_constraints(
    database: Database,
) -> None:
    async with database.session() as session, session.begin():
        session.add(GuildConfigModel(guild_id=GUILD_ID))

    run_id = uuid.uuid4()
    async with database.session() as session, session.begin():
        session.add(
            PublicationRunModel(
                id=run_id,
                guild_id=GUILD_ID,
                slot_key="1535774834955391047:2026-08-10T20:00:00+02:00",
                scheduled_for=NOW + timedelta(days=1),
                mode=PublicationMode.AUTOMATIC.value,
                idempotency_key="publication-key-1",
            )
        )

    with pytest.raises(IntegrityError):
        async with database.session() as session, session.begin():
            session.add(
                PublicationRunModel(
                    id=uuid.uuid4(),
                    guild_id=GUILD_ID,
                    slot_key="1535774834955391047:2026-08-10T20:00:00+02:00",
                    scheduled_for=NOW + timedelta(days=1),
                    mode=PublicationMode.MANUAL.value,
                    idempotency_key="publication-key-2",
                )
            )

    with pytest.raises(IntegrityError):
        async with database.session() as session, session.begin():
            session.add(
                PublicationRunModel(
                    id=uuid.uuid4(),
                    guild_id=GUILD_ID,
                    slot_key="1535774834955391047:2026-08-17T20:00:00+02:00",
                    scheduled_for=NOW + timedelta(days=8),
                    mode=PublicationMode.AUTOMATIC.value,
                    idempotency_key="publication-key-1",
                )
            )

    with pytest.raises(IntegrityError):
        async with database.session() as session, session.begin():
            session.add(
                InfoAnnouncementModel(
                    guild_id=GUILD_ID,
                    title="Invalid INFO",
                    description="Invalid dates",
                    valid_from=date(2026, 8, 10),
                    valid_until=date(2026, 8, 9),
                    created_by_user_id=USER_ID,
                    updated_by_user_id=USER_ID,
                )
            )

    pending_values = {
        "guild_id": GUILD_ID,
        "discord_channel_id": 1535775286135255060,
        "original_channel_name": "test-channel",
        "archive_category_id": 1535775156749369445,
        "requested_by_user_id": USER_ID,
        "reason": "Test",
        "state": ArchiveState.PENDING.value,
        "expires_at": NOW + timedelta(days=1),
    }
    async with database.session() as session, session.begin():
        session.add(ChannelArchiveRequestModel(**pending_values))

    with pytest.raises(IntegrityError):
        async with database.session() as session, session.begin():
            session.add(ChannelArchiveRequestModel(**pending_values))


async def test_soft_deleted_event_keeps_publication_snapshot(database: Database) -> None:
    _, event = await _seed_event(database)
    run_id = uuid.uuid4()
    snapshot_title = "Nemenný publikovaný titulok"
    async with database.session() as session, session.begin():
        session.add(
            PublicationRunModel(
                id=run_id,
                guild_id=GUILD_ID,
                slot_key="1535774834955391047:2026-08-17T20:00:00+02:00",
                scheduled_for=NOW + timedelta(days=8),
                mode=PublicationMode.AUTOMATIC.value,
                idempotency_key="publication-history-key",
            )
        )
        await session.flush()
        session.add(
            PublicationItemModel(
                publication_run_id=run_id,
                item_type=PublicationItemType.EXTERNAL_EVENT.value,
                position=0,
                external_event_id=event.id,
                final_title=snapshot_title,
                final_description="Publikovaný obsah",
                starts_at=event.starts_at,
                ends_at=event.ends_at,
                is_all_day=False,
            )
        )

    deleted_at = NOW + timedelta(hours=1)
    uow = SqlAlchemyUnitOfWork(database)
    async with uow.transaction() as transaction:
        assert await transaction.external_events.mark_deleted(event.id, deleted_at)

    async with database.session() as session:
        stored_event = await session.get(ExternalEventModel, event.id)
        snapshot = (
            await session.scalars(
                select(PublicationItemModel).where(
                    PublicationItemModel.publication_run_id == run_id
                )
            )
        ).one()
    assert stored_event is not None and stored_event.deleted_at == deleted_at
    assert snapshot.external_event_id == event.id
    assert snapshot.final_title == snapshot_title

    async with database.session() as session, session.begin():
        await session.execute(delete(ExternalEventModel).where(ExternalEventModel.id == event.id))
    async with database.session() as session:
        snapshot_after_physical_cleanup = await session.get(PublicationItemModel, snapshot.id)
    assert snapshot_after_physical_cleanup is not None
    assert snapshot_after_physical_cleanup.external_event_id is None
    assert snapshot_after_physical_cleanup.final_title == snapshot_title
