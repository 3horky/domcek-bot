from __future__ import annotations

import os

import pytest
from pydantic import SecretStr
from sqlalchemy.engine import make_url

from domcek_bot.config import AppEnvironment, Settings


def pytest_sessionstart(session: pytest.Session) -> None:
    del session
    value = os.environ.get("TEST_DATABASE_URL")
    if value is None:
        return
    database_name = make_url(value).database or ""
    if not database_name.endswith("_test"):
        raise RuntimeError(
            "pytest refuses TEST_DATABASE_URL unless the database name ends with _test"
        )


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env=AppEnvironment.TEST,
        database_url="postgresql+asyncpg://domcek:password@localhost:5432/domcek_test",
        session_secret=SecretStr("test-session-secret-with-at-least-32-characters"),
        log_format="console",
    )
