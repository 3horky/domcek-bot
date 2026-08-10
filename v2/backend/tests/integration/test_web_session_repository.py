from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from domcek_bot.application.auth.session import InvalidSession, SessionService
from domcek_bot.application.records import GuildConfigRecord
from domcek_bot.config import Settings
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.models import Base
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.skipif(
    "TEST_DATABASE_URL" not in os.environ,
    reason="integration database not configured",
)

GUILD_ID = 1535774834955391047
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


async def test_session_is_persisted_touched_expired_and_revoked(database: Database) -> None:
    unit_of_work = SqlAlchemyUnitOfWork(database)
    async with unit_of_work.transaction() as repositories:
        await repositories.guild_configs.add(GuildConfigRecord(guild_id=GUILD_ID))
    sessions = SessionService(
        unit_of_work,
        secret="s" * 32,
        lifetime=timedelta(hours=1),
    )

    issued = await sessions.create(guild_id=GUILD_ID, user_id=USER_ID, now=NOW)
    loaded = await sessions.authenticate(issued.session_token, now=NOW + timedelta(minutes=5))

    assert loaded.discord_user_id == USER_ID
    async with unit_of_work.transaction() as repositories:
        touched = await repositories.web_sessions.get_active_by_token_hash(
            issued.record.session_token_hash,
            now=NOW + timedelta(minutes=5),
        )
    assert touched is not None
    assert touched.last_seen_at == NOW + timedelta(minutes=5)

    with pytest.raises(InvalidSession, match="expired"):
        await sessions.authenticate(issued.session_token, now=NOW + timedelta(hours=1))
    await sessions.revoke(loaded, now=NOW + timedelta(minutes=6))
    with pytest.raises(InvalidSession):
        await sessions.authenticate(issued.session_token, now=NOW + timedelta(minutes=7))
