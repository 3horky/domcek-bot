from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from domcek_bot.config import (
    AppEnvironment,
    ConfigurationError,
    ProcessKind,
    PublicationExecutionMode,
    Settings,
)


def test_database_url_must_use_asyncpg() -> None:
    with pytest.raises(ValidationError, match=r"postgresql\+asyncpg"):
        Settings(database_url="postgresql://localhost/domcek")


def test_api_requires_session_secret() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://localhost/domcek",
        session_secret=None,
        session_secret_file=None,
    )
    with pytest.raises(ConfigurationError, match="SESSION_SECRET"):
        settings.validate_for(ProcessKind.API)


def test_bot_requires_discord_identity() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://localhost/domcek",
        discord_bot_token=SecretStr("valid-for-configuration-test"),
        discord_application_id=None,
        discord_guild_id=None,
    )
    with pytest.raises(ConfigurationError, match="DISCORD_APPLICATION_ID"):
        settings.validate_for(ProcessKind.BOT)


def test_secret_can_be_loaded_from_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    secret_file = tmp_path / "session"
    secret_file.write_text("x" * 48, encoding="utf-8")
    settings = Settings(
        database_url="postgresql+asyncpg://localhost/domcek",
        session_secret_file=secret_file,
    )
    assert settings.session_secret_value() == "x" * 48


def test_calendar_warning_age_must_be_lower_than_unsafe_age() -> None:
    with pytest.raises(ValidationError, match="CALENDAR_STALE_WARNING_MINUTES"):
        Settings(
            database_url="postgresql+asyncpg://localhost/domcek",
            calendar_stale_warning_minutes=360,
            calendar_max_safe_age_minutes=360,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("allowed_origins", "*"),
        ("allowed_origins", "https://example.test/path"),
        ("frontend_base_url", "https://example.test/admin"),
        ("discord_oauth_redirect_uri", "https://example.test/callback?next=evil"),
    ],
)
def test_web_urls_are_exact_origins_and_callback(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate(
            {"database_url": "postgresql+asyncpg://localhost/domcek", field: value}
        )


def test_production_web_urls_require_https() -> None:
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings(
            app_env=AppEnvironment.PRODUCTION,
            database_url="postgresql+asyncpg://localhost/domcek",
            frontend_base_url="http://example.test",
            discord_oauth_redirect_uri="http://example.test/api/v1/auth/discord/callback",
            allowed_origins="http://example.test",
        )


def test_manual_publication_is_enabled_only_by_live_or_explicit_staging_shadow() -> None:
    database_url = "postgresql+asyncpg://localhost/domcek"
    paused = Settings(database_url=database_url)
    shadow = Settings(
        database_url=database_url,
        publication_execution_mode=PublicationExecutionMode.SHADOW,
    )
    live = Settings(
        database_url=database_url,
        publication_execution_mode=PublicationExecutionMode.LIVE,
    )
    staging_shadow = Settings(
        database_url=database_url,
        app_env=AppEnvironment.STAGING,
        frontend_base_url="https://staging.example.test",
        discord_oauth_redirect_uri="https://staging.example.test/api/v1/auth/discord/callback",
        public_media_base_url="https://staging.example.test",
        allowed_origins="https://staging.example.test",
        publication_execution_mode=PublicationExecutionMode.SHADOW,
        allow_manual_publication_in_shadow=True,
    )

    assert not paused.manual_publication_enabled
    assert not shadow.manual_publication_enabled
    assert live.manual_publication_enabled
    assert staging_shadow.manual_publication_enabled


@pytest.mark.parametrize("environment", [AppEnvironment.LOCAL, AppEnvironment.PRODUCTION])
def test_manual_shadow_opt_in_is_rejected_outside_staging(
    environment: AppEnvironment,
) -> None:
    urls = (
        {
            "frontend_base_url": "https://carlo.example.test",
            "discord_oauth_redirect_uri": "https://carlo.example.test/api/v1/auth/discord/callback",
            "public_media_base_url": "https://carlo.example.test",
            "allowed_origins": "https://carlo.example.test",
        }
        if environment is AppEnvironment.PRODUCTION
        else {}
    )
    with pytest.raises(ValidationError, match="ALLOW_MANUAL_PUBLICATION_IN_SHADOW"):
        Settings.model_validate(
            {
                "database_url": "postgresql+asyncpg://localhost/domcek",
                "app_env": environment,
                "publication_execution_mode": PublicationExecutionMode.SHADOW,
                "allow_manual_publication_in_shadow": True,
                **urls,
            }
        )
