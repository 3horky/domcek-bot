"""Durable Discord notification workflow for the publication protection period."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Protocol

from domcek_bot.application.publication.engine import (
    ModeratorAlertGateway,
    PublicationEngine,
    PublicationGuardPending,
    PublicationGuardResult,
    PublicationResult,
)
from domcek_bot.application.records import PublicationGuardNoticeRecord
from domcek_bot.application.unit_of_work import UnitOfWork
from domcek_bot.domain.enums import PublicationState


class PublicationGuardDiscordGateway(Protocol):
    async def admin_member_ids(self, guild_id: int, admin_role_id: int) -> tuple[int, ...]: ...

    async def send_guard_dm(
        self,
        *,
        recipient_user_id: int,
        run_id: uuid.UUID,
        release_at: datetime,
        nonce: str,
    ) -> tuple[int, int]: ...

    async def delete_guard_dm(self, *, channel_id: int, message_id: int) -> None: ...


class PublicationGuardService:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        engine: PublicationEngine,
        discord: PublicationGuardDiscordGateway,
        alerts: ModeratorAlertGateway,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._engine = engine
        self._discord = discord
        self._alerts = alerts

    async def notify(self, run_id: uuid.UUID, *, correlation_id: str) -> int:
        async with self._unit_of_work.transaction() as repositories:
            run = await repositories.publication_runs.get(run_id)
            if run is None or run.state is not PublicationState.WAITING_FOR_RELEASE:
                return 0
            if run.release_at is None:
                raise RuntimeError("waiting publication has no release timestamp")
            config = await repositories.guild_configs.get(run.guild_id)
            if config is None or config.admin_role_id is None:
                raise RuntimeError("publication guard has no Admin role configuration")
            existing = await repositories.publication_runs.list_guard_notices(run.id)
        admins = await self._discord.admin_member_ids(run.guild_id, config.admin_role_id)
        recipient_ids = tuple(dict.fromkeys((*admins, *config.publication_guard_recipient_ids)))
        existing_ids = {notice.recipient_user_id for notice in existing}
        notices = tuple(
            PublicationGuardNoticeRecord(
                id=uuid.uuid4(),
                publication_run_id=run.id,
                recipient_user_id=recipient_id,
                state="pending",
                nonce=hashlib.sha256(f"guard:{run.id}:{recipient_id}".encode()).hexdigest(),
            )
            for recipient_id in recipient_ids
            if recipient_id not in existing_ids
        )
        if notices:
            async with self._unit_of_work.transaction() as repositories:
                await repositories.publication_runs.add_guard_notices(notices)
        sent = 0
        for notice in (*existing, *notices):
            if notice.state in {"sent", "deleted"}:
                continue
            try:
                channel_id, message_id = await self._discord.send_guard_dm(
                    recipient_user_id=notice.recipient_user_id,
                    run_id=run.id,
                    release_at=run.release_at,
                    nonce=notice.nonce,
                )
            except Exception as exc:
                async with self._unit_of_work.transaction() as repositories:
                    await repositories.publication_runs.mark_guard_notice_failed(
                        notice.id, detail=type(exc).__name__
                    )
                await self._alerts.send_alert(
                    guild_id=run.guild_id,
                    moderator_channel_id=config.moderator_channel_id,
                    title="Ochranná správa sa nedoručila",
                    summary=(
                        "Publikovanie pokračuje podľa plánu, ale jeden z oprávnených "
                        "príjemcov nedostal dočasnú súkromnú správu."
                    ),
                    correlation_id=correlation_id,
                    run_id=run.id,
                )
                continue
            async with self._unit_of_work.transaction() as repositories:
                await repositories.publication_runs.mark_guard_notice_sent(
                    notice.id,
                    channel_id=channel_id,
                    message_id=message_id,
                    sent_at=datetime.now(UTC),
                )
            sent += 1
        return sent

    async def stop_for_user(
        self,
        *,
        guild_id: int,
        user_id: int,
        correlation_id: str,
        run_id: uuid.UUID | None = None,
        now: datetime | None = None,
    ) -> PublicationGuardResult:
        checked_at = now or datetime.now(UTC)
        async with self._unit_of_work.transaction() as repositories:
            config = await repositories.guild_configs.get(guild_id)
            waiting = await repositories.publication_runs.get_waiting_guard(
                guild_id, now=checked_at, run_id=run_id
            )
        if config is None or config.admin_role_id is None:
            raise PermissionError("publication guard configuration is unavailable")
        admins = await self._discord.admin_member_ids(guild_id, config.admin_role_id)
        if user_id not in {*admins, *config.publication_guard_recipient_ids}:
            raise PermissionError("user is not an authorized publication guard recipient")
        if waiting is None:
            raise PublicationGuardPending("publication can no longer be stopped")
        result = await self._engine.cancel_guard(
            waiting.id,
            correlation_id=correlation_id,
            actor_user_id=user_id,
            now=checked_at,
        )
        await self.cleanup(waiting.id)
        return result

    async def cleanup(self, run_id: uuid.UUID) -> None:
        async with self._unit_of_work.transaction() as repositories:
            notices = await repositories.publication_runs.list_guard_notices(run_id)
        for notice in notices:
            if (
                notice.state != "sent"
                or notice.discord_channel_id is None
                or notice.discord_message_id is None
            ):
                continue
            try:
                await self._discord.delete_guard_dm(
                    channel_id=notice.discord_channel_id,
                    message_id=notice.discord_message_id,
                )
            except Exception:  # noqa: S112 - cleanup cannot change the terminal decision
                continue
            async with self._unit_of_work.transaction() as repositories:
                await repositories.publication_runs.mark_guard_notice_deleted(
                    notice.id, deleted_at=datetime.now(UTC)
                )

    async def release_due(
        self, *, now: datetime, correlation_id: str
    ) -> list[PublicationGuardResult | PublicationResult]:
        results = await self._engine.release_due_guards(now=now, correlation_id=correlation_id)
        for result in results:
            if result.state is not PublicationState.WAITING_FOR_RELEASE:
                await self.cleanup(result.run_id)
        return results
