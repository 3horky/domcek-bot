from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from domcek_bot.application.auth.authorization import AppRole, AuthorizationDenied, Principal
from domcek_bot.application.editor.events import (
    EditorialConflict,
    EditorialObjectNotFound,
    EditorialValidationError,
    EventEditorialService,
    SeriesEditorialConflict,
    UpdateEventOverride,
    UpdateSeriesOverride,
)
from domcek_bot.application.records import (
    CalendarSourceRecord,
    ExternalEventRecord,
    GuildConfigRecord,
)
from domcek_bot.config import Settings
from domcek_bot.domain.enums import (
    AuditResult,
    DescriptionState,
    InclusionDecision,
)
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.models import Base
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.skipif(
    "TEST_DATABASE_URL" not in os.environ,
    reason="integration database not configured",
)

GUILD_ID = 1535774834955391047
OTHER_GUILD_ID = GUILD_ID + 1
USER_ID = 1535771583841439765
NOW = datetime(2026, 8, 9, 10, tzinfo=UTC)


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


def _principal(role: AppRole, *, guild_id: int = GUILD_ID) -> Principal:
    return Principal(
        guild_id=guild_id,
        user_id=USER_ID,
        username="editor",
        display_name="Editor",
        avatar_url=None,
        discord_role_ids=frozenset(),
        app_roles=frozenset({role}),
    )


async def _seed(
    database: Database,
    *,
    recurring: bool = False,
) -> tuple[SqlAlchemyUnitOfWork, ExternalEventRecord]:
    unit_of_work = SqlAlchemyUnitOfWork(database)
    source = CalendarSourceRecord(
        id=uuid.uuid4(),
        guild_id=GUILD_ID,
        provider="google",
        external_calendar_id="editor@example.test",
        display_name="Editor calendar",
    )
    event = ExternalEventRecord(
        id=uuid.uuid4(),
        calendar_source_id=source.id,
        source_key=f"source-{uuid.uuid4().hex}",
        provider_event_id="provider-editor",
        occurrence_id="provider-editor-occurrence" if recurring else None,
        series_key="provider-editor-series" if recurring else None,
        original_start_key=(NOW + timedelta(days=1)).isoformat() if recurring else None,
        source_title="Google title",
        is_all_day=False,
        starts_at=NOW + timedelta(days=1),
        ends_at=NOW + timedelta(days=1, hours=1),
        last_synced_at=NOW,
    )
    async with unit_of_work.transaction() as repositories:
        await repositories.guild_configs.add(GuildConfigRecord(guild_id=GUILD_ID))
        await repositories.calendar_sources.add(source)
        await repositories.external_events.add(event)
    return unit_of_work, event


async def test_admin_and_team_mod_updates_are_versioned_and_audited(
    database: Database,
) -> None:
    unit_of_work, event = await _seed(database)
    service = EventEditorialService(unit_of_work)

    created = await service.update_instance(
        UpdateEventOverride(
            event_id=event.id,
            expected_version=0,
            public_title="Redakčný titulok",
            description_state=DescriptionState.CUSTOM,
            public_description="Redakčný popis",
            inclusion_decision=InclusionDecision.FORCE_INCLUDE,
        ),
        principal=_principal(AppRole.ADMIN),
        correlation_id="admin-create",
        now=NOW,
    )
    assert created.version == 1
    assert created.inclusion_decision is InclusionDecision.FORCE_INCLUDE

    updated = await service.update_instance(
        UpdateEventOverride(
            event_id=event.id,
            expected_version=1,
            public_title="Team Mod titulok",
            description_state=DescriptionState.INTENTIONALLY_EMPTY,
            public_description=None,
        ),
        principal=_principal(AppRole.TEAM_MOD),
        correlation_id="team-update",
        now=NOW + timedelta(minutes=1),
    )
    assert updated.version == 2
    assert updated.inclusion_decision is InclusionDecision.FORCE_INCLUDE
    assert updated.updated_by_user_id == USER_ID

    async with unit_of_work.transaction() as repositories:
        audit = await repositories.audit_logs.list_for_object("event_override", str(event.id))
    assert [entry.correlation_id for entry in audit] == ["admin-create", "team-update"]
    assert all(entry.result is AuditResult.SUCCEEDED for entry in audit)


async def test_denied_inclusion_is_audited_without_mutation(database: Database) -> None:
    unit_of_work, event = await _seed(database)
    service = EventEditorialService(unit_of_work)

    with pytest.raises(AuthorizationDenied):
        await service.update_instance(
            UpdateEventOverride(
                event_id=event.id,
                expected_version=0,
                public_title="Team title",
                description_state=DescriptionState.INHERIT,
                public_description=None,
                inclusion_decision=InclusionDecision.FORCE_EXCLUDE,
            ),
            principal=_principal(AppRole.TEAM_MOD),
            correlation_id="denied-force",
            now=NOW,
        )

    async with unit_of_work.transaction() as repositories:
        assert await repositories.event_overrides.get(event.id) is None
        audit = await repositories.audit_logs.list_for_object("event_override", str(event.id))
    assert len(audit) == 1
    assert audit[0].result is AuditResult.FAILED
    assert audit[0].after_value is None


async def test_stale_and_cross_guild_updates_do_not_overwrite(database: Database) -> None:
    unit_of_work, event = await _seed(database)
    service = EventEditorialService(unit_of_work)
    command = UpdateEventOverride(
        event_id=event.id,
        expected_version=0,
        public_title=None,
        description_state=DescriptionState.INHERIT,
        public_description=None,
    )
    await service.update_instance(
        command,
        principal=_principal(AppRole.ADMIN),
        correlation_id="first",
        now=NOW,
    )

    with pytest.raises(EditorialConflict) as conflict:
        await service.update_instance(
            command,
            principal=_principal(AppRole.ADMIN),
            correlation_id="stale",
            now=NOW,
        )
    assert conflict.value.current is not None
    assert conflict.value.current.version == 1

    with pytest.raises(EditorialObjectNotFound):
        await service.update_instance(
            UpdateEventOverride(
                event_id=event.id,
                expected_version=1,
                public_title="Cudzí zásah",
                description_state=DescriptionState.INHERIT,
                public_description=None,
            ),
            principal=_principal(AppRole.ADMIN, guild_id=OTHER_GUILD_ID),
            correlation_id="cross-guild",
            now=NOW,
        )


async def test_series_updates_apply_from_occurrence_and_are_versioned(
    database: Database,
) -> None:
    unit_of_work, event = await _seed(database, recurring=True)
    service = EventEditorialService(unit_of_work)

    created = await service.update_series(
        UpdateSeriesOverride(
            event_id=event.id,
            expected_version=0,
            public_title="Názov od tohto výskytu",
            description_state=DescriptionState.CUSTOM,
            public_description="Popis série",
        ),
        principal=_principal(AppRole.TEAM_MOD),
        correlation_id="series-create",
        now=NOW,
    )
    assert created.version == 1
    assert created.series_key == event.series_key
    assert created.effective_from_key == event.original_start_key
    assert created.effective_from_at == NOW + timedelta(days=1)
    assert created.effective_from_date is None

    updated = await service.update_series(
        UpdateSeriesOverride(
            event_id=event.id,
            expected_version=1,
            public_title="Nový názov série",
            description_state=DescriptionState.INTENTIONALLY_EMPTY,
            public_description=None,
        ),
        principal=_principal(AppRole.ADMIN),
        correlation_id="series-update",
        now=NOW + timedelta(minutes=1),
    )
    assert updated.id == created.id
    assert updated.version == 2
    assert updated.public_title == "Nový názov série"

    with pytest.raises(SeriesEditorialConflict) as conflict:
        await service.update_series(
            UpdateSeriesOverride(
                event_id=event.id,
                expected_version=1,
                public_title="Zastaraný názov",
                description_state=DescriptionState.INHERIT,
                public_description=None,
            ),
            principal=_principal(AppRole.ADMIN),
            correlation_id="series-stale",
            now=NOW + timedelta(minutes=2),
        )
    assert conflict.value.current is not None
    assert conflict.value.current.version == 2

    async with unit_of_work.transaction() as repositories:
        audit = await repositories.audit_logs.list_for_object(
            "event_series_override", str(created.id)
        )
    assert [entry.correlation_id for entry in audit] == [
        "series-create",
        "series-update",
    ]


async def test_series_update_rejects_non_recurring_and_cross_guild_events(
    database: Database,
) -> None:
    unit_of_work, event = await _seed(database)
    service = EventEditorialService(unit_of_work)
    command = UpdateSeriesOverride(
        event_id=event.id,
        expected_version=0,
        public_title=None,
        description_state=DescriptionState.INHERIT,
        public_description=None,
    )

    with pytest.raises(EditorialValidationError):
        await service.update_series(
            command,
            principal=_principal(AppRole.ADMIN),
            correlation_id="not-recurring",
            now=NOW,
        )

    with pytest.raises(EditorialObjectNotFound):
        await service.update_series(
            command,
            principal=_principal(AppRole.ADMIN, guild_id=OTHER_GUILD_ID),
            correlation_id="series-cross-guild",
            now=NOW,
        )
