"""Composition helpers for the production Google Calendar adapter."""

from __future__ import annotations

from domcek_bot.config import ConfigurationError, Settings
from domcek_bot.infrastructure.google_calendar import (
    GoogleCalendarClient,
    GoogleServiceAccountTokenProvider,
)


def build_google_calendar_client(settings: Settings) -> GoogleCalendarClient:
    credential_path = settings.google_service_account_file
    if credential_path is None:
        raise ConfigurationError("GOOGLE_SERVICE_ACCOUNT_FILE is required for Calendar sync")
    token_provider = GoogleServiceAccountTokenProvider.from_file(credential_path)
    return GoogleCalendarClient(
        token_provider,
        page_size=settings.calendar_sync_page_size,
        timeout_seconds=settings.calendar_request_timeout_seconds,
        retry_attempts=settings.calendar_retry_attempts,
        retry_base_seconds=settings.calendar_retry_base_seconds,
        timezone=settings.timezone,
    )
