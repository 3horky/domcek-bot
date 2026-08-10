from __future__ import annotations

import pytest
from pydantic import SecretStr

from domcek_bot.config import AppEnvironment, Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env=AppEnvironment.TEST,
        database_url="postgresql+asyncpg://domcek:password@localhost:5432/domcek_test",
        session_secret=SecretStr("test-session-secret-with-at-least-32-characters"),
        log_format="console",
    )
