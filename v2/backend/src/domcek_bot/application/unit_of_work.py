"""Application-owned contracts for an atomic repository transaction."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Protocol

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
    WebSessionRepository,
)


class RepositorySet(Protocol):
    @property
    def guild_configs(self) -> GuildConfigRepository: ...

    @property
    def calendar_sources(self) -> CalendarSourceRepository: ...

    @property
    def reaction_configs(self) -> ReactionConfigRepository: ...

    @property
    def external_events(self) -> ExternalEventRepository: ...

    @property
    def event_overrides(self) -> EventOverrideRepository: ...

    @property
    def event_series_overrides(self) -> EventSeriesOverrideRepository: ...

    @property
    def manual_events(self) -> ManualEventRepository: ...

    @property
    def info_announcements(self) -> InfoAnnouncementRepository: ...

    @property
    def publication_runs(self) -> PublicationRunRepository: ...

    @property
    def shadow_publications(self) -> ShadowPublicationRepository: ...

    @property
    def runtime_heartbeats(self) -> RuntimeHeartbeatRepository: ...

    @property
    def integration_tasks(self) -> IntegrationTaskRepository: ...

    @property
    def channel_archive_requests(self) -> ChannelArchiveRequestRepository: ...

    @property
    def web_sessions(self) -> WebSessionRepository: ...

    @property
    def audit_logs(self) -> AuditLogRepository: ...


class UnitOfWork(Protocol):
    """Port used by application services without importing SQLAlchemy."""

    def transaction(self) -> AbstractAsyncContextManager[RepositorySet]: ...
