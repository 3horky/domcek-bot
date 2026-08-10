from __future__ import annotations

import os

import pytest

from domcek_bot.config import Settings
from domcek_bot.infrastructure.database import Database


@pytest.mark.skipif(
    "TEST_DATABASE_URL" not in os.environ, reason="integration database not configured"
)
async def test_postgresql_ping_and_transaction() -> None:
    settings = Settings(database_url=os.environ["TEST_DATABASE_URL"])
    database = Database(settings)
    try:
        await database.ping()
        async with database.transaction() as connection:
            result = await connection.exec_driver_sql("SELECT 42")
            assert result.scalar_one() == 42
    finally:
        await database.close()
