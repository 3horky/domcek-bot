from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import func, select, text, update

from domcek_bot.application.auth.authorization import (
    AppRole,
    AuthorizationDenied,
    Principal,
)
from domcek_bot.application.publication.service import PublicationDraftService
from domcek_bot.application.publication.shadow import ShadowPublicationService
from domcek_bot.application.records import CalendarSourceRecord
from domcek_bot.config import AppEnvironment, Settings
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.models import (
    Base,
    GuildConfigModel,
    ManualEventModel,
    PublicationRunModel,
)
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.skipif(
    "TEST_DATABASE_URL" not in os.environ,
    reason="integration database not configured",
)

GUILD_ID = 1535774834955391047
OTHER_GUILD_ID = 1535774834955391999
FIRST_OBSERVATION = datetime(2026, 8, 9, 18, 0, tzinfo=UTC)


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


async def test_shadow_capture_is_durable_updated_and_never_materializes_a_live_run(
    database: Database,
) -> None:
    event_id = uuid.uuid4()
    async with database.session() as session, session.begin():
        session.add(GuildConfigModel(guild_id=GUILD_ID))
        session.add(GuildConfigModel(guild_id=OTHER_GUILD_ID))
        session.add(
            ManualEventModel(
                id=event_id,
                guild_id=GUILD_ID,
                title="Prvá verzia",
                is_all_day=True,
                starts_on=date(2026, 8, 11),
                ends_on=date(2026, 8, 12),
                timezone="Europe/Bratislava",
                created_by_user_id=42,
                updated_by_user_id=42,
            )
        )

    uow = SqlAlchemyUnitOfWork(database)
    source_id = uuid.uuid4()
    async with uow.transaction() as repositories:
        await repositories.calendar_sources.add(
            CalendarSourceRecord(
                id=source_id,
                guild_id=GUILD_ID,
                provider="google",
                external_calendar_id="shadow@example.test",
                display_name="Shadow",
            )
        )
        await repositories.calendar_sources.mark_sync_succeeded(
            source_id,
            sync_token="token",
            sync_token_query_key="query",
            completed_at=FIRST_OBSERVATION,
            was_full_sync=True,
        )
    service = ShadowPublicationService(uow, PublicationDraftService(uow))
    first = await service.capture_next(
        GUILD_ID,
        observed_at=FIRST_OBSERVATION,
        calendar_sync_succeeded=True,
    )

    async with database.session() as session, session.begin():
        await session.execute(
            update(ManualEventModel)
            .where(ManualEventModel.id == event_id)
            .values(title="Druhá verzia")
        )
    second_observation = FIRST_OBSERVATION + timedelta(hours=1)
    second = await service.capture_next(
        GUILD_ID,
        observed_at=second_observation,
        calendar_sync_succeeded=False,
    )
    foreign = await service.capture_next(
        OTHER_GUILD_ID,
        observed_at=FIRST_OBSERVATION,
        calendar_sync_succeeded=True,
    )

    assert first.id == second.id
    assert first.slot_key == second.slot_key
    assert first.draft_sha256 != second.draft_sha256
    assert second.first_observed_at == FIRST_OBSERVATION
    assert second.last_observed_at == second_observation
    assert second.observation_count == 2
    assert second.item_count == 1
    assert second.message_count == 1
    assert second.draft_json["public_items"][0]["title"] == "Druhá verzia"
    assert first.calendar_sync_valid is True
    assert second.calendar_sync_valid is False
    assert second.calendar_sync_evidence["sync_attempt_succeeded"] is False
    assert second.calendar_sync_evidence["active_source_count"] == 1
    assert foreign.calendar_sync_valid is False

    own = await service.list(_principal(AppRole.TEAM_MOD))
    assert [capture.id for capture in own] == [second.id]
    assert foreign.id not in {capture.id for capture in own}
    with pytest.raises(AuthorizationDenied):
        await service.list(_principal(None))

    async with database.session() as session:
        live_run_count = await session.scalar(select(func.count()).select_from(PublicationRunModel))
    assert live_run_count == 0
