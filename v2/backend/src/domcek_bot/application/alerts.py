"""Guild-configured, visually distinct moderator alert routing."""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import ClassVar, Protocol

from domcek_bot.application.unit_of_work import UnitOfWork


class AlertCategory(StrEnum):
    CALENDAR = "calendar"
    PUBLICATION = "publication"
    CHANNEL = "channel"
    ROLE = "role"
    REMINDER = "reminder"


class ModeratorAlertTransport(Protocol):
    async def send_alert(
        self,
        *,
        guild_id: int,
        moderator_channel_id: int | None,
        title: str,
        summary: str,
        correlation_id: str,
        run_id: uuid.UUID | None,
    ) -> None: ...


class ConfiguredModeratorAlerts:
    _PREFIX: ClassVar[dict[AlertCategory, str]] = {
        AlertCategory.CALENDAR: "📅 Kalendár",
        AlertCategory.PUBLICATION: "📣 Publikovanie",
        AlertCategory.CHANNEL: "#️⃣ Kanály",
        AlertCategory.ROLE: "🛡️ Roly",
        AlertCategory.REMINDER: "⏰ Pripomienka",
    }

    def __init__(
        self,
        unit_of_work: UnitOfWork,
        transport: ModeratorAlertTransport,
        category: AlertCategory,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._transport = transport
        self._category = category

    async def send_alert(
        self,
        *,
        guild_id: int,
        moderator_channel_id: int | None,
        title: str,
        summary: str,
        correlation_id: str,
        run_id: uuid.UUID | None,
    ) -> None:
        del moderator_channel_id
        async with self._unit_of_work.transaction() as repositories:
            guild = await repositories.guild_configs.get(guild_id)
        if guild is None or guild.moderator_channel_id is None or not self._enabled(guild):
            return
        await self._transport.send_alert(
            guild_id=guild_id,
            moderator_channel_id=guild.moderator_channel_id,
            title=f"{self._PREFIX[self._category]} · {title}",
            summary=summary,
            correlation_id=correlation_id,
            run_id=run_id,
        )

    def _enabled(self, guild: object) -> bool:
        field = {
            AlertCategory.CALENDAR: "alert_calendar_sync_enabled",
            AlertCategory.PUBLICATION: "alert_publication_enabled",
            AlertCategory.CHANNEL: "alert_channel_operations_enabled",
            AlertCategory.ROLE: "alert_role_operations_enabled",
            AlertCategory.REMINDER: "alert_publication_reminder_enabled",
        }[self._category]
        return bool(getattr(guild, field))
