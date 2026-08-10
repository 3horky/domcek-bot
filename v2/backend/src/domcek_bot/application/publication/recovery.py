"""Explicit Admin reconciliation of an ambiguous Discord message effect."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from domcek_bot.application.audit import AuditWriter
from domcek_bot.application.auth.authorization import Capability, Principal
from domcek_bot.application.publication.engine import PublicationEngine, PublicationResult
from domcek_bot.application.unit_of_work import UnitOfWork
from domcek_bot.domain.enums import PublicationMessageState, PublicationState


class InvalidReconciliation(ValueError):
    pass


class PublicationRecoveryService:
    def __init__(self, unit_of_work: UnitOfWork, engine: PublicationEngine) -> None:
        self._unit_of_work = unit_of_work
        self._engine = engine

    async def mark_existing_and_continue(
        self,
        run_id: uuid.UUID,
        *,
        message_position: int,
        discord_message_id: int,
        principal: Principal,
        correlation_id: str,
        now: datetime | None = None,
    ) -> PublicationResult:
        return await self._reconcile(
            run_id,
            message_position=message_position,
            discord_message_id=discord_message_id,
            principal=principal,
            correlation_id=correlation_id,
            now=now or datetime.now(UTC),
        )

    async def confirm_not_sent_and_continue(
        self,
        run_id: uuid.UUID,
        *,
        message_position: int,
        principal: Principal,
        correlation_id: str,
        now: datetime | None = None,
    ) -> PublicationResult:
        return await self._reconcile(
            run_id,
            message_position=message_position,
            discord_message_id=None,
            principal=principal,
            correlation_id=correlation_id,
            now=now or datetime.now(UTC),
        )

    async def _reconcile(
        self,
        run_id: uuid.UUID,
        *,
        message_position: int,
        discord_message_id: int | None,
        principal: Principal,
        correlation_id: str,
        now: datetime,
    ) -> PublicationResult:
        principal.require(Capability.RECONCILE_PUBLICATION)
        async with self._unit_of_work.transaction() as repositories:
            run = await repositories.publication_runs.get(run_id)
            if run is None or run.guild_id != principal.guild_id:
                raise InvalidReconciliation("publication run not found")
            messages = await repositories.publication_runs.list_messages(run_id)
            message = next((item for item in messages if item.position == message_position), None)
            if message is None or message.state is not PublicationMessageState.UNCERTAIN:
                raise InvalidReconciliation("message does not require reconciliation")
            if discord_message_id is None:
                await repositories.publication_runs.reset_uncertain_message(message.id)
                resolution = "confirmed_not_sent"
            else:
                await repositories.publication_runs.mark_message_sent(
                    message.id, discord_message_id=discord_message_id, sent_at=now
                )
                resolution = "existing_message_linked"
            await repositories.publication_runs.resolve_incidents(
                run_id,
                resolution=resolution,
                resolved_by_user_id=principal.user_id,
                resolved_at=now,
            )
            await repositories.publication_runs.set_state(run_id, PublicationState.RETRY_PENDING)
            await AuditWriter(repositories.audit_logs).success(
                guild_id=principal.guild_id,
                actor_user_id=principal.user_id,
                action="publication.reconciled",
                object_type="publication_run",
                object_id=str(run_id),
                correlation_id=correlation_id,
                after_value={
                    "message_position": message_position,
                    "resolution": resolution,
                    "discord_message_id": discord_message_id,
                },
            )
        return await self._engine.publish(run_id, correlation_id=correlation_id)
