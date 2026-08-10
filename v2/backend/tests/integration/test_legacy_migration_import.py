from __future__ import annotations

import os
import sqlite3
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select, text

from domcek_bot.application.records import (
    CalendarSourceRecord,
    ExternalEventRecord,
    GuildConfigRecord,
)
from domcek_bot.config import Settings
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.models import (
    AuditLogModel,
    Base,
    EventOverrideModel,
    InfoAnnouncementModel,
    ManualEventModel,
    ReactionConfigChannelModel,
    ReactionConfigModel,
)
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from domcek_bot.migration.legacy import (
    LegacyMigrationError,
    build_report,
    enrich_google_matches,
    import_report,
    read_legacy,
)

pytestmark = pytest.mark.skipif(
    "TEST_DATABASE_URL" not in os.environ,
    reason="integration database not configured",
)

GUILD_ID = 1535774834955391047
ACTOR_ID = 713075588155441243


@pytest.fixture
async def database() -> AsyncIterator[Database]:
    settings = Settings(database_url=os.environ["TEST_DATABASE_URL"])
    database = Database(settings)
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    async with database.transaction() as connection:
        await connection.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))
    async with SqlAlchemyUnitOfWork(database).transaction() as repositories:
        await repositories.guild_configs.add(GuildConfigRecord(guild_id=GUILD_ID))
    try:
        yield database
    finally:
        async with database.transaction() as connection:
            await connection.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))
        await database.close()


def _legacy_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE announcements (
            id INTEGER PRIMARY KEY, typ TEXT NOT NULL, title TEXT NOT NULL,
            description TEXT NOT NULL, datetime TEXT, day TEXT, link TEXT,
            image TEXT, visible_from TEXT, visible_to TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE bot_settings (key TEXT PRIMARY KEY, value TEXT);
        INSERT INTO announcements VALUES
          (1, 'event', 'Minulá udalosť', 'Text', '12.12. // 19:00', 'piatok', NULL,
           NULL, '10.12.2025', '12.12.2025', '2025-12-01T12:00:00'),
          (2, 'info', 'Staré INFO', 'Popis', NULL, NULL, NULL,
           'https://example.org/image.png', '10.12.2025', '23.12.2025',
           '2025-12-01T12:00:00');
        INSERT INTO bot_settings VALUES
          ('publish_schedule', '{"day":"Friday","time":"09:00"}'),
          ('schedule_active', 'true'),
          ('reaction_emoji', '"<:seen:1448575722774855681>"'),
          ('auto_react_channels', '[1448319121132490894]');
        """
    )
    connection.commit()
    connection.close()


async def test_import_is_idempotent_and_preserves_expired_history(
    database: Database, tmp_path: Path
) -> None:
    source = tmp_path / "legacy.db"
    _legacy_database(source)
    report = build_report(source, as_of=date(2026, 8, 10))
    announcements, _, _ = read_legacy(source)

    first = await import_report(
        report,
        announcements,
        target_url=os.environ["TEST_DATABASE_URL"],
        guild_id=GUILD_ID,
        actor_user_id=ACTOR_ID,
        approve_unmatched=True,
        approved_matches={},
        apply_settings=True,
    )
    second = await import_report(
        report,
        announcements,
        target_url=os.environ["TEST_DATABASE_URL"],
        guild_id=GUILD_ID,
        actor_user_id=ACTOR_ID,
        approve_unmatched=True,
        approved_matches={},
        apply_settings=True,
    )

    assert first.result == {
        "inserted_info": 1,
        "inserted_manual": 1,
        "inserted_overrides": 0,
        "skipped_existing": 0,
        "needs_review": 0,
        "settings_changed": 3,
    }
    assert second.result == {
        "inserted_info": 0,
        "inserted_manual": 0,
        "inserted_overrides": 0,
        "skipped_existing": 2,
        "needs_review": 0,
        "settings_changed": 0,
    }
    async with database.transaction() as connection:
        assert await connection.scalar(select(func.count()).select_from(InfoAnnouncementModel)) == 1
        assert await connection.scalar(select(func.count()).select_from(ManualEventModel)) == 1
        assert await connection.scalar(select(func.count()).select_from(AuditLogModel)) == 3
        info = (
            await connection.execute(
                select(InfoAnnouncementModel.active, InfoAnnouncementModel.deleted_at)
            )
        ).one()
        event = (
            await connection.execute(select(ManualEventModel.active, ManualEventModel.deleted_at))
        ).one()
        reaction_emoji_id = await connection.scalar(select(ReactionConfigModel.seen_emoji_id))
        channel_id = await connection.scalar(select(ReactionConfigChannelModel.discord_channel_id))
    assert info.active is False and info.deleted_at is not None
    assert event.active is False and event.deleted_at is not None
    assert reaction_emoji_id == 1448575722774855681
    assert channel_id == 1448319121132490894


async def test_future_event_match_requires_explicit_approval(
    database: Database, tmp_path: Path
) -> None:
    source = tmp_path / "future.db"
    connection = sqlite3.connect(source)
    connection.executescript(
        """
        CREATE TABLE announcements (
            id INTEGER PRIMARY KEY, typ TEXT NOT NULL, title TEXT NOT NULL,
            description TEXT NOT NULL, datetime TEXT, day TEXT, link TEXT,
            image TEXT, visible_from TEXT, visible_to TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE bot_settings (key TEXT PRIMARY KEY, value TEXT);
        INSERT INTO announcements VALUES
          (7, 'event', 'Budúce stretnutie', 'Legacy redakčný text',
           '15.08. // 10:00', 'sobota', NULL, NULL, '10.08.2026', '16.08.2026',
           '2026-08-10T10:00:00');
        """
    )
    connection.commit()
    connection.close()
    source_id = uuid.uuid4()
    event_id = uuid.uuid4()
    async with SqlAlchemyUnitOfWork(database).transaction() as repositories:
        await repositories.calendar_sources.add(
            CalendarSourceRecord(
                id=source_id,
                guild_id=GUILD_ID,
                provider="google",
                external_calendar_id="future@example.test",
                display_name="Future",
            )
        )
        await repositories.external_events.add(
            ExternalEventRecord(
                id=event_id,
                calendar_source_id=source_id,
                source_key="future-7",
                provider_event_id="provider-7",
                source_title="Budúce stretnutie",
                source_description="Google text",
                is_all_day=False,
                starts_at=datetime(2026, 8, 15, 8, tzinfo=UTC),
                ends_at=datetime(2026, 8, 15, 9, tzinfo=UTC),
                last_synced_at=datetime(2026, 8, 10, 8, tzinfo=UTC),
            )
        )
    report = await enrich_google_matches(
        build_report(source, as_of=date(2026, 8, 10)),
        target_url=os.environ["TEST_DATABASE_URL"],
        guild_id=GUILD_ID,
    )
    announcements, _, _ = read_legacy(source)
    assert report.items[0].action == "review_google_match"
    assert report.items[0].match_candidates == (str(event_id),)

    skipped = await import_report(
        report,
        announcements,
        target_url=os.environ["TEST_DATABASE_URL"],
        guild_id=GUILD_ID,
        actor_user_id=ACTOR_ID,
        approve_unmatched=True,
        approved_matches={},
        apply_settings=False,
    )
    assert skipped.result is not None and skipped.result["needs_review"] == 1
    imported = await import_report(
        report,
        announcements,
        target_url=os.environ["TEST_DATABASE_URL"],
        guild_id=GUILD_ID,
        actor_user_id=ACTOR_ID,
        approve_unmatched=False,
        approved_matches={7: str(event_id)},
        apply_settings=False,
    )
    assert imported.result is not None and imported.result["inserted_overrides"] == 1
    async with database.transaction() as db_connection:
        description = await db_connection.scalar(
            select(EventOverrideModel.public_description).where(
                EventOverrideModel.external_event_id == event_id
            )
        )
        audit_action = await db_connection.scalar(
            select(AuditLogModel.action).where(AuditLogModel.object_id == str(event_id))
        )
    assert description == "Legacy redakčný text"
    assert audit_action == "legacy_event_override_imported"


async def test_all_day_match_is_detected_and_identical_content_creates_no_override(
    database: Database, tmp_path: Path
) -> None:
    source = tmp_path / "all-day.db"
    connection = sqlite3.connect(source)
    connection.executescript(
        """
        CREATE TABLE announcements (
            id INTEGER PRIMARY KEY, typ TEXT NOT NULL, title TEXT NOT NULL,
            description TEXT NOT NULL, datetime TEXT, day TEXT, link TEXT,
            image TEXT, visible_from TEXT, visible_to TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE bot_settings (key TEXT PRIMARY KEY, value TEXT);
        INSERT INTO announcements VALUES
          (8, 'event', 'Celodenná akcia', 'Rovnaký text',
           '16.08.', 'nedeľa', NULL, NULL, '10.08.2026', '16.08.2026',
           '2026-08-10T10:00:00');
        """
    )
    connection.commit()
    connection.close()
    source_id = uuid.uuid4()
    event_id = uuid.uuid4()
    async with SqlAlchemyUnitOfWork(database).transaction() as repositories:
        await repositories.calendar_sources.add(
            CalendarSourceRecord(
                id=source_id,
                guild_id=GUILD_ID,
                provider="google",
                external_calendar_id="all-day@example.test",
                display_name="All day",
            )
        )
        await repositories.external_events.add(
            ExternalEventRecord(
                id=event_id,
                calendar_source_id=source_id,
                source_key="all-day-8",
                provider_event_id="provider-8",
                source_title="Celodenná akcia",
                source_description="Rovnaký text",
                is_all_day=True,
                starts_on=date(2026, 8, 16),
                ends_on=date(2026, 8, 17),
                last_synced_at=datetime(2026, 8, 10, 8, tzinfo=UTC),
            )
        )
    report = await enrich_google_matches(
        build_report(source, as_of=date(2026, 8, 10)),
        target_url=os.environ["TEST_DATABASE_URL"],
        guild_id=GUILD_ID,
    )
    announcements, _, _ = read_legacy(source)
    assert report.items[0].action == "review_google_match"
    assert report.items[0].match_candidates == (str(event_id),)

    imported = await import_report(
        report,
        announcements,
        target_url=os.environ["TEST_DATABASE_URL"],
        guild_id=GUILD_ID,
        actor_user_id=ACTOR_ID,
        approve_unmatched=False,
        approved_matches={8: str(event_id)},
        apply_settings=False,
    )
    assert imported.result is not None
    assert imported.result["inserted_overrides"] == 0
    assert imported.result["skipped_existing"] == 1
    async with database.transaction() as db_connection:
        assert await db_connection.scalar(select(func.count()).select_from(EventOverrideModel)) == 0
        assert await db_connection.scalar(select(func.count()).select_from(AuditLogModel)) == 0


async def test_invalid_legacy_reaction_setting_is_rejected_before_write(
    database: Database, tmp_path: Path
) -> None:
    source = tmp_path / "bad-reaction.db"
    _legacy_database(source)
    connection = sqlite3.connect(source)
    connection.execute(
        "UPDATE bot_settings SET value = ? WHERE key = 'reaction_emoji'",
        ('"not emoji"',),
    )
    connection.commit()
    connection.close()
    report = build_report(source, as_of=date(2026, 8, 10))
    announcements, _, _ = read_legacy(source)

    with pytest.raises(LegacyMigrationError, match="Legacy nastavenie reakcií nie je platné"):
        await import_report(
            report,
            announcements,
            target_url=os.environ["TEST_DATABASE_URL"],
            guild_id=GUILD_ID,
            actor_user_id=ACTOR_ID,
            approve_unmatched=True,
            approved_matches={},
            apply_settings=True,
        )

    async with database.transaction() as db_connection:
        assert (
            await db_connection.scalar(select(func.count()).select_from(ReactionConfigModel)) == 0
        )
        assert await db_connection.scalar(select(func.count()).select_from(AuditLogModel)) == 0
