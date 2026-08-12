"""Persistent publication snapshot, delivery and crash recovery use cases."""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from typing import Protocol

from domcek_bot.application.audit import AuditWriter
from domcek_bot.application.publication.composer import compose_publication
from domcek_bot.application.publication.intro import FALLBACK_TEXT, IntroResult, IntroService
from domcek_bot.application.publication.models import (
    DiscordEmbedPlan,
    PublicationDraft,
    PublicationDraftItem,
)
from domcek_bot.application.publication.service import PublicationDraftService
from domcek_bot.application.records import (
    PublicationItemRecord,
    PublicationMessageRecord,
    PublicationRunRecord,
)
from domcek_bot.application.unit_of_work import UnitOfWork
from domcek_bot.domain.enums import (
    PublicationItemType,
    PublicationMessageState,
    PublicationMode,
    PublicationState,
)


class PublicationError(RuntimeError):
    pass


class PublicationChannelMissing(PublicationError):
    pass


class PublicationAlreadyRunning(PublicationError):
    pass


class PublicationSlotChanged(PublicationError):
    pass


class DiscordDefinitiveError(PublicationError):
    """Discord rejected a request and confirmed that it did not create a message."""


class DiscordTransientError(PublicationError):
    """A request can be retried safely because Discord confirmed no external effect."""

    def __init__(self, message: str, *, retry_after: float = 1.0) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class DiscordAmbiguousError(PublicationError):
    """The caller cannot know whether Discord accepted the external effect."""


class DiscordPublicationGateway(Protocol):
    async def send_message(self, message: PublicationMessageRecord) -> int: ...

    async def add_reaction(self, *, channel_id: int, message_id: int, emoji: str) -> None: ...


class ModeratorAlertGateway(Protocol):
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


class NullModeratorAlertGateway:
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
        del guild_id, moderator_channel_id, title, summary, correlation_id, run_id


@dataclass(frozen=True, slots=True)
class PreparedPublication:
    run: PublicationRunRecord
    created: bool
    message_count: int
    item_count: int


@dataclass(frozen=True, slots=True)
class PublicationPreview:
    draft: PublicationDraft
    intro: IntroResult
    announcement_channel_id: int | None


@dataclass(frozen=True, slots=True)
class PublicationResult:
    run_id: uuid.UUID
    state: PublicationState
    sent_message_ids: tuple[int, ...]
    warning_codes: tuple[str, ...] = ()


class PublicationEngine:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        draft_service: PublicationDraftService,
        intro_service: IntroService,
        discord: DiscordPublicationGateway,
        *,
        alerts: ModeratorAlertGateway | None = None,
        seen_emoji: str = "✅",
        max_safe_retries: int = 3,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._draft_service = draft_service
        self._intro_service = intro_service
        self._discord = discord
        self._alerts = alerts or NullModeratorAlertGateway()
        self._seen_emoji = seen_emoji
        self._max_safe_retries = max_safe_retries

    async def prepare(
        self,
        guild_id: int,
        *,
        reference_time: datetime,
        mode: PublicationMode,
        initiated_by_user_id: int | None,
        correlation_id: str,
        expected_slot_key: str | None = None,
        expected_draft_sha256: str | None = None,
        intro_override: IntroResult | None = None,
    ) -> PreparedPublication:
        base_snapshot = await self._draft_service.load_next_snapshot(
            guild_id,
            reference_time=reference_time,
            intro_text=FALLBACK_TEXT,
        )
        provisional = compose_publication(base_snapshot)
        if expected_slot_key is not None and provisional.slot_key != expected_slot_key:
            raise PublicationSlotChanged("publication slot changed")
        intro = intro_override or await self._intro_service.create(
            enabled=base_snapshot.guild.generated_intro_enabled,
            scheduled_local=provisional.scheduled_local,
            event_titles=tuple(item.title for item in provisional.public_items),
        )
        draft = compose_publication(replace(base_snapshot, intro_text=intro.text))
        if expected_draft_sha256 is not None and _draft_sha256(draft) != expected_draft_sha256:
            raise PublicationSlotChanged("publication draft changed")
        channel_id = base_snapshot.guild.announcement_channel_id
        if channel_id is None:
            raise PublicationChannelMissing("announcement channel is not configured")

        run_id = uuid.uuid4()
        run, items, messages = _snapshot_records(
            run_id=run_id,
            draft=draft,
            intro=intro,
            channel_id=channel_id,
            mode=mode,
            initiated_by_user_id=initiated_by_user_id,
            now=reference_time,
        )
        async with self._unit_of_work.transaction() as repositories:
            await repositories.publication_runs.lock_slot(guild_id, draft.slot_key)
            existing = await repositories.publication_runs.get_for_slot(guild_id, draft.slot_key)
            if existing is not None:
                existing_messages = await repositories.publication_runs.list_messages(existing.id)
                return PreparedPublication(
                    existing,
                    False,
                    len(existing_messages),
                    len(draft.public_items),
                )
            await repositories.publication_runs.add_snapshot(run, items, messages)
            await AuditWriter(repositories.audit_logs).success(
                guild_id=guild_id,
                actor_user_id=initiated_by_user_id,
                action="publication.snapshot_created",
                object_type="publication_run",
                object_id=str(run_id),
                correlation_id=correlation_id,
                after_value={
                    "slot_key": draft.slot_key,
                    "mode": mode.value,
                    "message_count": len(messages),
                    "item_count": len(items),
                    "intro_prompt_version": intro.prompt_version,
                    "intro_used_fallback": intro.used_fallback,
                },
            )
        return PreparedPublication(run, True, len(messages), len(items))

    async def preview(self, guild_id: int, *, reference_time: datetime) -> PublicationPreview:
        snapshot = await self._draft_service.load_next_snapshot(
            guild_id,
            reference_time=reference_time,
            intro_text=FALLBACK_TEXT,
        )
        provisional = compose_publication(snapshot)
        intro = await self._intro_service.create(
            enabled=snapshot.guild.generated_intro_enabled,
            scheduled_local=provisional.scheduled_local,
            event_titles=tuple(item.title for item in provisional.public_items),
        )
        draft = compose_publication(replace(snapshot, intro_text=intro.text))
        return PublicationPreview(draft, intro, snapshot.guild.announcement_channel_id)

    async def publish(
        self,
        run_id: uuid.UUID,
        *,
        correlation_id: str,
    ) -> PublicationResult:
        async with self._unit_of_work.transaction() as repositories:
            run = await repositories.publication_runs.get(run_id)
            if run is None:
                raise LookupError(f"publication run not found: {run_id}")
            messages = await repositories.publication_runs.list_messages(run_id)
            guild = await repositories.guild_configs.get(run.guild_id)
            if guild is None:
                raise LookupError(f"guild configuration not found: {run.guild_id}")
            if run.state in {
                PublicationState.SUCCEEDED_AUTOMATIC,
                PublicationState.SUCCEEDED_MANUAL,
            }:
                return PublicationResult(
                    run.id,
                    run.state,
                    tuple(
                        message.discord_message_id
                        for message in messages
                        if message.discord_message_id is not None
                    ),
                    run.warning_codes,
                )
            if any(message.state is PublicationMessageState.UNCERTAIN for message in messages):
                raise PublicationAlreadyRunning("publication requires moderator reconciliation")
            increment_attempt = run.state is not PublicationState.PREPARING
            attempt = run.attempt + (1 if increment_attempt else 0)
            await repositories.publication_runs.set_state(
                run.id,
                PublicationState.PUBLISHING,
                increment_attempt=increment_attempt,
            )
            await AuditWriter(repositories.audit_logs).success(
                guild_id=run.guild_id,
                actor_user_id=run.initiated_by_user_id,
                action="publication.attempt_started",
                object_type="publication_run",
                object_id=str(run.id),
                correlation_id=correlation_id,
                after_value={"attempt": attempt},
            )
            run = replace(run, attempt=attempt, state=PublicationState.PUBLISHING)

        sent_ids: list[int] = []
        warnings = list(run.warning_codes)
        for initial_message in messages:
            message = await self._reload_message(run.id, initial_message.id)
            if message.discord_message_id is not None:
                sent_ids.append(message.discord_message_id)
                continue
            if message.state is PublicationMessageState.SENDING:
                summary = "Výsledok predchádzajúceho odoslania nie je možné bezpečne určiť."
                await self._mark_uncertain(
                    run, message, correlation_id, summary, guild.moderator_channel_id
                )
                return PublicationResult(
                    run.id, PublicationState.PARTIALLY_PUBLISHED, tuple(sent_ids), tuple(warnings)
                )
            if message.state is PublicationMessageState.UNCERTAIN:
                return PublicationResult(
                    run.id, PublicationState.PARTIALLY_PUBLISHED, tuple(sent_ids), tuple(warnings)
                )
            claimed = await self._claim(message.id)
            if not claimed:
                raise PublicationAlreadyRunning("publication message is already being delivered")
            try:
                discord_message_id = await self._send_with_retry(
                    run, message, correlation_id=correlation_id
                )
            except DiscordAmbiguousError:
                await self._mark_uncertain(
                    run,
                    message,
                    correlation_id,
                    "Discord spojenie sa prerušilo bez potvrdenia výsledku.",
                    guild.moderator_channel_id,
                )
                return PublicationResult(
                    run.id, PublicationState.PARTIALLY_PUBLISHED, tuple(sent_ids), tuple(warnings)
                )
            except (DiscordDefinitiveError, DiscordTransientError) as exc:
                detail = _safe_error(exc)
                terminal = isinstance(exc, DiscordDefinitiveError) or (
                    run.attempt >= self._max_safe_retries
                )
                async with self._unit_of_work.transaction() as repositories:
                    if terminal:
                        await repositories.publication_runs.mark_delivery_exhausted(
                            run.id,
                            message.id,
                            correlation_id=correlation_id,
                            summary=detail,
                        )
                    else:
                        await repositories.publication_runs.mark_message_failed(
                            message.id, detail=detail
                        )
                        await repositories.publication_runs.set_state(
                            run.id,
                            PublicationState.RETRY_PENDING,
                            error_code="discord_delivery_failed",
                            error_detail=detail,
                        )
                    await AuditWriter(repositories.audit_logs).failure(
                        guild_id=run.guild_id,
                        actor_user_id=run.initiated_by_user_id,
                        action="publication.delivery_failed",
                        object_type="publication_run",
                        object_id=str(run.id),
                        correlation_id=correlation_id,
                        after_value={
                            "message_position": message.position,
                            "error_type": type(exc).__name__,
                            "terminal": terminal,
                        },
                    )
                await self._alerts.send_alert(
                    guild_id=run.guild_id,
                    moderator_channel_id=guild.moderator_channel_id,
                    title=(
                        "Carlo vyčerpal bezpečné pokusy publikovania"
                        if terminal
                        else "Publikovanie Carla čaká na opakovanie"
                    ),
                    summary=detail,
                    correlation_id=correlation_id,
                    run_id=run.id,
                )
                return PublicationResult(
                    run.id,
                    PublicationState.FAILED if terminal else PublicationState.RETRY_PENDING,
                    tuple(sent_ids),
                    tuple(warnings),
                )
            async with self._unit_of_work.transaction() as repositories:
                await repositories.publication_runs.mark_message_sent(
                    message.id,
                    discord_message_id=discord_message_id,
                    sent_at=datetime.now(UTC),
                )
            sent_ids.append(discord_message_id)

        seen_target = next((message for message in reversed(messages) if message.seen_target), None)
        seen_emoji = seen_target.reaction_emoji if seen_target is not None else None
        if seen_target is not None and sent_ids and seen_emoji is not None:
            try:
                target_id = next(
                    message_id
                    for message, message_id in zip(messages, sent_ids, strict=True)
                    if message.id == seen_target.id
                )
                await self._discord.add_reaction(
                    channel_id=seen_target.discord_channel_id,
                    message_id=target_id,
                    emoji=seen_emoji,
                )
            except Exception as exc:
                warning = "seen_reaction_failed"
                warnings.append(warning)
                async with self._unit_of_work.transaction() as repositories:
                    await repositories.publication_runs.mark_reaction_warning(
                        seen_target.id, detail=_safe_error(exc)
                    )

        completed_state = (
            PublicationState.SUCCEEDED_MANUAL
            if run.mode is PublicationMode.MANUAL
            else PublicationState.SUCCEEDED_AUTOMATIC
        )
        completed_at = datetime.now(UTC)
        async with self._unit_of_work.transaction() as repositories:
            await repositories.publication_runs.set_state(
                run.id,
                completed_state,
                completed_at=completed_at,
                warning_codes=tuple(dict.fromkeys(warnings)),
            )
            await AuditWriter(repositories.audit_logs).success(
                guild_id=run.guild_id,
                actor_user_id=run.initiated_by_user_id,
                action="publication.completed",
                object_type="publication_run",
                object_id=str(run.id),
                correlation_id=correlation_id,
                after_value={
                    "state": completed_state.value,
                    "message_ids": sent_ids,
                    "warning_codes": warnings,
                },
            )
        return PublicationResult(run.id, completed_state, tuple(sent_ids), tuple(warnings))

    async def recover(
        self, *, stale_before: datetime, correlation_id: str
    ) -> list[PublicationResult]:
        async with self._unit_of_work.transaction() as repositories:
            runs = await repositories.publication_runs.list_recoverable(
                attempted_before=stale_before
            )
        results: list[PublicationResult] = []
        for run in runs:
            results.append(await self.publish(run.id, correlation_id=correlation_id))
        return results

    async def _reload_message(
        self, run_id: uuid.UUID, message_id: uuid.UUID
    ) -> PublicationMessageRecord:
        async with self._unit_of_work.transaction() as repositories:
            messages = await repositories.publication_runs.list_messages(run_id)
        return next(message for message in messages if message.id == message_id)

    async def _claim(self, message_id: uuid.UUID) -> bool:
        async with self._unit_of_work.transaction() as repositories:
            return await repositories.publication_runs.claim_message(
                message_id, attempted_at=datetime.now(UTC)
            )

    async def _send_with_retry(
        self,
        run: PublicationRunRecord,
        message: PublicationMessageRecord,
        *,
        correlation_id: str,
    ) -> int:
        for attempt in range(1, self._max_safe_retries + 1):
            if attempt > 1:
                async with self._unit_of_work.transaction() as repositories:
                    await repositories.publication_runs.increment_message_attempt(
                        message.id, attempted_at=datetime.now(UTC)
                    )
            try:
                return await self._discord.send_message(message)
            except DiscordTransientError as exc:
                async with self._unit_of_work.transaction() as repositories:
                    await AuditWriter(repositories.audit_logs).failure(
                        guild_id=run.guild_id,
                        actor_user_id=run.initiated_by_user_id,
                        action="publication.delivery_retry",
                        object_type="publication_message",
                        object_id=str(message.id),
                        correlation_id=correlation_id,
                        after_value={
                            "message_position": message.position,
                            "attempt": message.attempt_count + attempt,
                            "will_retry": attempt < self._max_safe_retries,
                        },
                    )
                if attempt == self._max_safe_retries:
                    raise
                await asyncio.sleep(max(0.0, exc.retry_after))
        raise AssertionError("retry loop exhausted")

    async def _mark_uncertain(
        self,
        run: PublicationRunRecord,
        message: PublicationMessageRecord,
        correlation_id: str,
        summary: str,
        moderator_channel_id: int | None,
    ) -> None:
        async with self._unit_of_work.transaction() as repositories:
            await repositories.publication_runs.mark_uncertain(
                run.id,
                message.id,
                correlation_id=correlation_id,
                summary=summary,
            )
            await AuditWriter(repositories.audit_logs).failure(
                guild_id=run.guild_id,
                actor_user_id=run.initiated_by_user_id,
                action="publication.delivery_uncertain",
                object_type="publication_message",
                object_id=str(message.id),
                correlation_id=correlation_id,
                after_value={"message_position": message.position},
            )
        await self._alerts.send_alert(
            guild_id=run.guild_id,
            moderator_channel_id=moderator_channel_id,
            title="Carlo zastavil publikovanie bez rizika duplicity",
            summary=summary,
            correlation_id=correlation_id,
            run_id=run.id,
        )


def _snapshot_records(
    *,
    run_id: uuid.UUID,
    draft: PublicationDraft,
    intro: IntroResult,
    channel_id: int,
    mode: PublicationMode,
    initiated_by_user_id: int | None,
    now: datetime,
) -> tuple[
    PublicationRunRecord,
    tuple[PublicationItemRecord, ...],
    tuple[PublicationMessageRecord, ...],
]:
    warning_codes = tuple(
        [*(warning.code.value for warning in draft.warnings)]
        + ([intro.warning_code] if intro.warning_code else [])
    )
    run = PublicationRunRecord(
        id=run_id,
        guild_id=draft.guild_id,
        slot_key=draft.slot_key,
        scheduled_for=draft.scheduled_for,
        mode=mode,
        initiated_by_user_id=initiated_by_user_id,
        state=PublicationState.PREPARING,
        attempt=1,
        idempotency_key=f"publication:{draft.slot_key}",
        composer_version=draft.composer_version,
        intro_text=draft.intro_text,
        intro_prompt_version=intro.prompt_version,
        intro_used_fallback=intro.used_fallback,
        outro_text=draft.outro_text,
        warning_codes=warning_codes,
        started_at=now,
    )
    items: list[PublicationItemRecord] = [
        PublicationItemRecord(
            id=uuid.uuid4(),
            publication_run_id=run_id,
            item_type=PublicationItemType.INTRO,
            position=0,
            final_title=None,
            final_description=draft.intro_text,
        )
    ]
    items.extend(
        _item_record(run_id, item, position)
        for position, item in enumerate(draft.public_items, start=1)
    )
    if draft.outro_text is not None:
        items.append(
            PublicationItemRecord(
                id=uuid.uuid4(),
                publication_run_id=run_id,
                item_type=PublicationItemType.OUTRO,
                position=len(items),
                final_title=None,
                final_description=draft.outro_text,
            )
        )
    messages = tuple(
        PublicationMessageRecord(
            id=uuid.uuid5(run_id, f"message:{message.position}"),
            publication_run_id=run_id,
            position=message.position,
            discord_channel_id=channel_id,
            part_key=message.part_key,
            nonce=message.nonce,
            content=message.content,
            embeds=tuple(_embed_payload(embed) for embed in message.embeds),
            allowed_mentions=message.allowed_mentions,
            seen_target=message.seen_target,
            reaction_emoji=message.reaction_emoji,
        )
        for message in draft.messages
    )
    return run, tuple(items), messages


def _item_record(
    run_id: uuid.UUID, item: PublicationDraftItem, position: int
) -> PublicationItemRecord:
    source_id = uuid.UUID(item.source_id)
    item_type = PublicationItemType(item.kind.value)
    return PublicationItemRecord(
        id=uuid.uuid4(),
        publication_run_id=run_id,
        item_type=item_type,
        position=position,
        external_event_id=source_id if item_type is PublicationItemType.EXTERNAL_EVENT else None,
        manual_event_id=source_id if item_type is PublicationItemType.MANUAL_EVENT else None,
        info_announcement_id=source_id if item_type is PublicationItemType.INFO else None,
        final_title=item.title,
        final_description=item.description,
        display_time=item.display_time,
        day_emoji=item.day_emoji,
        starts_at=item.starts_at,
        ends_at=item.ends_at,
        starts_on=item.starts_on,
        ends_on=item.ends_on,
        is_all_day=item.is_all_day,
        link_url=item.link_url,
        image_url=item.image_url,
    )


def _embed_payload(embed: DiscordEmbedPlan) -> dict[str, object]:
    values = asdict(embed)  # dataclass from the pure composer
    payload: dict[str, object] = {
        "title": values["title"],
        "color": values["color"],
    }
    for source, target in (
        ("description", "description"),
        ("link_url", "url"),
    ):
        if values[source] is not None:
            payload[target] = values[source]
    if values["author_name"] is not None:
        payload["author"] = {
            "name": values["author_name"],
            **(
                {"icon_url": values["author_icon_url"]}
                if values["author_icon_url"] is not None
                else {}
            ),
        }
    if values["thumbnail_url"] is not None:
        payload["thumbnail"] = {"url": values["thumbnail_url"]}
    return payload


def _draft_sha256(draft: PublicationDraft) -> str:
    return hashlib.sha256(draft.canonical_json().encode()).hexdigest()


def _safe_error(exc: BaseException) -> str:
    return str(exc).replace("\n", " ")[:500] or type(exc).__name__
