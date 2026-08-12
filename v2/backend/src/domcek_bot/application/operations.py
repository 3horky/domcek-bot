"""Persistent runtime heartbeats and guild-isolated operational summaries."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from domcek_bot.application.auth.authorization import Capability, Principal
from domcek_bot.application.publication.composer import next_unprocessed_slot
from domcek_bot.application.records import (
    CalendarSourceRecord,
    IntegrationTaskRecord,
    RuntimeHeartbeatRecord,
)
from domcek_bot.application.unit_of_work import UnitOfWork
from domcek_bot.domain.enums import PublicationState
from domcek_bot.domain.ids import GuildId
from domcek_bot.domain.time import PublicationSchedule

HEARTBEAT_NAMESPACE = uuid.UUID("e21150ce-f3f4-42b9-92e6-4e69eef7e866")
SUCCESS_STATES = {
    PublicationState.SUCCEEDED_AUTOMATIC,
    PublicationState.SUCCEEDED_MANUAL,
}
FAILURE_STATES = {
    PublicationState.FAILED,
    PublicationState.PARTIALLY_PUBLISHED,
}
IN_PROGRESS_STATES = {
    PublicationState.PREPARING,
    PublicationState.WAITING_FOR_RELEASE,
    PublicationState.PUBLISHING,
    PublicationState.RETRY_PENDING,
}


@dataclass(frozen=True, slots=True)
class ProcessStatus:
    process_name: str
    instance_id: uuid.UUID
    state: str
    healthy: bool
    started_at: datetime
    last_seen_at: datetime
    details: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RuntimeHealth:
    healthy: bool
    reason: str
    active_instances: int
    state: str | None
    last_seen_at: datetime | None


@dataclass(frozen=True, slots=True)
class PublicationMetrics:
    sample_size: int
    successful: int
    failed: int
    in_progress: int
    skipped: int


@dataclass(frozen=True, slots=True)
class OperationsSummary:
    observed_at: datetime
    processes: tuple[ProcessStatus, ...]
    active_instance_counts: dict[str, int]
    calendars: tuple[CalendarSourceRecord, ...]
    publication_metrics: PublicationMetrics
    recent_tasks: tuple[IntegrationTaskRecord, ...]
    next_slot_key: str
    next_scheduled_for: datetime


class RuntimeOperationsService:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def heartbeat(
        self,
        *,
        guild_id: int,
        process_name: str,
        instance_id: uuid.UUID,
        state: str,
        started_at: datetime,
        observed_at: datetime | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        timestamp = _aware(observed_at or datetime.now(UTC))
        clean_process = process_name.strip().lower()
        clean_state = state.strip().lower()
        if not clean_process or len(clean_process) > 32:
            raise ValueError("runtime process name is invalid")
        if not clean_state or len(clean_state) > 32:
            raise ValueError("runtime state is invalid")
        identity = uuid.uuid5(HEARTBEAT_NAMESPACE, f"{guild_id}:{clean_process}:{instance_id}")
        record = RuntimeHeartbeatRecord(
            id=identity,
            guild_id=guild_id,
            process_name=clean_process,
            instance_id=instance_id,
            state=clean_state,
            started_at=_aware(started_at),
            last_seen_at=timestamp,
            details=dict(details or {}),
        )
        async with self._unit_of_work.transaction() as repositories:
            await repositories.runtime_heartbeats.upsert(record)

    async def process_health(
        self,
        *,
        guild_id: int,
        process_name: str,
        expected_state: str,
        expected_execution_mode: str | None = None,
        now: datetime | None = None,
        stale_after: timedelta = timedelta(seconds=90),
    ) -> RuntimeHealth:
        """Check that exactly one expected runtime instance is fresh and ready."""

        observed_at = _aware(now or datetime.now(UTC))
        clean_process = process_name.strip().lower()
        clean_expected_state = expected_state.strip().lower()
        if not clean_process or not clean_expected_state:
            raise ValueError("process name and expected state are required")
        if stale_after <= timedelta(0):
            raise ValueError("runtime heartbeat freshness must be positive")

        async with self._unit_of_work.transaction() as repositories:
            heartbeats = await repositories.runtime_heartbeats.list_for_guild(guild_id)

        active = [
            heartbeat
            for heartbeat in heartbeats
            if heartbeat.process_name == clean_process
            and _heartbeat_is_healthy(heartbeat, observed_at, stale_after)
        ]
        if not active:
            return RuntimeHealth(
                healthy=False,
                reason="no_fresh_instance",
                active_instances=0,
                state=None,
                last_seen_at=None,
            )
        newest = max(active, key=lambda item: item.last_seen_at)
        if len(active) != 1:
            return RuntimeHealth(
                healthy=False,
                reason="duplicate_active_instances",
                active_instances=len(active),
                state=newest.state,
                last_seen_at=newest.last_seen_at,
            )
        if newest.state != clean_expected_state:
            return RuntimeHealth(
                healthy=False,
                reason="unexpected_state",
                active_instances=1,
                state=newest.state,
                last_seen_at=newest.last_seen_at,
            )
        if (
            expected_execution_mode is not None
            and newest.details.get("publication_execution_mode") != expected_execution_mode
        ):
            return RuntimeHealth(
                healthy=False,
                reason="unexpected_execution_mode",
                active_instances=1,
                state=newest.state,
                last_seen_at=newest.last_seen_at,
            )
        return RuntimeHealth(
            healthy=True,
            reason="ready",
            active_instances=1,
            state=newest.state,
            last_seen_at=newest.last_seen_at,
        )

    async def summary(
        self,
        principal: Principal,
        *,
        now: datetime | None = None,
        stale_after: timedelta = timedelta(seconds=90),
    ) -> OperationsSummary:
        principal.require(Capability.VIEW_ADMIN)
        observed_at = _aware(now or datetime.now(UTC))
        async with self._unit_of_work.transaction() as repositories:
            guild = await repositories.guild_configs.get(principal.guild_id)
            if guild is None:
                raise LookupError("guild configuration not found")
            heartbeats = await repositories.runtime_heartbeats.list_for_guild(principal.guild_id)
            calendars = await repositories.calendar_sources.list_for_guild(principal.guild_id)
            runs = await repositories.publication_runs.list_for_guild(principal.guild_id, limit=100)
            tasks = await repositories.integration_tasks.list_for_guild(
                principal.guild_id, limit=20
            )
            completed = await repositories.publication_runs.completed_slot_keys(principal.guild_id)

        latest_by_process: dict[str, RuntimeHeartbeatRecord] = {}
        active_instance_counts: dict[str, int] = {}
        for heartbeat in heartbeats:
            latest_by_process.setdefault(heartbeat.process_name, heartbeat)
            if _heartbeat_is_healthy(heartbeat, observed_at, stale_after):
                active_instance_counts[heartbeat.process_name] = (
                    active_instance_counts.get(heartbeat.process_name, 0) + 1
                )
        processes = tuple(
            ProcessStatus(
                process_name=heartbeat.process_name,
                instance_id=heartbeat.instance_id,
                state=heartbeat.state,
                healthy=_heartbeat_is_healthy(heartbeat, observed_at, stale_after),
                started_at=heartbeat.started_at,
                last_seen_at=heartbeat.last_seen_at,
                details=heartbeat.details,
            )
            for heartbeat in latest_by_process.values()
        )
        schedule = PublicationSchedule(
            guild.publication_weekday, guild.publication_time, guild.timezone
        )
        next_slot = next_unprocessed_slot(
            schedule, GuildId(principal.guild_id), observed_at, completed
        )
        metrics = PublicationMetrics(
            sample_size=len(runs),
            successful=sum(run.state in SUCCESS_STATES for run in runs),
            failed=sum(run.state in FAILURE_STATES for run in runs),
            in_progress=sum(run.state in IN_PROGRESS_STATES for run in runs),
            skipped=sum(run.state is PublicationState.SKIPPED_AFTER_MANUAL for run in runs),
        )
        return OperationsSummary(
            observed_at=observed_at,
            processes=processes,
            active_instance_counts=active_instance_counts,
            calendars=tuple(calendars),
            publication_metrics=metrics,
            recent_tasks=tuple(tasks),
            next_slot_key=next_slot.key,
            next_scheduled_for=next_slot.instant,
        )


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("runtime timestamps must be timezone-aware")
    return value


def _heartbeat_is_healthy(
    heartbeat: RuntimeHeartbeatRecord,
    observed_at: datetime,
    stale_after: timedelta,
) -> bool:
    return bool(
        heartbeat.last_seen_at <= observed_at
        and observed_at - heartbeat.last_seen_at <= stale_after
        and heartbeat.state not in {"disconnected", "stopped", "failed"}
    )
