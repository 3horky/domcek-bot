"""Typed bootstrap configuration shared by every backend process."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class ProcessKind(StrEnum):
    API = "api"
    BOT = "bot"
    WORKER = "worker"
    MIGRATION = "migration"


class PublicationExecutionMode(StrEnum):
    PAUSED = "paused"
    SHADOW = "shadow"
    LIVE = "live"


class ConfigurationError(RuntimeError):
    """Raised when a process-specific required setting is missing or unsafe."""


class Settings(BaseSettings):
    """Environment configuration with conservative, non-secret defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: AppEnvironment = AppEnvironment.LOCAL
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    log_format: str = "json"
    timezone: str = "Europe/Bratislava"

    database_url: str
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=5, ge=0, le=50)
    database_connect_timeout_seconds: float = Field(default=5.0, gt=0, le=60)

    api_host: str = "0.0.0.0"  # noqa: S104 - intentional container bind address
    api_port: int = Field(default=8000, ge=1, le=65535)
    allowed_origins: str = "http://localhost:5173"
    frontend_base_url: str = "http://localhost:5173"
    session_secret: SecretStr | None = None
    session_secret_file: Path | None = None
    session_lifetime_hours: int = Field(default=12, ge=1, le=168)
    oauth_state_lifetime_minutes: int = Field(default=10, ge=1, le=30)
    api_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    api_oauth_rate_limit: int = Field(default=20, ge=1, le=1000)
    api_mutation_rate_limit: int = Field(default=120, ge=1, le=10000)
    media_root: Path = Path("/var/lib/domcek/media")
    public_media_base_url: str = "http://localhost:8000"
    media_max_upload_bytes: int = Field(default=8 * 1024 * 1024, ge=1024, le=25 * 1024 * 1024)
    media_max_image_edge: int = Field(default=1600, ge=256, le=4096)

    discord_application_id: int | None = None
    discord_guild_id: int | None = None
    discord_admin_role_id: int | None = None
    discord_team_mod_role_id: int | None = None
    discord_publisher_role_id: int | None = None
    discord_announcement_channel_id: int | None = None
    discord_command_channel_id: int | None = None
    discord_moderator_channel_id: int | None = None
    discord_projects_category_id: int | None = None
    discord_archive_category_id: int | None = None
    discord_bot_token: SecretStr | None = None
    discord_bot_token_file: Path | None = None
    discord_oauth_client_id: int | None = None
    discord_oauth_client_secret: SecretStr | None = None
    discord_oauth_client_secret_file: Path | None = None
    discord_oauth_redirect_uri: str = "http://localhost:8000/api/v1/auth/discord/callback"

    google_service_account_file: Path | None = None
    calendar_sync_past_days: int = Field(default=30, ge=0, le=365)
    calendar_sync_future_days: int = Field(default=400, ge=14, le=1825)
    calendar_sync_page_size: int = Field(default=250, ge=1, le=2500)
    calendar_request_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    calendar_retry_attempts: int = Field(default=3, ge=1, le=8)
    calendar_retry_base_seconds: float = Field(default=0.5, ge=0, le=30)
    calendar_stale_warning_minutes: int = Field(default=120, ge=1, le=10080)
    calendar_max_safe_age_minutes: int = Field(default=360, ge=1, le=20160)
    worker_poll_interval_seconds: float = Field(default=30.0, ge=1, le=3600)
    calendar_sync_interval_seconds: float = Field(default=300.0, ge=30, le=86400)
    publication_grace_period_minutes: int = Field(default=120, ge=1, le=1440)
    publication_reminder_lead_hours: int = Field(default=24, ge=1, le=168)
    publication_execution_mode: PublicationExecutionMode = PublicationExecutionMode.PAUSED
    allow_manual_publication_in_shadow: bool = False
    publication_recovery_stale_seconds: int = Field(default=90, ge=10, le=3600)
    publication_retry_attempts: int = Field(default=3, ge=1, le=8)
    publication_seen_emoji: str = Field(default="✅", min_length=1, max_length=100)
    discord_sync_guild_commands: bool = True
    discord_dm_response_enabled: bool = True
    bot_thoughts_file: Path = Path("/run/project-assets/thoughts.txt")
    intro_generator_api_key: SecretStr | None = None
    intro_generator_api_key_file: Path | None = None
    intro_generator_model: str = Field(
        default="gemini-2.5-flash-lite", min_length=1, max_length=100
    )
    intro_generator_timeout_seconds: float = Field(default=12.0, gt=0, le=60)

    @model_validator(mode="after")
    def validate_calendar_freshness_thresholds(self) -> Settings:
        if self.calendar_stale_warning_minutes >= self.calendar_max_safe_age_minutes:
            raise ValueError(
                "CALENDAR_STALE_WARNING_MINUTES must be lower than CALENDAR_MAX_SAFE_AGE_MINUTES"
            )
        return self

    @model_validator(mode="after")
    def validate_manual_shadow_publication(self) -> Settings:
        if self.allow_manual_publication_in_shadow and not (
            self.app_env is AppEnvironment.STAGING
            and self.publication_execution_mode is PublicationExecutionMode.SHADOW
        ):
            raise ValueError(
                "ALLOW_MANUAL_PUBLICATION_IN_SHADOW is allowed only in the staging "
                "environment while PUBLICATION_EXECUTION_MODE=shadow"
            )
        return self

    @model_validator(mode="after")
    def block_live_until_product_safety_contracts_exist(self) -> Settings:
        if self.publication_execution_mode is PublicationExecutionMode.LIVE:
            raise ValueError(
                "PUBLICATION_EXECUTION_MODE=live is blocked until the durable publication "
                "grace period and state-safe Discord Undo contracts are implemented"
            )
        return self

    @model_validator(mode="after")
    def validate_web_urls(self) -> Settings:
        for field_name, value in (
            ("FRONTEND_BASE_URL", self.frontend_base_url),
            ("DISCORD_OAUTH_REDIRECT_URI", self.discord_oauth_redirect_uri),
            ("PUBLIC_MEDIA_BASE_URL", self.public_media_base_url),
        ):
            parsed = urlsplit(value)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError(f"{field_name} must be an absolute HTTP(S) URL")
            if parsed.username or parsed.password or parsed.fragment:
                raise ValueError(f"{field_name} cannot contain credentials or a fragment")
            if field_name == "FRONTEND_BASE_URL" and (parsed.path not in {"", "/"} or parsed.query):
                raise ValueError("FRONTEND_BASE_URL cannot contain a path or query")
            if field_name == "DISCORD_OAUTH_REDIRECT_URI" and parsed.query:
                raise ValueError("DISCORD_OAUTH_REDIRECT_URI cannot contain a query")
            if field_name == "PUBLIC_MEDIA_BASE_URL" and (
                parsed.path not in {"", "/"} or parsed.query
            ):
                raise ValueError("PUBLIC_MEDIA_BASE_URL cannot contain a path or query")
            if self.app_env in {AppEnvironment.STAGING, AppEnvironment.PRODUCTION}:
                if parsed.scheme != "https":
                    raise ValueError(f"{field_name} must use HTTPS outside local/test")
        for origin in self.allowed_origin_list:
            parsed = urlsplit(origin)
            if (
                "*" in origin
                or parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("ALLOWED_ORIGINS must contain exact HTTP(S) origins")
            if self.app_env in {AppEnvironment.STAGING, AppEnvironment.PRODUCTION}:
                if parsed.scheme != "https":
                    raise ValueError("ALLOWED_ORIGINS must use HTTPS outside local/test")
        return self

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use postgresql+asyncpg://")
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"unknown IANA timezone: {value}") from exc
        return value

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        normalized = value.upper()
        if normalized not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(allowed)}")
        return normalized

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, value: str) -> str:
        if value not in {"json", "console"}:
            raise ValueError("LOG_FORMAT must be json or console")
        return value

    @property
    def allowed_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    def secret_value(self, direct: SecretStr | None, file_path: Path | None, name: str) -> str:
        if direct is not None and direct.get_secret_value():
            return direct.get_secret_value()
        if file_path is not None:
            try:
                value = file_path.read_text(encoding="utf-8").strip()
            except OSError as exc:
                raise ConfigurationError(f"{name} file cannot be read: {file_path}") from exc
            if value:
                return value
        raise ConfigurationError(f"{name} is required for this process")

    def discord_token_value(self) -> str:
        return self.secret_value(
            self.discord_bot_token,
            self.discord_bot_token_file,
            "DISCORD_BOT_TOKEN or DISCORD_BOT_TOKEN_FILE",
        )

    def session_secret_value(self) -> str:
        value = self.secret_value(
            self.session_secret,
            self.session_secret_file,
            "SESSION_SECRET or SESSION_SECRET_FILE",
        )
        if len(value) < 32:
            raise ConfigurationError("SESSION_SECRET must contain at least 32 characters")
        return value

    def discord_oauth_secret_value(self) -> str:
        return self.secret_value(
            self.discord_oauth_client_secret,
            self.discord_oauth_client_secret_file,
            "DISCORD_OAUTH_CLIENT_SECRET or DISCORD_OAUTH_CLIENT_SECRET_FILE",
        )

    @property
    def resolved_discord_oauth_client_id(self) -> int:
        client_id = self.discord_oauth_client_id or self.discord_application_id
        if client_id is None:
            raise ConfigurationError(
                "DISCORD_OAUTH_CLIENT_ID or DISCORD_APPLICATION_ID is required"
            )
        return client_id

    @property
    def secure_cookies(self) -> bool:
        return self.app_env in {AppEnvironment.STAGING, AppEnvironment.PRODUCTION}

    @property
    def manual_publication_enabled(self) -> bool:
        return self.publication_execution_mode is PublicationExecutionMode.LIVE or (
            self.publication_execution_mode is PublicationExecutionMode.SHADOW
            and self.app_env is AppEnvironment.STAGING
            and self.allow_manual_publication_in_shadow
        )

    def validate_for(self, process: ProcessKind) -> Settings:
        if self.app_env in {AppEnvironment.STAGING, AppEnvironment.PRODUCTION}:
            if self.log_format != "json":
                raise ConfigurationError("staging and production require LOG_FORMAT=json")
            if "localhost" in self.allowed_origin_list:
                raise ConfigurationError("staging and production cannot allow localhost origins")

        if process is ProcessKind.API:
            self.session_secret_value()
            self.discord_oauth_secret_value()
            _ = self.resolved_discord_oauth_client_id
            if self.discord_guild_id is None:
                raise ConfigurationError("DISCORD_GUILD_ID is required for the API process")
            self.discord_token_value()
        elif process in {ProcessKind.BOT, ProcessKind.WORKER}:
            self.discord_token_value()
            if process is ProcessKind.BOT and self.discord_application_id is None:
                raise ConfigurationError("DISCORD_APPLICATION_ID is required for the bot process")
            if process is ProcessKind.BOT:
                self.session_secret_value()
            if self.discord_guild_id is None:
                raise ConfigurationError(
                    f"DISCORD_GUILD_ID is required for the {process.value} process"
                )
        return self

    def optional_intro_generator_key(self) -> str | None:
        if self.intro_generator_api_key is not None:
            value = self.intro_generator_api_key.get_secret_value().strip()
            return value or None
        if self.intro_generator_api_key_file is None:
            return None
        try:
            value = self.intro_generator_api_key_file.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise ConfigurationError(
                f"INTRO_GENERATOR_API_KEY_FILE cannot be read: {self.intro_generator_api_key_file}"
            ) from exc
        return value or None


def load_settings(process: ProcessKind) -> Settings:
    """Load environment values and enforce the selected process contract."""

    return Settings().validate_for(process)
