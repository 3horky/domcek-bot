from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import text

from domcek_bot.application.publication.models import DraftItemKind, ValueOrigin
from domcek_bot.application.publication.service import PublicationDraftService
from domcek_bot.config import Settings
from domcek_bot.domain.enums import (
    DescriptionState,
    InclusionDecision,
    PublicationMode,
    PublicationState,
)
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.models import (
    Base,
    CalendarSourceModel,
    EventOverrideModel,
    EventSeriesOverrideModel,
    ExternalEventModel,
    GuildConfigModel,
    InfoAnnouncementModel,
    ManualEventModel,
    PublicationRunModel,
)
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.skipif(
    "TEST_DATABASE_URL" not in os.environ,
    reason="integration database not configured",
)

GUILD_ID = 1535774834955391047
USER_ID = 1535771583841439765
REFERENCE = datetime(2026, 8, 9, 18, 0, tzinfo=UTC)
FIRST_SLOT_KEY = f"{GUILD_ID}:2026-08-10T20:00:Europe/Bratislava"


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


async def test_service_composes_one_transactional_persistence_snapshot(
    database: Database,
) -> None:
    source_id = uuid.uuid4()
    event_id = uuid.uuid4()
    series_id = uuid.uuid4()
    manual_id = uuid.uuid4()
    info_id = uuid.uuid4()
    event_start = datetime(2026, 8, 18, 8, 0, tzinfo=UTC)

    async with database.session() as session, session.begin():
        session.add(
            GuildConfigModel(
                guild_id=GUILD_ID,
                publish_google_descriptions=False,
                closing_message="Majte sa pekne.",
            )
        )
        await session.flush()
        session.add(
            CalendarSourceModel(
                id=source_id,
                guild_id=GUILD_ID,
                provider="google",
                external_calendar_id="calendar@example.test",
                display_name="Test calendar",
                priority=10,
            )
        )
        await session.flush()
        session.add(
            ExternalEventModel(
                id=event_id,
                calendar_source_id=source_id,
                source_key="stable-source-key",
                provider_event_id="google-event",
                occurrence_id="google-instance",
                series_key="stable-series-key",
                original_start_key=event_start.isoformat(),
                source_title="Google titulok",
                source_description="<p>Google popis</p>",
                is_all_day=False,
                starts_at=event_start,
                ends_at=event_start + timedelta(hours=1),
                last_synced_at=REFERENCE,
            )
        )
        await session.flush()
        session.add(
            EventSeriesOverrideModel(
                id=series_id,
                calendar_source_id=source_id,
                series_key="stable-series-key",
                effective_from_key=event_start.isoformat(),
                effective_all_day=False,
                effective_from_at=event_start,
                public_title="Sériový titulok",
                description_state=DescriptionState.CUSTOM.value,
                public_description="Sériový popis",
                updated_by_user_id=USER_ID,
            )
        )
        session.add(
            EventOverrideModel(
                external_event_id=event_id,
                public_title="Výskytový titulok",
                description_state=DescriptionState.INHERIT.value,
                inclusion_decision=InclusionDecision.AUTO.value,
                updated_by_user_id=USER_ID,
            )
        )
        session.add(
            ManualEventModel(
                id=manual_id,
                guild_id=GUILD_ID,
                title="Manuálna udalosť",
                description="Manuálny popis",
                is_all_day=False,
                starts_at=event_start + timedelta(hours=2),
                ends_at=event_start + timedelta(hours=3),
                created_by_user_id=USER_ID,
                updated_by_user_id=USER_ID,
            )
        )
        session.add(
            InfoAnnouncementModel(
                id=info_id,
                guild_id=GUILD_ID,
                title="INFO oznam",
                description="Dôležité informácie",
                valid_from=date(2026, 8, 17),
                valid_until=date(2026, 8, 17),
                image_url="https://example.test/info.png",
                created_by_user_id=USER_ID,
                updated_by_user_id=USER_ID,
            )
        )
        session.add(
            PublicationRunModel(
                id=uuid.uuid4(),
                guild_id=GUILD_ID,
                slot_key=FIRST_SLOT_KEY,
                scheduled_for=datetime(2026, 8, 10, 18, 0, tzinfo=UTC),
                mode=PublicationMode.MANUAL.value,
                state=PublicationState.SUCCEEDED_MANUAL.value,
                idempotency_key="completed-first-slot",
            )
        )
        session.add(
            PublicationRunModel(
                id=uuid.uuid4(),
                guild_id=GUILD_ID,
                slot_key=f"{GUILD_ID}:2026-08-17T20:00:Europe/Bratislava",
                scheduled_for=datetime(2026, 8, 17, 18, 0, tzinfo=UTC),
                mode=PublicationMode.AUTOMATIC.value,
                state=PublicationState.FAILED.value,
                idempotency_key="failed-next-slot",
            )
        )

    draft = await PublicationDraftService(SqlAlchemyUnitOfWork(database)).compose_next(
        GUILD_ID,
        reference_time=REFERENCE,
        intro_text="Najbližšie udalosti",
    )

    assert draft.slot_key == f"{GUILD_ID}:2026-08-17T20:00:Europe/Bratislava"
    assert draft.window_starts_at.date() == date(2026, 8, 17)
    assert [item.kind for item in draft.public_items] == [
        DraftItemKind.INFO,
        DraftItemKind.EXTERNAL_EVENT,
        DraftItemKind.MANUAL_EVENT,
    ]
    external = draft.public_items[1]
    assert external.title == "Výskytový titulok"
    assert external.title_origin is ValueOrigin.INSTANCE
    assert external.description == "Sériový popis"
    assert external.description_origin is ValueOrigin.SERIES
    assert len(draft.messages) == 1
    assert draft.messages[0].content == ("@everyone\nNajbližšie udalosti\n\nMajte sa pekne.")
    assert draft.messages[0].allowed_mentions == ("everyone",)
    assert draft.messages[-1].seen_target
