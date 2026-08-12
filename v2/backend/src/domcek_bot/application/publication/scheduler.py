"""Timezone-aware due-slot scheduler with freshness and grace-period gates."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from domcek_bot.application.audit import AuditWriter
from domcek_bot.application.publication.engine import (
    ModeratorAlertGateway,
    PublicationAlreadyRunning,
    PublicationEngine,
)
from domcek_bot.application.unit_of_work import UnitOfWork
from domcek_bot.domain.enums import PublicationMode, PublicationState
from domcek_bot.domain.ids import GuildId
from domcek_bot.domain.time import PublicationSchedule, PublicationSlot


@dataclass(frozen=True, slots=True)
class SchedulerDecision:
    guild_id: int
    slot_key: str | None
    action: str
    run_id: uuid.UUID | None = None


class FinalCalendarSynchronizer(Protocol):
    async def synchronize_guild(self, guild_id: int, *, correlation_id: str) -> bool: ...


class PublicationScheduler:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        engine: PublicationEngine,
        alerts: ModeratorAlertGateway,
        *,
        grace_period: timedelta,
        calendar_max_safe_age: timedelta,
        final_calendar_sync: FinalCalendarSynchronizer,
        reminder_alerts: ModeratorAlertGateway | None = None,
        reminder_lead: timedelta = timedelta(hours=24),
    ) -> None:
        self._unit_of_work = unit_of_work
        self._engine = engine
        self._alerts = alerts
        self._grace_period = grace_period
        self._calendar_max_safe_age = calendar_max_safe_age
        self._final_calendar_sync = final_calendar_sync
        self._reminder_alerts = reminder_alerts
        self._reminder_lead = reminder_lead

    async def send_upcoming_reminders(
        self, *, now: datetime | None = None, correlation_id: str | None = None
    ) -> list[SchedulerDecision]:
        """Send at most one configured reminder for each upcoming publication slot."""
        checked_at = now or datetime.now(UTC)
        correlation = correlation_id or str(uuid.uuid4())
        async with self._unit_of_work.transaction() as repositories:
            guilds = await repositories.guild_configs.list_all()
        decisions: list[SchedulerDecision] = []
        for guild in guilds:
            if (
                self._reminder_alerts is None
                or not guild.automatic_publication_enabled
                or not guild.alert_publication_reminder_enabled
                or guild.moderator_channel_id is None
            ):
                decisions.append(SchedulerDecision(guild.guild_id, None, "reminder_disabled"))
                continue
            schedule = PublicationSchedule(
                guild.publication_weekday, guild.publication_time, guild.timezone
            )
            slot = schedule.next_slot(GuildId(guild.guild_id), checked_at, inclusive=True)
            time_until_slot = slot.instant - checked_at
            if not timedelta(0) < time_until_slot <= self._reminder_lead:
                decisions.append(SchedulerDecision(guild.guild_id, slot.key, "reminder_not_due"))
                continue
            sent = await self._send_reminder_once(
                guild.guild_id,
                guild.moderator_channel_id,
                slot,
                correlation,
            )
            decisions.append(
                SchedulerDecision(
                    guild.guild_id,
                    slot.key,
                    "reminder_sent" if sent else "reminder_already_sent",
                )
            )
        return decisions

    async def run_due(
        self, *, now: datetime | None = None, correlation_id: str | None = None
    ) -> list[SchedulerDecision]:
        checked_at = now or datetime.now(UTC)
        correlation = correlation_id or str(uuid.uuid4())
        async with self._unit_of_work.transaction() as repositories:
            guilds = await repositories.guild_configs.list_all()
        decisions: list[SchedulerDecision] = []
        for guild in guilds:
            if not guild.automatic_publication_enabled:
                decisions.append(SchedulerDecision(guild.guild_id, None, "automatic_disabled"))
                continue
            schedule = PublicationSchedule(
                guild.publication_weekday, guild.publication_time, guild.timezone
            )
            slot = _latest_due_slot(schedule, GuildId(guild.guild_id), checked_at)
            if slot is None:
                decisions.append(SchedulerDecision(guild.guild_id, None, "not_due"))
                continue
            async with self._unit_of_work.transaction() as repositories:
                existing = await repositories.publication_runs.get_for_slot(
                    guild.guild_id, slot.key
                )
            if existing is not None:
                if existing.state in {
                    PublicationState.PREPARING,
                    PublicationState.RETRY_PENDING,
                }:
                    try:
                        resumed = await self._engine.publish(
                            existing.id, correlation_id=correlation
                        )
                    except PublicationAlreadyRunning:
                        decisions.append(
                            SchedulerDecision(
                                guild.guild_id,
                                slot.key,
                                "publication_in_progress",
                                existing.id,
                            )
                        )
                        continue
                    decisions.append(
                        SchedulerDecision(
                            guild.guild_id, slot.key, resumed.state.value, resumed.run_id
                        )
                    )
                    continue
                if existing.state is PublicationState.WAITING_FOR_RELEASE:
                    released = await self._engine.release_guard(
                        existing.id,
                        correlation_id=correlation,
                        now=checked_at,
                    )
                    decisions.append(
                        SchedulerDecision(
                            guild.guild_id,
                            slot.key,
                            released.state.value,
                            released.run_id,
                        )
                    )
                    continue
                if existing.state is PublicationState.SUCCEEDED_MANUAL:
                    action = "skipped_after_manual"
                elif existing.state is PublicationState.PUBLISHING:
                    action = "publication_in_progress"
                elif existing.state is PublicationState.FAILED:
                    action = "publication_failed_requires_admin"
                else:
                    action = "already_materialized"
                decisions.append(SchedulerDecision(guild.guild_id, slot.key, action, existing.id))
                continue
            if checked_at - slot.instant > self._grace_period:
                newly_recorded = await self._audit_skip(
                    guild.guild_id, slot, "missed_slot_outside_grace", correlation
                )
                if newly_recorded:
                    await self._alerts.send_alert(
                        guild_id=guild.guild_id,
                        moderator_channel_id=guild.moderator_channel_id,
                        title="Carlo nepublikoval starý zmeškaný termín",
                        summary="Termín je mimo bezpečnej doby automatického dobehnutia.",
                        correlation_id=correlation,
                        run_id=None,
                    )
                decisions.append(SchedulerDecision(guild.guild_id, slot.key, "outside_grace"))
                continue
            final_sync_succeeded = await self._final_calendar_sync.synchronize_guild(
                guild.guild_id, correlation_id=correlation
            )
            calendar_is_safe = await self._calendar_is_safe(guild.guild_id, checked_at)
            if not final_sync_succeeded and not (
                guild.allow_stale_calendar_cache and calendar_is_safe
            ):
                newly_recorded = await self._audit_skip(
                    guild.guild_id, slot, "final_calendar_sync_failed", correlation
                )
                if newly_recorded:
                    await self._alerts.send_alert(
                        guild_id=guild.guild_id,
                        moderator_channel_id=guild.moderator_channel_id,
                        title="Carlo zablokoval publikovanie",
                        summary=(
                            "Finálna synchronizácia kalendára zlyhala a núdzové použitie "
                            "posledných dát nie je povolené alebo už nie je bezpečné."
                        ),
                        correlation_id=correlation,
                        run_id=None,
                    )
                decisions.append(
                    SchedulerDecision(guild.guild_id, slot.key, "final_calendar_sync_failed")
                )
                continue
            if not calendar_is_safe:
                newly_recorded = await self._audit_skip(
                    guild.guild_id, slot, "calendar_stale", correlation
                )
                if newly_recorded:
                    await self._alerts.send_alert(
                        guild_id=guild.guild_id,
                        moderator_channel_id=guild.moderator_channel_id,
                        title="Carlo zablokoval publikovanie",
                        summary="Kalendárové údaje nie sú dostatočne čerstvé.",
                        correlation_id=correlation,
                        run_id=None,
                    )
                decisions.append(SchedulerDecision(guild.guild_id, slot.key, "calendar_stale"))
                continue
            if not final_sync_succeeded:
                await self._audit_stale_cache_acceptance(guild.guild_id, slot, correlation)
                await self._alerts.send_alert(
                    guild_id=guild.guild_id,
                    moderator_channel_id=guild.moderator_channel_id,
                    title="Carlo použil posledné bezpečne čerstvé dáta",
                    summary=(
                        "Finálna synchronizácia zlyhala; publikovanie pokračovalo iba na základe "
                        "výslovného nastavenia Admina."
                    ),
                    correlation_id=correlation,
                    run_id=None,
                )
            prepared = await self._engine.prepare(
                guild.guild_id,
                reference_time=slot.instant,
                mode=PublicationMode.AUTOMATIC,
                initiated_by_user_id=None,
                correlation_id=correlation,
            )
            try:
                guarded = await self._engine.begin_guard(
                    prepared.run.id,
                    correlation_id=correlation,
                    now=checked_at,
                )
            except PublicationAlreadyRunning:
                decisions.append(
                    SchedulerDecision(
                        guild.guild_id,
                        slot.key,
                        "publication_in_progress",
                        prepared.run.id,
                    )
                )
                continue
            decisions.append(
                SchedulerDecision(guild.guild_id, slot.key, guarded.state.value, guarded.run_id)
            )
        return decisions

    async def _audit_stale_cache_acceptance(
        self, guild_id: int, slot: PublicationSlot, correlation_id: str
    ) -> None:
        async with self._unit_of_work.transaction() as repositories:
            await AuditWriter(repositories.audit_logs).success(
                guild_id=guild_id,
                actor_user_id=None,
                action="publication.stale_calendar_cache_accepted",
                object_type="publication_slot",
                object_id=slot.key,
                correlation_id=correlation_id,
                after_value={"reason": "explicit_admin_opt_in"},
            )

    async def _calendar_is_safe(self, guild_id: int, checked_at: datetime) -> bool:
        async with self._unit_of_work.transaction() as repositories:
            sources = await repositories.calendar_sources.list_for_guild(guild_id)
        active = [source for source in sources if source.active]
        return bool(active) and all(
            source.last_sync_success_at is not None
            and checked_at - source.last_sync_success_at <= self._calendar_max_safe_age
            for source in active
        )

    async def _audit_skip(
        self, guild_id: int, slot: PublicationSlot, reason: str, correlation_id: str
    ) -> bool:
        async with self._unit_of_work.transaction() as repositories:
            await repositories.publication_runs.lock_slot(guild_id, slot.key)
            existing = await repositories.audit_logs.list_for_object("publication_slot", slot.key)
            if any(
                entry.action == "publication.scheduler_skipped"
                and entry.after_value is not None
                and entry.after_value.get("reason") == reason
                for entry in existing
            ):
                return False
            await AuditWriter(repositories.audit_logs).success(
                guild_id=guild_id,
                actor_user_id=None,
                action="publication.scheduler_skipped",
                object_type="publication_slot",
                object_id=slot.key,
                correlation_id=correlation_id,
                after_value={"reason": reason},
            )
        return True

    async def _send_reminder_once(
        self,
        guild_id: int,
        moderator_channel_id: int,
        slot: PublicationSlot,
        correlation_id: str,
    ) -> bool:
        if self._reminder_alerts is None:  # guarded by the caller, kept type-safe
            return False
        async with self._unit_of_work.transaction() as repositories:
            await repositories.publication_runs.lock_slot(guild_id, slot.key)
            existing_run = await repositories.publication_runs.get_for_slot(guild_id, slot.key)
            existing_audit = await repositories.audit_logs.list_for_object(
                "publication_slot", slot.key
            )
            if existing_run is not None or any(
                entry.action == "publication.reminder_sent" for entry in existing_audit
            ):
                return False
            await self._reminder_alerts.send_alert(
                guild_id=guild_id,
                moderator_channel_id=moderator_channel_id,
                title="Blíži sa automatické publikovanie",
                summary=(
                    "Skontrolujte najbližší draft v Redakčnom pulte. "
                    f"Naplánovaný termín: {slot.instant.isoformat()}."
                ),
                correlation_id=correlation_id,
                run_id=None,
            )
            await AuditWriter(repositories.audit_logs).success(
                guild_id=guild_id,
                actor_user_id=None,
                action="publication.reminder_sent",
                object_type="publication_slot",
                object_id=slot.key,
                correlation_id=correlation_id,
                after_value={"scheduled_for": slot.instant.isoformat()},
            )
        return True


def _latest_due_slot(
    schedule: PublicationSchedule, guild_id: GuildId, now: datetime
) -> PublicationSlot | None:
    candidate = schedule.next_slot(guild_id, now - timedelta(days=7), inclusive=False)
    return candidate if candidate.instant <= now else None
