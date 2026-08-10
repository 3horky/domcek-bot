"""Transactional full and incremental calendar synchronization orchestration."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol

import structlog

from domcek_bot.application.calendar.contracts import (
    CalendarClient,
    CalendarIntegrationError,
    CalendarMetadata,
    CalendarPayloadError,
    CalendarSyncTokenExpired,
    ProviderCalendarEvent,
)
from domcek_bot.application.calendar.normalization import normalize_provider_event
from domcek_bot.application.records import CalendarSourceRecord
from domcek_bot.application.unit_of_work import UnitOfWork
from domcek_bot.domain.enums import ExternalEventStatus

logger = structlog.get_logger(__name__)


class CalendarSyncMode(StrEnum):
    FULL = "full"
    INCREMENTAL = "incremental"
    FULL_AFTER_EXPIRED_TOKEN = "full_after_expired_token"  # noqa: S105


class CalendarSyncAlreadyRunning(CalendarIntegrationError):
    pass


@dataclass(frozen=True, slots=True)
class CalendarSyncPolicy:
    past_horizon: timedelta = timedelta(days=30)
    future_horizon: timedelta = timedelta(days=400)
    max_pages: int = 1000
    lease_timeout: timedelta = timedelta(minutes=15)

    def __post_init__(self) -> None:
        if self.past_horizon < timedelta(0):
            raise ValueError("past sync horizon cannot be negative")
        if self.future_horizon < timedelta(days=14):
            raise ValueError("future sync horizon must cover at least 14 days")
        if self.max_pages < 1:
            raise ValueError("max_pages must be positive")
        if self.lease_timeout <= timedelta(0):
            raise ValueError("sync lease timeout must be positive")


@dataclass(frozen=True, slots=True)
class CalendarSyncResult:
    source_id: uuid.UUID
    mode: CalendarSyncMode
    pages: int
    received: int
    created: int
    updated: int
    cancelled: int
    ignored_cancellations: int
    missing_marked_deleted: int
    series_identity_warnings: int
    completed_at: datetime


@dataclass(frozen=True, slots=True)
class CalendarConnectionResult:
    source_id: uuid.UUID
    metadata: CalendarMetadata


class ModeratorAlertPort(Protocol):
    async def calendar_sync_blocked(
        self, *, guild_id: int, source_id: uuid.UUID, error_code: str
    ) -> None: ...

    async def calendar_series_identity_changed(
        self, *, guild_id: int, source_id: uuid.UUID, event_id: uuid.UUID
    ) -> None: ...


class NullModeratorAlert:
    async def calendar_sync_blocked(
        self, *, guild_id: int, source_id: uuid.UUID, error_code: str
    ) -> None:
        return None

    async def calendar_series_identity_changed(
        self, *, guild_id: int, source_id: uuid.UUID, event_id: uuid.UUID
    ) -> None:
        return None


class CalendarSyncService:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        client: CalendarClient,
        *,
        policy: CalendarSyncPolicy | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        alerts: ModeratorAlertPort | None = None,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._client = client
        self._policy = policy or CalendarSyncPolicy()
        self._clock = clock
        self._alerts = alerts or NullModeratorAlert()

    async def verify_connection(self, source_id: uuid.UUID) -> CalendarConnectionResult:
        source = await self._load_source(source_id)
        metadata = await self._client.get_calendar(source.external_calendar_id)
        if metadata.access_role not in {"reader", "writer", "owner"}:
            raise CalendarIntegrationError("calendar does not provide event read access")
        return CalendarConnectionResult(source_id=source_id, metadata=metadata)

    async def synchronize(
        self, source_id: uuid.UUID, *, force_full: bool = False
    ) -> CalendarSyncResult:
        source = await self._load_source(source_id)
        attempted_at = self._aware_now()
        async with self._unit_of_work.transaction() as transaction:
            acquired = await transaction.calendar_sources.try_acquire_sync(
                source_id,
                attempted_at=attempted_at,
                stale_before=attempted_at - self._policy.lease_timeout,
            )
        if not acquired:
            raise CalendarSyncAlreadyRunning("calendar synchronization is already running")

        try:
            can_increment = (
                not force_full
                and source.sync_token is not None
                and source.sync_token_query_key == self._client.sync_query_key
            )
            if can_increment:
                try:
                    events, next_token, pages = await self._collect_pages(
                        source, sync_token=source.sync_token
                    )
                    mode = CalendarSyncMode.INCREMENTAL
                except CalendarSyncTokenExpired:
                    events, next_token, pages = await self._collect_pages(source, sync_token=None)
                    mode = CalendarSyncMode.FULL_AFTER_EXPIRED_TOKEN
            else:
                events, next_token, pages = await self._collect_pages(source, sync_token=None)
                mode = CalendarSyncMode.FULL

            completed_at = self._aware_now()
            return await self._apply_success(
                source,
                events=events,
                next_sync_token=next_token,
                pages=pages,
                mode=mode,
                completed_at=completed_at,
            )
        except Exception as exc:
            error_code = _safe_error_code(exc)
            failure_at = self._aware_now()
            async with self._unit_of_work.transaction() as transaction:
                await transaction.calendar_sources.mark_sync_failed(
                    source_id, attempted_at=failure_at, error_code=error_code
                )
            try:
                await self._alerts.calendar_sync_blocked(
                    guild_id=source.guild_id,
                    source_id=source_id,
                    error_code=error_code,
                )
            except Exception as alert_error:
                # Alert delivery must not hide the synchronization failure and
                # provider payloads must not reach logs.
                logger.warning(
                    "calendar_sync_alert_failed",
                    source_id=str(source_id),
                    alert_error=type(alert_error).__name__,
                )
            raise

    async def _load_source(self, source_id: uuid.UUID) -> CalendarSourceRecord:
        async with self._unit_of_work.transaction() as transaction:
            source = await transaction.calendar_sources.get(source_id)
        if source is None:
            raise LookupError(f"calendar source not found: {source_id}")
        if not source.active:
            raise CalendarIntegrationError("calendar source is inactive")
        return source

    async def _collect_pages(
        self, source: CalendarSourceRecord, *, sync_token: str | None
    ) -> tuple[list[ProviderCalendarEvent], str, int]:
        page_token: str | None = None
        seen_page_tokens: set[str] = set()
        events: list[ProviderCalendarEvent] = []
        next_sync_token: str | None = None
        now = self._aware_now()
        time_min = None if sync_token else now - self._policy.past_horizon
        time_max = None if sync_token else now + self._policy.future_horizon

        for page_number in range(1, self._policy.max_pages + 1):
            page = await self._client.list_events(
                source.external_calendar_id,
                page_token=page_token,
                sync_token=sync_token,
                time_min=time_min,
                time_max=time_max,
            )
            events.extend(page.events)
            next_sync_token = page.next_sync_token
            if page.next_page_token is None:
                if next_sync_token is None:
                    raise CalendarPayloadError("last Google page has no nextSyncToken")
                return events, next_sync_token, page_number
            if page.next_sync_token is not None:
                raise CalendarPayloadError("non-final Google page unexpectedly has nextSyncToken")
            if page.next_page_token in seen_page_tokens:
                raise CalendarPayloadError("Google pagination token repeated")
            seen_page_tokens.add(page.next_page_token)
            page_token = page.next_page_token

        raise CalendarPayloadError("Google pagination exceeded configured safety limit")

    async def _apply_success(
        self,
        source: CalendarSourceRecord,
        *,
        events: list[ProviderCalendarEvent],
        next_sync_token: str,
        pages: int,
        mode: CalendarSyncMode,
        completed_at: datetime,
    ) -> CalendarSyncResult:
        created = 0
        updated = 0
        cancelled = 0
        ignored_cancellations = 0
        seen_source_keys: set[str] = set()
        series_identity_warnings: set[uuid.UUID] = set()

        async with self._unit_of_work.transaction() as transaction:
            existing_by_source_key = {
                event.source_key: event
                for event in await transaction.external_events.list_for_source(source.id)
            }
            for event in events:
                if event.status is ExternalEventStatus.CANCELLED:
                    was_known = await transaction.external_events.cancel_by_provider_event_id(
                        source.id,
                        event.provider_event_id,
                        synced_at=completed_at,
                    )
                    cancelled += int(was_known)
                    ignored_cancellations += int(not was_known)
                    continue

                normalized = normalize_provider_event(event, source, synced_at=completed_at)
                existing = existing_by_source_key.get(normalized.source_key)
                if existing is not None and existing.series_key != normalized.series_key:
                    override = await transaction.event_overrides.get(existing.id)
                    if override is not None:
                        series_identity_warnings.add(existing.id)
                seen_source_keys.add(normalized.source_key)
                was_created = await transaction.external_events.upsert_from_sync(normalized)
                created += int(was_created)
                updated += int(not was_created)

            is_full = mode is not CalendarSyncMode.INCREMENTAL
            missing_marked_deleted = 0
            if is_full:
                missing_marked_deleted = await transaction.external_events.mark_missing_deleted(
                    source.id,
                    seen_source_keys,
                    deleted_at=completed_at,
                )
            await transaction.calendar_sources.mark_sync_succeeded(
                source.id,
                sync_token=next_sync_token,
                sync_token_query_key=self._client.sync_query_key,
                completed_at=completed_at,
                was_full_sync=is_full,
            )

        for event_id in series_identity_warnings:
            try:
                await self._alerts.calendar_series_identity_changed(
                    guild_id=source.guild_id,
                    source_id=source.id,
                    event_id=event_id,
                )
            except Exception as alert_error:
                logger.warning(
                    "calendar_series_alert_failed",
                    source_id=str(source.id),
                    event_id=str(event_id),
                    alert_error=type(alert_error).__name__,
                )

        return CalendarSyncResult(
            source_id=source.id,
            mode=mode,
            pages=pages,
            received=len(events),
            created=created,
            updated=updated,
            cancelled=cancelled,
            ignored_cancellations=ignored_cancellations,
            missing_marked_deleted=missing_marked_deleted,
            series_identity_warnings=len(series_identity_warnings),
            completed_at=completed_at,
        )

    def _aware_now(self) -> datetime:
        value = self._clock()
        if value.utcoffset() is None:
            raise ValueError("calendar sync clock must return an aware datetime")
        return value


def _safe_error_code(exc: Exception) -> str:
    if isinstance(exc, CalendarIntegrationError):
        return type(exc).__name__
    return "CalendarSyncInternalError"
