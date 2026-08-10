from __future__ import annotations

import pytest

from domcek_bot.config import ConfigurationError, Settings
from domcek_bot.infrastructure.calendar_factory import build_google_calendar_client
from domcek_bot.infrastructure.google_calendar import GOOGLE_CALENDAR_READONLY_SCOPE


def test_calendar_integration_uses_only_readonly_scope() -> None:
    assert GOOGLE_CALENDAR_READONLY_SCOPE == ("https://www.googleapis.com/auth/calendar.readonly")


def test_calendar_factory_requires_server_side_credential_path() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://localhost/domcek",
        google_service_account_file=None,
    )
    with pytest.raises(ConfigurationError, match="GOOGLE_SERVICE_ACCOUNT_FILE"):
        build_google_calendar_client(settings)
