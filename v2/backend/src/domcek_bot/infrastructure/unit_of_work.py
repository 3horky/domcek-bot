"""SQLAlchemy Unit of Work implementing one atomic application transaction."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from sqlalchemy.orm.exc import StaleDataError

from domcek_bot.application.repositories import (
    AuditLogRepository,
    CalendarSourceRepository,
    ChannelArchiveRequestRepository,
    EventOverrideRepository,
    EventSeriesOverrideRepository,
    ExternalEventRepository,
    GuildConfigRepository,
    InfoAnnouncementRepository,
    IntegrationTaskRepository,
    ManualEventRepository,
    PublicationRunRepository,
    ReactionConfigRepository,
    RuntimeHeartbeatRepository,
    ShadowPublicationRepository,
    UndoOperationRepository,
    WebSessionRepository,
)
from domcek_bot.application.unit_of_work import RepositorySet
from domcek_bot.domain.errors import OptimisticLockError
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.repositories import (
    SqlAlchemyAuditLogRepository,
    SqlAlchemyCalendarSourceRepository,
    SqlAlchemyChannelArchiveRequestRepository,
    SqlAlchemyEventOverrideRepository,
    SqlAlchemyEventSeriesOverrideRepository,
    SqlAlchemyExternalEventRepository,
    SqlAlchemyGuildConfigRepository,
    SqlAlchemyInfoAnnouncementRepository,
    SqlAlchemyIntegrationTaskRepository,
    SqlAlchemyManualEventRepository,
    SqlAlchemyPublicationRunRepository,
    SqlAlchemyReactionConfigRepository,
    SqlAlchemyRuntimeHeartbeatRepository,
    SqlAlchemyShadowPublicationRepository,
    SqlAlchemyUndoOperationRepository,
    SqlAlchemyWebSessionRepository,
)


@dataclass(frozen=True, slots=True)
class SqlAlchemyRepositorySet:
    guild_configs: GuildConfigRepository
    calendar_sources: CalendarSourceRepository
    reaction_configs: ReactionConfigRepository
    external_events: ExternalEventRepository
    event_overrides: EventOverrideRepository
    event_series_overrides: EventSeriesOverrideRepository
    manual_events: ManualEventRepository
    info_announcements: InfoAnnouncementRepository
    publication_runs: PublicationRunRepository
    shadow_publications: ShadowPublicationRepository
    runtime_heartbeats: RuntimeHeartbeatRepository
    integration_tasks: IntegrationTaskRepository
    channel_archive_requests: ChannelArchiveRequestRepository
    undo_operations: UndoOperationRepository
    web_sessions: WebSessionRepository
    audit_logs: AuditLogRepository


class SqlAlchemyUnitOfWork:
    def __init__(self, database: Database) -> None:
        self._database = database

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[RepositorySet]:
        try:
            async with self._database.session() as session, session.begin():
                yield SqlAlchemyRepositorySet(
                    guild_configs=SqlAlchemyGuildConfigRepository(session),
                    calendar_sources=SqlAlchemyCalendarSourceRepository(session),
                    reaction_configs=SqlAlchemyReactionConfigRepository(session),
                    external_events=SqlAlchemyExternalEventRepository(session),
                    event_overrides=SqlAlchemyEventOverrideRepository(session),
                    event_series_overrides=SqlAlchemyEventSeriesOverrideRepository(session),
                    manual_events=SqlAlchemyManualEventRepository(session),
                    info_announcements=SqlAlchemyInfoAnnouncementRepository(session),
                    publication_runs=SqlAlchemyPublicationRunRepository(session),
                    shadow_publications=SqlAlchemyShadowPublicationRepository(session),
                    runtime_heartbeats=SqlAlchemyRuntimeHeartbeatRepository(session),
                    integration_tasks=SqlAlchemyIntegrationTaskRepository(session),
                    channel_archive_requests=SqlAlchemyChannelArchiveRequestRepository(session),
                    undo_operations=SqlAlchemyUndoOperationRepository(session),
                    web_sessions=SqlAlchemyWebSessionRepository(session),
                    audit_logs=SqlAlchemyAuditLogRepository(session),
                )
        except StaleDataError as exc:
            raise OptimisticLockError("record changed since it was loaded") from exc
