"""Immutable publication history and dashboard operational summary."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from domcek_bot.application.auth.authorization import Capability, Principal
from domcek_bot.application.records import (
    PublicationItemRecord,
    PublicationMessageRecord,
    PublicationRunRecord,
)
from domcek_bot.application.unit_of_work import UnitOfWork
from domcek_bot.domain.calendar import CalendarFreshnessState, assess_calendar_freshness


@dataclass(frozen=True, slots=True)
class PublicationHistoryEntry:
    run: PublicationRunRecord
    items: tuple[PublicationItemRecord, ...]
    messages: tuple[PublicationMessageRecord, ...]


@dataclass(frozen=True, slots=True)
class DashboardSummary:
    automatic_publication_enabled: bool
    last_calendar_sync_at: datetime | None
    last_publication: PublicationRunRecord | None
    pending_archive_count: int
    discord_places_configured: bool
    active_calendars: tuple[DashboardCalendarSource, ...]


@dataclass(frozen=True, slots=True)
class DashboardCalendarSource:
    id: uuid.UUID
    display_name: str
    sync_status: str
    freshness: CalendarFreshnessState
    last_sync_success_at: datetime | None
    last_sync_error: str | None


class PublicationHistoryService:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        *,
        calendar_warning_age: timedelta = timedelta(hours=2),
        calendar_max_safe_age: timedelta = timedelta(hours=6),
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._calendar_warning_age = calendar_warning_age
        self._calendar_max_safe_age = calendar_max_safe_age
        self._clock = clock or (lambda: datetime.now(UTC))

    async def list(
        self, principal: Principal, *, limit: int = 50
    ) -> tuple[PublicationHistoryEntry, ...]:
        principal.require(Capability.VIEW_ADMIN)
        safe_limit = min(max(limit, 1), 100)
        async with self._unit_of_work.transaction() as repositories:
            runs = await repositories.publication_runs.list_for_guild(
                principal.guild_id, limit=safe_limit
            )
            entries: list[PublicationHistoryEntry] = []
            for run in runs:
                items = await repositories.publication_runs.list_items(run.id)
                messages = await repositories.publication_runs.list_messages(run.id)
                entries.append(PublicationHistoryEntry(run, tuple(items), tuple(messages)))
        return tuple(entries)

    async def get(self, run_id: uuid.UUID, principal: Principal) -> PublicationHistoryEntry | None:
        principal.require(Capability.VIEW_ADMIN)
        async with self._unit_of_work.transaction() as repositories:
            run = await repositories.publication_runs.get(run_id)
            if run is None or run.guild_id != principal.guild_id:
                return None
            items = await repositories.publication_runs.list_items(run.id)
            messages = await repositories.publication_runs.list_messages(run.id)
        return PublicationHistoryEntry(run, tuple(items), tuple(messages))

    async def dashboard(self, principal: Principal) -> DashboardSummary:
        principal.require(Capability.VIEW_ADMIN)
        async with self._unit_of_work.transaction() as repositories:
            guild = await repositories.guild_configs.get(principal.guild_id)
            if guild is None:
                raise LookupError("guild configuration not found")
            calendars = await repositories.calendar_sources.list_for_guild(principal.guild_id)
            runs = await repositories.publication_runs.list_for_guild(principal.guild_id, limit=1)
            archives = await repositories.channel_archive_requests.list_pending(principal.guild_id)
        last_sync = max(
            (item.last_sync_success_at for item in calendars if item.last_sync_success_at),
            default=None,
        )
        observed_at = self._clock()
        active_calendars = tuple(
            DashboardCalendarSource(
                id=item.id,
                display_name=item.display_name,
                sync_status=item.sync_status.value,
                freshness=assess_calendar_freshness(
                    item.last_sync_success_at,
                    now=observed_at,
                    warning_after=self._calendar_warning_age,
                    unsafe_after=self._calendar_max_safe_age,
                ).state,
                last_sync_success_at=item.last_sync_success_at,
                last_sync_error=item.last_sync_error,
            )
            for item in calendars
            if item.active
        )
        return DashboardSummary(
            automatic_publication_enabled=guild.automatic_publication_enabled,
            last_calendar_sync_at=last_sync,
            last_publication=runs[0] if runs else None,
            pending_archive_count=len(archives),
            discord_places_configured=guild.announcement_channel_id is not None,
            active_calendars=active_calendars,
        )
