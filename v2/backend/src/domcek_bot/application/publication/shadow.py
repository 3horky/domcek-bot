"""Durable no-delivery publication captures used by staging shadow operation."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime

from domcek_bot.application.auth.authorization import Capability, Principal
from domcek_bot.application.publication.intro import FALLBACK_TEXT
from domcek_bot.application.publication.service import PublicationDraftService
from domcek_bot.application.records import ShadowPublicationRecord
from domcek_bot.application.unit_of_work import UnitOfWork


class ShadowPublicationService:
    def __init__(self, unit_of_work: UnitOfWork, drafts: PublicationDraftService) -> None:
        self._unit_of_work = unit_of_work
        self._drafts = drafts

    async def capture_next(
        self,
        guild_id: int,
        *,
        observed_at: datetime,
        calendar_sync_succeeded: bool,
    ) -> ShadowPublicationRecord:
        draft = await self._drafts.compose_next(
            guild_id,
            reference_time=observed_at,
            intro_text=FALLBACK_TEXT,
        )
        canonical = draft.canonical_json()
        payload: object = json.loads(canonical)
        if not isinstance(payload, dict):  # canonical draft root is an invariant
            raise TypeError("publication draft must serialize to an object")
        async with self._unit_of_work.transaction() as repositories:
            sources = tuple(
                source
                for source in await repositories.calendar_sources.list_for_guild(guild_id)
                if source.active
            )
        evidence = {
            "sync_attempt_succeeded": calendar_sync_succeeded,
            "active_source_count": len(sources),
            "sources": [
                {
                    "id": str(source.id),
                    "status": source.sync_status.value,
                    "last_sync_success_at": (
                        source.last_sync_success_at.isoformat()
                        if source.last_sync_success_at is not None
                        else None
                    ),
                }
                for source in sources
            ],
        }
        sync_valid = (
            bool(sources)
            and calendar_sync_succeeded
            and all(
                source.sync_status.value == "succeeded" and source.last_sync_success_at is not None
                for source in sources
            )
        )
        capture = ShadowPublicationRecord(
            id=uuid.uuid4(),
            guild_id=guild_id,
            slot_key=draft.slot_key,
            scheduled_for=draft.scheduled_for,
            first_observed_at=observed_at,
            last_observed_at=observed_at,
            observation_count=1,
            draft_sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            draft_json=payload,
            item_count=len(draft.public_items),
            message_count=len(draft.messages),
            calendar_sync_valid=sync_valid,
            calendar_sync_evidence=evidence,
            warning_codes=tuple(warning.code.value for warning in draft.warnings),
        )
        async with self._unit_of_work.transaction() as repositories:
            return await repositories.shadow_publications.record(capture)

    async def list(
        self, principal: Principal, *, limit: int = 20
    ) -> tuple[ShadowPublicationRecord, ...]:
        principal.require(Capability.VIEW_ADMIN)
        safe_limit = min(max(limit, 1), 100)
        async with self._unit_of_work.transaction() as repositories:
            captures = await repositories.shadow_publications.list_for_guild(
                principal.guild_id, limit=safe_limit
            )
        return tuple(captures)
