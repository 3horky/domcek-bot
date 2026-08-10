"""Transactional snapshot loader for the pure publication composer."""

from __future__ import annotations

from datetime import datetime

from domcek_bot.application.publication.composer import compose_publication
from domcek_bot.application.publication.models import (
    EventSeriesOverrideInput,
    InfoAnnouncementInput,
    ManualEventInput,
    PublicationComposeSnapshot,
    PublicationDraft,
)
from domcek_bot.application.unit_of_work import UnitOfWork


class PublicationConfigurationNotFound(LookupError):
    """Raised when a guild has no persisted publication configuration."""


class PublicationDraftService:
    """Load one consistent database snapshot and compose the next publication."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def compose_next(
        self,
        guild_id: int,
        *,
        reference_time: datetime,
        intro_text: str,
    ) -> PublicationDraft:
        snapshot = await self.load_next_snapshot(
            guild_id, reference_time=reference_time, intro_text=intro_text
        )
        return compose_publication(snapshot)

    async def load_next_snapshot(
        self,
        guild_id: int,
        *,
        reference_time: datetime,
        intro_text: str,
    ) -> PublicationComposeSnapshot:
        async with self._unit_of_work.transaction() as repositories:
            guild = await repositories.guild_configs.get(guild_id)
            if guild is None:
                raise PublicationConfigurationNotFound(
                    f"publication configuration not found for guild {guild_id}"
                )

            sources = await repositories.calendar_sources.list_for_guild(guild_id)
            source_ids = tuple(source.id for source in sources)
            events = await repositories.external_events.list_for_sources(source_ids)
            event_ids = tuple(event.id for event in events)
            overrides = await repositories.event_overrides.list_for_events(event_ids)
            series = await repositories.event_series_overrides.list_for_sources(source_ids)
            manual = await repositories.manual_events.list_for_guild(guild_id)
            info = await repositories.info_announcements.list_for_guild(guild_id)
            completed = await repositories.publication_runs.completed_slot_keys(guild_id)

        return PublicationComposeSnapshot(
            guild=guild,
            reference_time=reference_time,
            calendar_sources=tuple(sources),
            external_events=tuple(events),
            event_overrides=tuple(overrides),
            series_overrides=tuple(
                EventSeriesOverrideInput(
                    id=item.id,
                    calendar_source_id=item.calendar_source_id,
                    series_key=item.series_key,
                    effective_from_key=item.effective_from_key,
                    effective_all_day=item.effective_all_day,
                    effective_from_at=item.effective_from_at,
                    effective_from_date=item.effective_from_date,
                    public_title=item.public_title,
                    description_state=item.description_state,
                    public_description=item.public_description,
                    version=item.version,
                )
                for item in series
            ),
            manual_events=tuple(
                ManualEventInput(
                    id=item.id,
                    guild_id=item.guild_id,
                    title=item.title,
                    description=item.description,
                    is_all_day=item.is_all_day,
                    starts_at=item.starts_at,
                    ends_at=item.ends_at,
                    starts_on=item.starts_on,
                    ends_on=item.ends_on,
                    timezone=item.timezone,
                    link_url=item.link_url,
                    active=item.active,
                    deleted_at=item.deleted_at,
                )
                for item in manual
            ),
            info_announcements=tuple(
                InfoAnnouncementInput(
                    id=item.id,
                    guild_id=item.guild_id,
                    title=item.title,
                    description=item.description,
                    valid_from=item.valid_from,
                    valid_until=item.valid_until,
                    link_url=item.link_url,
                    image_url=item.image_url,
                    active=item.active,
                    deleted_at=item.deleted_at,
                )
                for item in info
            ),
            completed_slot_keys=completed,
            intro_text=intro_text,
        )
