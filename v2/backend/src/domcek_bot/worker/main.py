"""Calendar synchronization, publication scheduler and recovery worker."""

from __future__ import annotations

import asyncio
import signal
import uuid
from datetime import UTC, datetime, timedelta

import structlog

from domcek_bot.application.alerts import AlertCategory, ConfiguredModeratorAlerts
from domcek_bot.application.calendar.sync import CalendarSyncPolicy, CalendarSyncService
from domcek_bot.application.operations import RuntimeOperationsService
from domcek_bot.application.publication.engine import ModeratorAlertGateway, PublicationEngine
from domcek_bot.application.publication.intro import IntroService
from domcek_bot.application.publication.scheduler import PublicationScheduler
from domcek_bot.application.publication.service import PublicationDraftService
from domcek_bot.application.publication.shadow import ShadowPublicationService
from domcek_bot.config import ProcessKind, PublicationExecutionMode, load_settings
from domcek_bot.infrastructure.calendar_factory import build_google_calendar_client
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.discord_publication import (
    DiscordHttpPublicationGateway,
    DiscordModeratorAlertGateway,
)
from domcek_bot.infrastructure.gemini_intro import GeminiIntroGenerator
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from domcek_bot.logging import configure_logging

logger = structlog.get_logger(__name__)


class CalendarModeratorAlerts:
    def __init__(
        self,
        unit_of_work: SqlAlchemyUnitOfWork,
        discord: ModeratorAlertGateway,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._discord = discord

    async def calendar_sync_blocked(
        self, *, guild_id: int, source_id: uuid.UUID, error_code: str
    ) -> None:
        await self._send(
            guild_id,
            "Carlo nedokázal synchronizovať kalendár",
            f"Zdroj {source_id}; bezpečný kód chyby: {error_code}.",
        )

    async def calendar_series_identity_changed(
        self, *, guild_id: int, source_id: uuid.UUID, event_id: uuid.UUID
    ) -> None:
        await self._send(
            guild_id,
            "Carlo našiel nejednoznačnú zmenu opakovanej udalosti",
            f"Zdroj {source_id}; udalosť {event_id}. Skontrolujte redakčný pult.",
        )

    async def _send(self, guild_id: int, title: str, summary: str) -> None:
        async with self._unit_of_work.transaction() as repositories:
            guild = await repositories.guild_configs.get(guild_id)
        await self._discord.send_alert(
            guild_id=guild_id,
            moderator_channel_id=guild.moderator_channel_id if guild else None,
            title=title,
            summary=summary,
            correlation_id=str(uuid.uuid4()),
            run_id=None,
        )


class WorkerFinalCalendarSynchronizer:
    def __init__(
        self,
        unit_of_work: SqlAlchemyUnitOfWork,
        service: CalendarSyncService,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._service = service

    async def synchronize_guild(self, guild_id: int, *, correlation_id: str) -> bool:
        return await _sync_active_calendars(
            self._unit_of_work,
            self._service,
            guild_id=guild_id,
            correlation_id=correlation_id,
        )


async def serve() -> None:
    settings = load_settings(ProcessKind.WORKER)
    configure_logging(settings, ProcessKind.WORKER.value)
    database = Database(settings)
    unit_of_work = SqlAlchemyUnitOfWork(database)
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for shutdown_signal in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(shutdown_signal, stop_event.set)
        except NotImplementedError:  # pragma: no cover - Windows event loop
            pass

    token = settings.discord_token_value()
    discord = DiscordHttpPublicationGateway(bot_token=token)
    alerts = DiscordModeratorAlertGateway(
        bot_token=token, frontend_base_url=settings.frontend_base_url
    )
    calendar_client = build_google_calendar_client(settings)
    intro_key = settings.optional_intro_generator_key()
    intro_generator = (
        GeminiIntroGenerator(
            api_key=intro_key,
            model=settings.intro_generator_model,
            timeout_seconds=settings.intro_generator_timeout_seconds,
        )
        if intro_key is not None
        else None
    )
    draft_service = PublicationDraftService(unit_of_work)
    shadow_publications = ShadowPublicationService(unit_of_work, draft_service)
    runtime_operations = RuntimeOperationsService(unit_of_work)
    runtime_instance_id = uuid.uuid4()
    runtime_started_at = datetime.now(UTC)
    publication_alerts = ConfiguredModeratorAlerts(unit_of_work, alerts, AlertCategory.PUBLICATION)
    calendar_alerts = ConfiguredModeratorAlerts(unit_of_work, alerts, AlertCategory.CALENDAR)
    reminder_alerts = ConfiguredModeratorAlerts(unit_of_work, alerts, AlertCategory.REMINDER)
    engine = PublicationEngine(
        unit_of_work,
        draft_service,
        IntroService(intro_generator),
        discord,
        alerts=publication_alerts,
        seen_emoji=settings.publication_seen_emoji,
        max_safe_retries=settings.publication_retry_attempts,
    )
    calendar_sync = CalendarSyncService(
        unit_of_work,
        calendar_client,
        policy=CalendarSyncPolicy(
            past_horizon=timedelta(days=settings.calendar_sync_past_days),
            future_horizon=timedelta(days=settings.calendar_sync_future_days),
        ),
        alerts=CalendarModeratorAlerts(unit_of_work, calendar_alerts),
    )
    scheduler = PublicationScheduler(
        unit_of_work,
        engine,
        publication_alerts,
        grace_period=timedelta(minutes=settings.publication_grace_period_minutes),
        calendar_max_safe_age=timedelta(minutes=settings.calendar_max_safe_age_minutes),
        final_calendar_sync=WorkerFinalCalendarSynchronizer(unit_of_work, calendar_sync),
        reminder_alerts=reminder_alerts,
        reminder_lead=timedelta(hours=settings.publication_reminder_lead_hours),
    )

    await database.ping()
    await logger.ainfo(
        "worker_started",
        publication_execution_mode=settings.publication_execution_mode.value,
    )
    try:
        await _heartbeat_worker(
            unit_of_work,
            runtime_operations,
            runtime_instance_id,
            runtime_started_at,
            state="running",
            execution_mode=settings.publication_execution_mode,
        )
        if settings.publication_execution_mode is PublicationExecutionMode.LIVE:
            await _recover(engine, settings.publication_recovery_stale_seconds)
        else:
            await logger.ainfo(
                "publication_recovery_skipped",
                publication_execution_mode=settings.publication_execution_mode.value,
            )
        next_calendar_sync = datetime.min.replace(tzinfo=UTC)
        while not stop_event.is_set():
            now = datetime.now(UTC)
            if now >= next_calendar_sync:
                async with unit_of_work.transaction() as repositories:
                    guilds = await repositories.guild_configs.list_all()
                for guild in guilds:
                    sync_succeeded = await _sync_active_calendars(
                        unit_of_work,
                        calendar_sync,
                        guild_id=guild.guild_id,
                    )
                    if settings.publication_execution_mode is PublicationExecutionMode.SHADOW:
                        await _capture_shadow_publication(
                            shadow_publications,
                            guild.guild_id,
                            now,
                            calendar_sync_succeeded=sync_succeeded,
                        )
                next_calendar_sync = now + timedelta(
                    seconds=settings.calendar_sync_interval_seconds
                )
            if settings.publication_execution_mode is PublicationExecutionMode.LIVE:
                await _run_scheduler(scheduler)
            await _heartbeat_worker(
                unit_of_work,
                runtime_operations,
                runtime_instance_id,
                runtime_started_at,
                state="running",
                execution_mode=settings.publication_execution_mode,
            )
            try:
                await asyncio.wait_for(
                    stop_event.wait(), timeout=settings.worker_poll_interval_seconds
                )
            except TimeoutError:
                await database.ping()
    finally:
        await _heartbeat_worker(
            unit_of_work,
            runtime_operations,
            runtime_instance_id,
            runtime_started_at,
            state="stopped",
            execution_mode=settings.publication_execution_mode,
        )
        if intro_generator is not None:
            await intro_generator.close()
        await calendar_client.close()
        await alerts.close()
        await discord.close()
        await database.close()
        await logger.ainfo("worker_stopped")


async def _heartbeat_worker(
    unit_of_work: SqlAlchemyUnitOfWork,
    operations: RuntimeOperationsService,
    instance_id: uuid.UUID,
    started_at: datetime,
    *,
    state: str,
    execution_mode: PublicationExecutionMode,
    observed_at: datetime | None = None,
) -> None:
    try:
        async with unit_of_work.transaction() as repositories:
            guilds = await repositories.guild_configs.list_all()
        for guild in guilds:
            await operations.heartbeat(
                guild_id=guild.guild_id,
                process_name="worker",
                instance_id=instance_id,
                state=state,
                started_at=started_at,
                observed_at=observed_at,
                details={"publication_execution_mode": execution_mode.value},
            )
    except Exception as exc:
        await logger.awarning("worker_runtime_heartbeat_failed", error_type=type(exc).__name__)


async def _sync_active_calendars(
    unit_of_work: SqlAlchemyUnitOfWork,
    service: CalendarSyncService,
    *,
    guild_id: int | None = None,
    correlation_id: str | None = None,
) -> bool:
    async with unit_of_work.transaction() as repositories:
        guilds = await repositories.guild_configs.list_all()
        sources = [
            source
            for guild in guilds
            if guild_id is None or guild.guild_id == guild_id
            for source in await repositories.calendar_sources.list_for_guild(guild.guild_id)
            if source.active
        ]
    all_succeeded = bool(sources)
    for source in sources:
        try:
            result = await service.synchronize(source.id)
            await logger.ainfo(
                "calendar_sync_completed",
                source_id=str(source.id),
                correlation_id=correlation_id,
                mode=result.mode.value,
                received=result.received,
            )
        except Exception as exc:
            all_succeeded = False
            await logger.aerror(
                "calendar_sync_failed",
                source_id=str(source.id),
                correlation_id=correlation_id,
                error_type=type(exc).__name__,
            )
    return all_succeeded


async def _recover(engine: PublicationEngine, stale_seconds: int) -> None:
    correlation_id = str(uuid.uuid4())
    try:
        results = await engine.recover(
            stale_before=datetime.now(UTC) - timedelta(seconds=stale_seconds),
            correlation_id=correlation_id,
        )
        await logger.ainfo("publication_recovery_completed", recovered=len(results))
    except Exception as exc:
        await logger.aerror(
            "publication_recovery_failed",
            correlation_id=correlation_id,
            error_type=type(exc).__name__,
        )


async def _capture_shadow_publication(
    service: ShadowPublicationService,
    guild_id: int,
    observed_at: datetime,
    *,
    calendar_sync_succeeded: bool,
) -> None:
    correlation_id = str(uuid.uuid4())
    try:
        capture = await service.capture_next(
            guild_id,
            observed_at=observed_at,
            calendar_sync_succeeded=calendar_sync_succeeded,
        )
        await logger.ainfo(
            "shadow_publication_captured",
            correlation_id=correlation_id,
            guild_id=guild_id,
            slot_key=capture.slot_key,
            draft_sha256=capture.draft_sha256,
            observation_count=capture.observation_count,
            item_count=capture.item_count,
            message_count=capture.message_count,
            calendar_sync_valid=capture.calendar_sync_valid,
        )
    except Exception as exc:
        await logger.aerror(
            "shadow_publication_failed",
            correlation_id=correlation_id,
            guild_id=guild_id,
            error_type=type(exc).__name__,
        )


async def _run_scheduler(scheduler: PublicationScheduler) -> None:
    correlation_id = str(uuid.uuid4())
    try:
        reminder_decisions = await scheduler.send_upcoming_reminders(correlation_id=correlation_id)
        decisions = await scheduler.run_due(correlation_id=correlation_id)
        interesting = [
            decision
            for decision in (*reminder_decisions, *decisions)
            if decision.action
            not in {"not_due", "reminder_disabled", "reminder_not_due", "reminder_already_sent"}
        ]
        if interesting:
            await logger.ainfo(
                "publication_scheduler_checked",
                correlation_id=correlation_id,
                decisions=[decision.action for decision in interesting],
            )
    except Exception as exc:
        await logger.aerror(
            "publication_scheduler_failed",
            correlation_id=correlation_id,
            error_type=type(exc).__name__,
        )


def run() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    run()
