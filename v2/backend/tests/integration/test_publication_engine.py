from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text, update

from domcek_bot.application.auth.authorization import AppRole, Principal
from domcek_bot.application.publication.engine import (
    DiscordAmbiguousError,
    DiscordTransientError,
    NullModeratorAlertGateway,
    PublicationEngine,
    PublicationGuardResult,
)
from domcek_bot.application.publication.guard import PublicationGuardService
from domcek_bot.application.publication.intro import IntroService
from domcek_bot.application.publication.manual import (
    InvalidPublishConfirmation,
    ManualPublicationDisabled,
    ManualPublicationService,
)
from domcek_bot.application.publication.recovery import PublicationRecoveryService
from domcek_bot.application.publication.scheduler import PublicationScheduler
from domcek_bot.application.publication.service import PublicationDraftService
from domcek_bot.application.records import PublicationMessageRecord
from domcek_bot.config import Settings
from domcek_bot.domain.enums import PublicationMessageState, PublicationMode, PublicationState
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.models import (
    AuditLogModel,
    Base,
    CalendarSourceModel,
    ExternalEventModel,
    GuildConfigModel,
    PublicationIncidentModel,
    PublicationMessageModel,
    PublicationRunModel,
    ReactionConfigModel,
)
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.skipif(
    "TEST_DATABASE_URL" not in os.environ,
    reason="integration database not configured",
)

GUILD_ID = 1535774834955391047
CHANNEL_ID = 1535775856281133066
USER_ID = 1535771583841439765
REFERENCE = datetime(2026, 8, 9, 18, 0, tzinfo=UTC)


@pytest.fixture
async def database() -> AsyncIterator[Database]:
    database = Database(Settings(database_url=os.environ["TEST_DATABASE_URL"]))
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    async with database.transaction() as connection:
        await connection.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))
    try:
        yield database
    finally:
        async with database.transaction() as connection:
            await connection.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))
        await database.close()


class FailingIntro:
    async def generate(self, *, prompt: str) -> str:
        del prompt
        raise RuntimeError("generator intentionally unavailable")


class CountingIntro:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, *, prompt: str) -> str:
        del prompt
        self.calls += 1
        return f"Generovaný úvod {self.calls}"


class RecordingDiscord:
    def __init__(
        self,
        *,
        transient_first: bool = False,
        always_transient: bool = False,
        ambiguous: bool = False,
        reaction_failure: bool = False,
    ) -> None:
        self.transient_first = transient_first
        self.always_transient = always_transient
        self.ambiguous = ambiguous
        self.reaction_failure = reaction_failure
        self.attempts = 0
        self.sent: list[PublicationMessageRecord] = []
        self.reactions: list[tuple[int, int, str]] = []

    async def send_message(self, message: PublicationMessageRecord) -> int:
        self.attempts += 1
        if self.ambiguous:
            raise DiscordAmbiguousError("connection dropped")
        if self.always_transient:
            raise DiscordTransientError("temporary Discord outage", retry_after=0)
        if self.transient_first and self.attempts == 1:
            raise DiscordTransientError("rate limited", retry_after=0)
        self.sent.append(message)
        return 9000 + len(self.sent)

    async def add_reaction(self, *, channel_id: int, message_id: int, emoji: str) -> None:
        if self.reaction_failure:
            raise DiscordTransientError("reaction unavailable", retry_after=0)
        self.reactions.append((channel_id, message_id, emoji))


class RecordingAlerts:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

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
        del guild_id, moderator_channel_id, summary, run_id
        self.calls.append((title, correlation_id))


class RecordingGuardDiscord:
    def __init__(self, *, admins: tuple[int, ...], fail_for: frozenset[int] = frozenset()) -> None:
        self.admins = admins
        self.fail_for = fail_for
        self.sent: list[tuple[int, uuid.UUID, str]] = []
        self.deleted: list[tuple[int, int]] = []

    async def admin_member_ids(self, guild_id: int, admin_role_id: int) -> tuple[int, ...]:
        assert guild_id == GUILD_ID
        assert admin_role_id == 777
        return self.admins

    async def send_guard_dm(
        self,
        *,
        recipient_user_id: int,
        run_id: uuid.UUID,
        release_at: datetime,
        nonce: str,
    ) -> tuple[int, int]:
        del release_at
        if recipient_user_id in self.fail_for:
            raise RuntimeError("DM disabled")
        self.sent.append((recipient_user_id, run_id, nonce))
        return recipient_user_id + 100, recipient_user_id + 200

    async def delete_guard_dm(self, *, channel_id: int, message_id: int) -> None:
        self.deleted.append((channel_id, message_id))


class ConfigurableFinalCalendarSync:
    def __init__(self, succeeds: bool = True) -> None:
        self.succeeds = succeeds
        self.calls: list[tuple[int, str]] = []

    async def synchronize_guild(self, guild_id: int, *, correlation_id: str) -> bool:
        self.calls.append((guild_id, correlation_id))
        return self.succeeds


async def _seed(database: Database, *, event_count: int, grace_seconds: int = 0) -> None:
    source_id = uuid.uuid4()
    async with database.session() as session, session.begin():
        session.add(
            GuildConfigModel(
                guild_id=GUILD_ID,
                announcement_channel_id=CHANNEL_ID,
                generated_intro_enabled=True,
                publication_grace_seconds=grace_seconds,
            )
        )
        await session.flush()
        session.add(
            CalendarSourceModel(
                id=source_id,
                guild_id=GUILD_ID,
                provider="google",
                external_calendar_id="calendar@example.test",
                display_name="Kalendár",
                last_sync_success_at=REFERENCE,
            )
        )
        await session.flush()
        for position in range(event_count):
            starts_at = datetime(2026, 8, 11, 8, 0, tzinfo=UTC) + timedelta(hours=position)
            session.add(
                ExternalEventModel(
                    id=uuid.uuid4(),
                    calendar_source_id=source_id,
                    source_key=f"event-{position}",
                    provider_event_id=f"google-{position}",
                    source_title=f"Udalosť {position:02d}",
                    is_all_day=False,
                    starts_at=starts_at,
                    ends_at=starts_at + timedelta(minutes=45),
                    last_synced_at=REFERENCE,
                )
            )


def _engine(database: Database, discord: RecordingDiscord) -> PublicationEngine:
    uow = SqlAlchemyUnitOfWork(database)
    return PublicationEngine(
        uow,
        PublicationDraftService(uow),
        IntroService(FailingIntro()),
        discord,
        max_safe_retries=3,
    )


async def test_snapshot_is_immutable_and_more_than_ten_events_publish_with_retry(
    database: Database,
) -> None:
    await _seed(database, event_count=11)
    discord = RecordingDiscord(transient_first=True)
    engine = _engine(database, discord)

    prepared = await engine.prepare(
        GUILD_ID,
        reference_time=REFERENCE,
        mode=PublicationMode.MANUAL,
        initiated_by_user_id=USER_ID,
        correlation_id="engine-many-events",
    )
    assert prepared.created
    assert prepared.message_count == 2
    assert prepared.item_count == 12  # intro + 11 events

    async with database.session() as session, session.begin():
        await session.execute(
            update(ExternalEventModel).values(source_title="Neskoršia redakčná zmena")
        )

    result = await engine.publish(prepared.run.id, correlation_id="engine-many-events")

    assert result.state is PublicationState.SUCCEEDED_MANUAL
    assert len(result.sent_message_ids) == 2
    assert discord.attempts == 3  # first safe rate-limit response plus two successful messages
    assert [len(message.embeds) for message in discord.sent] == [10, 1]
    assert discord.sent[0].embeds[0]["title"] == "Udalosť 00"
    assert discord.reactions == [(CHANNEL_ID, result.sent_message_ids[-1], "✅")]
    assert "intro_generator_failed" in result.warning_codes

    async with database.session() as session:
        run = await session.get(PublicationRunModel, prepared.run.id)
        messages = list(
            await session.scalars(
                select(PublicationMessageModel)
                .where(PublicationMessageModel.publication_run_id == prepared.run.id)
                .order_by(PublicationMessageModel.position)
            )
        )
    assert run is not None and run.intro_used_fallback
    assert run.state == PublicationState.SUCCEEDED_MANUAL.value
    assert run.attempt == 1
    assert all(message.state == PublicationMessageState.SENT.value for message in messages)
    assert [message.attempt_count for message in messages] == [2, 1]


async def test_manual_confirmation_publishes_the_exact_generated_preview(
    database: Database,
) -> None:
    await _seed(database, event_count=1)
    discord = RecordingDiscord()
    generator = CountingIntro()
    uow = SqlAlchemyUnitOfWork(database)
    engine = PublicationEngine(
        uow,
        PublicationDraftService(uow),
        IntroService(generator),
        discord,
    )
    service = ManualPublicationService(
        PublicationDraftService(uow),
        engine,
        secret="manual-preview-exact-secret-32-characters",
    )
    admin = Principal(
        guild_id=GUILD_ID,
        user_id=USER_ID,
        username="admin",
        display_name="Admin",
        avatar_url=None,
        discord_role_ids=frozenset(),
        app_roles=frozenset({AppRole.ADMIN}),
    )

    preview = await service.preview(principal=admin, now=REFERENCE)
    prepared, result = await service.confirm(
        preview.confirmation_token,
        principal=admin,
        correlation_id="exact-preview",
        now=REFERENCE + timedelta(minutes=1),
    )

    assert preview.draft.intro_text == "Generovaný úvod 1"
    assert generator.calls == 1
    assert prepared.run.intro_text == preview.draft.intro_text
    assert result.state is PublicationState.SUCCEEDED_MANUAL
    assert discord.sent[0].content == preview.draft.messages[0].content


async def test_manual_publication_policy_blocks_preview_and_confirm_without_discord_effect(
    database: Database,
) -> None:
    await _seed(database, event_count=1)
    discord = RecordingDiscord()
    uow = SqlAlchemyUnitOfWork(database)
    draft_service = PublicationDraftService(uow)
    engine = PublicationEngine(uow, draft_service, IntroService(None), discord)
    enabled = ManualPublicationService(
        draft_service,
        engine,
        secret="manual-policy-test-secret-with-32-characters",
    )
    blocked = ManualPublicationService(
        draft_service,
        engine,
        secret="manual-policy-test-secret-with-32-characters",
        publication_enabled=False,
    )
    publisher = Principal(
        guild_id=GUILD_ID,
        user_id=USER_ID,
        username="publisher",
        display_name="Publisher",
        avatar_url=None,
        discord_role_ids=frozenset(),
        app_roles=frozenset({AppRole.PUBLISHER}),
    )
    token = (await enabled.preview(principal=publisher, now=REFERENCE)).confirmation_token

    with pytest.raises(ManualPublicationDisabled):
        await blocked.preview(principal=publisher, now=REFERENCE)
    safe_preview = await blocked.preview(
        principal=publisher,
        now=REFERENCE,
        for_publication=False,
    )
    assert safe_preview.message_count == 1
    with pytest.raises(ManualPublicationDisabled):
        await blocked.confirm(
            token,
            principal=publisher,
            correlation_id="manual-policy-blocked",
            now=REFERENCE,
        )

    assert discord.attempts == 0
    async with database.session() as session:
        assert list(await session.scalars(select(PublicationRunModel))) == []


async def test_ambiguous_discord_effect_stops_and_creates_reconcile_incident(
    database: Database,
) -> None:
    await _seed(database, event_count=1)
    discord = RecordingDiscord(ambiguous=True)
    engine = _engine(database, discord)
    prepared = await engine.prepare(
        GUILD_ID,
        reference_time=REFERENCE,
        mode=PublicationMode.AUTOMATIC,
        initiated_by_user_id=None,
        correlation_id="engine-ambiguous",
    )

    result = await engine.publish(prepared.run.id, correlation_id="engine-ambiguous")

    assert result.state is PublicationState.PARTIALLY_PUBLISHED
    async with database.session() as session:
        run = await session.get(PublicationRunModel, prepared.run.id)
        message = (
            await session.scalars(
                select(PublicationMessageModel).where(
                    PublicationMessageModel.publication_run_id == prepared.run.id
                )
            )
        ).one()
        incidents = list(
            await session.scalars(
                select(PublicationIncidentModel).where(
                    PublicationIncidentModel.publication_run_id == prepared.run.id
                )
            )
        )
    assert run is not None and run.state == PublicationState.PARTIALLY_PUBLISHED.value
    assert message.state == PublicationMessageState.UNCERTAIN.value
    assert len(incidents) == 1
    assert incidents[0].correlation_id == "engine-ambiguous"

    discord.ambiguous = False
    uow = SqlAlchemyUnitOfWork(database)
    recovery = PublicationRecoveryService(uow, engine)
    recovered = await recovery.mark_existing_and_continue(
        prepared.run.id,
        message_position=0,
        discord_message_id=777777,
        principal=Principal(
            guild_id=GUILD_ID,
            user_id=USER_ID,
            username="admin",
            display_name="Admin",
            avatar_url=None,
            discord_role_ids=frozenset(),
            app_roles=frozenset({AppRole.ADMIN}),
        ),
        correlation_id="engine-reconciled",
        now=REFERENCE + timedelta(minutes=1),
    )
    assert recovered.state is PublicationState.SUCCEEDED_AUTOMATIC
    assert recovered.sent_message_ids == (777777,)

    async with database.session() as session:
        incident = (
            await session.scalars(
                select(PublicationIncidentModel).where(
                    PublicationIncidentModel.publication_run_id == prepared.run.id
                )
            )
        ).one()
    assert incident.state == "resolved"
    assert incident.resolution == "existing_message_linked"
    async with database.session() as session:
        recovered_run = await session.get(PublicationRunModel, prepared.run.id)
    assert recovered_run is not None and recovered_run.attempt == 2


async def test_recovery_does_not_claim_run_with_a_fresh_sending_message(
    database: Database,
) -> None:
    await _seed(database, event_count=11)
    engine = _engine(database, RecordingDiscord())
    prepared = await engine.prepare(
        GUILD_ID,
        reference_time=REFERENCE,
        mode=PublicationMode.AUTOMATIC,
        initiated_by_user_id=None,
        correlation_id="fresh-active-send",
    )
    assert prepared.message_count == 2
    async with database.session() as session, session.begin():
        await session.execute(
            update(PublicationRunModel)
            .where(PublicationRunModel.id == prepared.run.id)
            .values(state=PublicationState.PUBLISHING.value)
        )
        await session.execute(
            update(PublicationMessageModel)
            .where(
                PublicationMessageModel.publication_run_id == prepared.run.id,
                PublicationMessageModel.position == 0,
            )
            .values(
                state=PublicationMessageState.SENDING.value,
                last_attempt_at=REFERENCE,
            )
        )

    uow = SqlAlchemyUnitOfWork(database)
    async with uow.transaction() as repositories:
        fresh = await repositories.publication_runs.list_recoverable(
            attempted_before=REFERENCE - timedelta(seconds=90)
        )
    assert fresh == []

    async with uow.transaction() as repositories:
        stale = await repositories.publication_runs.list_recoverable(
            attempted_before=REFERENCE + timedelta(seconds=1)
        )
    assert [run.id for run in stale] == [prepared.run.id]


async def test_transient_delivery_has_bounded_run_attempts_and_terminal_incident(
    database: Database,
) -> None:
    await _seed(database, event_count=1)
    discord = RecordingDiscord(always_transient=True)
    alerts = RecordingAlerts()
    engine = PublicationEngine(
        SqlAlchemyUnitOfWork(database),
        PublicationDraftService(SqlAlchemyUnitOfWork(database)),
        IntroService(None),
        discord,
        alerts=alerts,
        max_safe_retries=3,
    )
    prepared = await engine.prepare(
        GUILD_ID,
        reference_time=REFERENCE,
        mode=PublicationMode.AUTOMATIC,
        initiated_by_user_id=None,
        correlation_id="bounded-retry",
    )
    first = await engine.publish(prepared.run.id, correlation_id="bounded-retry-1")
    assert first.state is PublicationState.RETRY_PENDING

    scheduler = PublicationScheduler(
        SqlAlchemyUnitOfWork(database),
        engine,
        alerts,
        grace_period=timedelta(hours=2),
        calendar_max_safe_age=timedelta(days=2),
        final_calendar_sync=ConfigurableFinalCalendarSync(),
    )
    due = datetime(2026, 8, 10, 18, 30, tzinfo=UTC)
    second = await scheduler.run_due(now=due, correlation_id="bounded-retry-2")
    third = await scheduler.run_due(now=due, correlation_id="bounded-retry-3")
    fourth = await scheduler.run_due(now=due, correlation_id="bounded-retry-4")

    assert [decision.action for decision in second] == [PublicationState.RETRY_PENDING.value]
    assert [decision.action for decision in third] == [PublicationState.FAILED.value]
    assert [decision.action for decision in fourth] == ["publication_failed_requires_admin"]
    assert discord.attempts == 9
    assert sum("vyčerpal" in title for title, _ in alerts.calls) == 1
    async with database.session() as session:
        run = await session.get(PublicationRunModel, prepared.run.id)
        incidents = list(
            await session.scalars(
                select(PublicationIncidentModel).where(
                    PublicationIncidentModel.publication_run_id == prepared.run.id,
                    PublicationIncidentModel.state == "open",
                )
            )
        )
    assert run is not None and run.state == PublicationState.FAILED.value
    assert run.attempt == 3
    assert len(incidents) == 1
    assert incidents[0].kind == "discord_delivery_exhausted"


async def test_seen_reaction_is_snapshotted_from_guild_configuration(database: Database) -> None:
    await _seed(database, event_count=1)
    async with database.session() as session, session.begin():
        session.add(
            ReactionConfigModel(
                guild_id=GUILD_ID,
                seen_enabled=True,
                seen_emoji_id=778899,
            )
        )
    discord = RecordingDiscord()
    engine = _engine(database, discord)
    prepared = await engine.prepare(
        GUILD_ID,
        reference_time=REFERENCE,
        mode=PublicationMode.MANUAL,
        initiated_by_user_id=USER_ID,
        correlation_id="configured-seen",
    )
    async with database.session() as session, session.begin():
        config = await session.get(ReactionConfigModel, GUILD_ID)
        assert config is not None
        config.seen_emoji_id = None
        config.seen_emoji_unicode = "❌"
    await engine.publish(prepared.run.id, correlation_id="configured-seen")
    assert discord.reactions == [(CHANNEL_ID, 9001, "_:778899")]


async def test_seen_reaction_failure_is_persisted_as_warning_not_publication_failure(
    database: Database,
) -> None:
    await _seed(database, event_count=1)
    discord = RecordingDiscord(reaction_failure=True)
    engine = _engine(database, discord)
    prepared = await engine.prepare(
        GUILD_ID,
        reference_time=REFERENCE,
        mode=PublicationMode.AUTOMATIC,
        initiated_by_user_id=None,
        correlation_id="seen-warning",
    )
    result = await engine.publish(prepared.run.id, correlation_id="seen-warning")

    assert result.state is PublicationState.SUCCEEDED_AUTOMATIC
    assert result.warning_codes == ("intro_generator_failed", "seen_reaction_failed")
    async with database.session() as session:
        run = await session.get(PublicationRunModel, prepared.run.id)
        message = (
            await session.scalars(
                select(PublicationMessageModel).where(
                    PublicationMessageModel.publication_run_id == prepared.run.id
                )
            )
        ).one()
    assert run is not None and "seen_reaction_failed" in run.warning_codes
    assert message.state == PublicationMessageState.SENT.value
    assert message.reaction_error == "reaction unavailable"


async def test_successful_manual_run_skips_exactly_the_same_scheduler_slot(
    database: Database,
) -> None:
    await _seed(database, event_count=1)
    discord = RecordingDiscord()
    engine = _engine(database, discord)
    manual = await engine.prepare(
        GUILD_ID,
        reference_time=REFERENCE,
        mode=PublicationMode.MANUAL,
        initiated_by_user_id=USER_ID,
        correlation_id="manual-before-slot",
    )
    await engine.publish(manual.run.id, correlation_id="manual-before-slot")

    scheduler = PublicationScheduler(
        SqlAlchemyUnitOfWork(database),
        engine,
        NullModeratorAlertGateway(),
        grace_period=timedelta(hours=2),
        calendar_max_safe_age=timedelta(days=2),
        final_calendar_sync=ConfigurableFinalCalendarSync(),
    )
    decisions = await scheduler.run_due(
        now=datetime(2026, 8, 10, 18, 30, tzinfo=UTC),
        correlation_id="scheduled-after-manual",
    )

    assert [decision.action for decision in decisions] == ["skipped_after_manual"]
    assert len(discord.sent) == 1


async def test_publication_guard_is_durable_stoppable_and_releasable(
    database: Database,
) -> None:
    await _seed(database, event_count=1, grace_seconds=30)
    discord = RecordingDiscord()
    engine = _engine(database, discord)
    prepared = await engine.prepare(
        GUILD_ID,
        reference_time=REFERENCE,
        mode=PublicationMode.MANUAL,
        initiated_by_user_id=USER_ID,
        correlation_id="guard-prepare",
    )

    waiting = await engine.begin_guard(
        prepared.run.id,
        correlation_id="guard-start",
        now=REFERENCE,
    )
    assert isinstance(waiting, PublicationGuardResult)
    assert waiting.state is PublicationState.WAITING_FOR_RELEASE
    assert waiting.release_at == REFERENCE + timedelta(seconds=30)
    assert discord.sent == []

    still_waiting = await engine.release_guard(
        prepared.run.id,
        correlation_id="guard-too-early",
        now=REFERENCE + timedelta(seconds=29),
    )
    assert still_waiting.state is PublicationState.WAITING_FOR_RELEASE
    assert discord.sent == []

    stopped = await engine.cancel_guard(
        prepared.run.id,
        correlation_id="guard-stop",
        actor_user_id=USER_ID,
        now=REFERENCE + timedelta(seconds=29),
    )
    replayed_stop = await engine.cancel_guard(
        prepared.run.id,
        correlation_id="guard-stop-replay",
        actor_user_id=USER_ID,
        now=REFERENCE + timedelta(seconds=29),
    )
    assert stopped.state is replayed_stop.state is PublicationState.CANCELLED
    assert discord.sent == []


async def test_publication_guard_releases_exactly_once_after_restart_boundary(
    database: Database,
) -> None:
    await _seed(database, event_count=1, grace_seconds=30)
    discord = RecordingDiscord()
    first_engine = _engine(database, discord)
    prepared = await first_engine.prepare(
        GUILD_ID,
        reference_time=REFERENCE,
        mode=PublicationMode.MANUAL,
        initiated_by_user_id=USER_ID,
        correlation_id="guard-restart-prepare",
    )
    waiting = await first_engine.begin_guard(
        prepared.run.id,
        correlation_id="guard-restart-start",
        now=REFERENCE,
    )
    assert waiting.state is PublicationState.WAITING_FOR_RELEASE

    restarted_engine = _engine(database, discord)
    published = await restarted_engine.release_guard(
        prepared.run.id,
        correlation_id="guard-restart-release",
        now=REFERENCE + timedelta(seconds=31),
    )
    replay = await restarted_engine.release_guard(
        prepared.run.id,
        correlation_id="guard-restart-replay",
        now=REFERENCE + timedelta(seconds=32),
    )
    assert published.state is replay.state is PublicationState.SUCCEEDED_MANUAL
    assert len(discord.sent) == 1


async def test_automatic_guard_notifies_fresh_admins_and_extra_recipients_once(
    database: Database,
) -> None:
    await _seed(database, event_count=1, grace_seconds=30)
    extra_recipient = USER_ID + 2
    async with database.session() as session, session.begin():
        await session.execute(
            update(GuildConfigModel)
            .where(GuildConfigModel.guild_id == GUILD_ID)
            .values(
                admin_role_id=777,
                publication_guard_recipient_ids=[extra_recipient],
                moderator_channel_id=CHANNEL_ID + 1,
            )
        )
    discord = RecordingDiscord()
    engine = _engine(database, discord)
    prepared = await engine.prepare(
        GUILD_ID,
        reference_time=REFERENCE,
        mode=PublicationMode.AUTOMATIC,
        initiated_by_user_id=None,
        correlation_id="guard-notice-prepare",
    )
    await engine.begin_guard(
        prepared.run.id,
        correlation_id="guard-notice-start",
        now=REFERENCE,
    )
    guard_discord = RecordingGuardDiscord(admins=(USER_ID,))
    guard = PublicationGuardService(
        SqlAlchemyUnitOfWork(database), engine, guard_discord, RecordingAlerts()
    )

    first = await guard.notify(prepared.run.id, correlation_id="guard-notice-first")
    second = await guard.notify(prepared.run.id, correlation_id="guard-notice-second")

    assert first == 2
    assert second == 0
    assert [recipient for recipient, _, _ in guard_discord.sent] == [USER_ID, extra_recipient]
    assert len({nonce for _, _, nonce in guard_discord.sent}) == 2


async def test_guard_dm_failure_alerts_but_does_not_block_release(
    database: Database,
) -> None:
    await _seed(database, event_count=1, grace_seconds=30)
    async with database.session() as session, session.begin():
        await session.execute(
            update(GuildConfigModel)
            .where(GuildConfigModel.guild_id == GUILD_ID)
            .values(admin_role_id=777, moderator_channel_id=CHANNEL_ID + 1)
        )
    discord = RecordingDiscord()
    engine = _engine(database, discord)
    prepared = await engine.prepare(
        GUILD_ID,
        reference_time=REFERENCE,
        mode=PublicationMode.AUTOMATIC,
        initiated_by_user_id=None,
        correlation_id="guard-failed-dm-prepare",
    )
    await engine.begin_guard(
        prepared.run.id,
        correlation_id="guard-failed-dm-start",
        now=REFERENCE,
    )
    alerts = RecordingAlerts()
    guard = PublicationGuardService(
        SqlAlchemyUnitOfWork(database),
        engine,
        RecordingGuardDiscord(admins=(USER_ID,), fail_for=frozenset({USER_ID})),
        alerts,
    )

    assert await guard.notify(prepared.run.id, correlation_id="guard-failed-dm") == 0
    released = await guard.release_due(
        now=REFERENCE + timedelta(seconds=31),
        correlation_id="guard-failed-dm-release",
    )

    assert released[0].state is PublicationState.SUCCEEDED_AUTOMATIC
    assert len(discord.sent) == 1
    assert alerts.calls == [("Ochranná správa sa nedoručila", "guard-failed-dm")]


async def test_dm_stop_reloads_admin_membership_and_cleans_up_notices(
    database: Database,
) -> None:
    await _seed(database, event_count=1, grace_seconds=30)
    async with database.session() as session, session.begin():
        await session.execute(
            update(GuildConfigModel)
            .where(GuildConfigModel.guild_id == GUILD_ID)
            .values(admin_role_id=777)
        )
    discord = RecordingDiscord()
    engine = _engine(database, discord)
    prepared = await engine.prepare(
        GUILD_ID,
        reference_time=REFERENCE,
        mode=PublicationMode.AUTOMATIC,
        initiated_by_user_id=None,
        correlation_id="guard-dm-stop-prepare",
    )
    await engine.begin_guard(
        prepared.run.id,
        correlation_id="guard-dm-stop-start",
        now=REFERENCE,
    )
    guard_discord = RecordingGuardDiscord(admins=(USER_ID,))
    guard = PublicationGuardService(
        SqlAlchemyUnitOfWork(database), engine, guard_discord, RecordingAlerts()
    )
    await guard.notify(prepared.run.id, correlation_id="guard-dm-stop-notify")

    guard_discord.admins = ()
    with pytest.raises(PermissionError):
        await guard.stop_for_user(
            guild_id=GUILD_ID,
            user_id=USER_ID,
            correlation_id="guard-stale-admin",
            now=REFERENCE + timedelta(seconds=10),
        )
    guard_discord.admins = (USER_ID,)
    stopped = await guard.stop_for_user(
        guild_id=GUILD_ID,
        user_id=USER_ID,
        correlation_id="guard-fresh-admin",
        now=REFERENCE + timedelta(seconds=10),
    )

    assert stopped.state is PublicationState.CANCELLED
    assert guard_discord.deleted == [(USER_ID + 100, USER_ID + 200)]
    assert discord.sent == []


async def test_manual_confirmation_is_user_bound_short_lived_and_not_replayable(
    database: Database,
) -> None:
    await _seed(database, event_count=1)
    discord = RecordingDiscord()
    engine = _engine(database, discord)
    service = ManualPublicationService(
        PublicationDraftService(SqlAlchemyUnitOfWork(database)),
        engine,
        secret="manual-confirmation-test-secret-32-characters",
        lifetime=timedelta(minutes=5),
    )
    publisher = Principal(
        guild_id=GUILD_ID,
        user_id=USER_ID,
        username="publisher",
        display_name="Publisher",
        avatar_url=None,
        discord_role_ids=frozenset(),
        app_roles=frozenset({AppRole.PUBLISHER}),
    )
    preview = await service.preview(principal=publisher, now=REFERENCE)
    assert preview.announcement_channel_id == CHANNEL_ID
    assert preview.announcement_count == 1
    assert preview.draft.messages[0].allowed_mentions == ("everyone",)

    other_user = Principal(
        guild_id=GUILD_ID,
        user_id=USER_ID + 1,
        username="other",
        display_name="Other",
        avatar_url=None,
        discord_role_ids=frozenset(),
        app_roles=frozenset({AppRole.PUBLISHER}),
    )
    with pytest.raises(InvalidPublishConfirmation, match="another user"):
        await service.confirm(
            preview.confirmation_token,
            principal=other_user,
            correlation_id="wrong-user",
            now=REFERENCE,
        )
    with pytest.raises(InvalidPublishConfirmation, match="expired"):
        await service.confirm(
            preview.confirmation_token,
            principal=publisher,
            correlation_id="expired",
            now=REFERENCE + timedelta(minutes=6),
        )

    _, result = await service.confirm(
        preview.confirmation_token,
        principal=publisher,
        correlation_id="valid-confirmation",
        now=REFERENCE + timedelta(minutes=1),
    )
    assert result.state is PublicationState.SUCCEEDED_MANUAL
    with pytest.raises(InvalidPublishConfirmation, match="slot changed"):
        await service.confirm(
            preview.confirmation_token,
            principal=publisher,
            correlation_id="replay",
            now=REFERENCE + timedelta(minutes=2),
        )

    async with database.session() as session:
        runs = list(await session.scalars(select(PublicationRunModel)))
    assert len(runs) == 1


async def test_missed_slot_alert_is_deduplicated_across_worker_polls(
    database: Database,
) -> None:
    await _seed(database, event_count=1)
    alerts = RecordingAlerts()
    scheduler = PublicationScheduler(
        SqlAlchemyUnitOfWork(database),
        _engine(database, RecordingDiscord()),
        alerts,
        grace_period=timedelta(hours=2),
        calendar_max_safe_age=timedelta(days=2),
        final_calendar_sync=ConfigurableFinalCalendarSync(),
    )
    checked_at = datetime(2026, 8, 9, 21, 30, tzinfo=UTC)

    first = await scheduler.run_due(now=checked_at, correlation_id="missed-first")
    second = await scheduler.run_due(now=checked_at, correlation_id="missed-second")

    assert first[0].action == second[0].action == "outside_grace"
    assert alerts.calls == [("Carlo nepublikoval starý zmeškaný termín", "missed-first")]


async def test_upcoming_publication_reminder_is_configured_and_deduplicated(
    database: Database,
) -> None:
    await _seed(database, event_count=1)
    async with database.session() as session, session.begin():
        await session.execute(
            update(GuildConfigModel)
            .where(GuildConfigModel.guild_id == GUILD_ID)
            .values(
                alert_publication_reminder_enabled=True,
                moderator_channel_id=987654321,
            )
        )
    alerts = RecordingAlerts()
    scheduler = PublicationScheduler(
        SqlAlchemyUnitOfWork(database),
        _engine(database, RecordingDiscord()),
        RecordingAlerts(),
        grace_period=timedelta(hours=2),
        calendar_max_safe_age=timedelta(days=2),
        final_calendar_sync=ConfigurableFinalCalendarSync(),
        reminder_alerts=alerts,
        reminder_lead=timedelta(hours=24),
    )
    checked_at = datetime(2026, 8, 9, 18, 30, tzinfo=UTC)

    first = await scheduler.send_upcoming_reminders(now=checked_at, correlation_id="reminder-first")
    second = await scheduler.send_upcoming_reminders(
        now=checked_at, correlation_id="reminder-second"
    )

    assert first[0].action == "reminder_sent"
    assert second[0].action == "reminder_already_sent"
    assert alerts.calls == [("Blíži sa automatické publikovanie", "reminder-first")]


async def test_due_scheduler_publishes_once_with_fresh_calendar(
    database: Database,
) -> None:
    await _seed(database, event_count=1)
    discord = RecordingDiscord()
    engine = _engine(database, discord)
    scheduler = PublicationScheduler(
        SqlAlchemyUnitOfWork(database),
        engine,
        RecordingAlerts(),
        grace_period=timedelta(hours=2),
        calendar_max_safe_age=timedelta(days=2),
        final_calendar_sync=ConfigurableFinalCalendarSync(),
    )
    checked_at = datetime(2026, 8, 10, 18, 30, tzinfo=UTC)

    first = await scheduler.run_due(now=checked_at, correlation_id="automatic-first")
    second = await scheduler.run_due(now=checked_at, correlation_id="automatic-second")

    assert first[0].action == PublicationState.SUCCEEDED_AUTOMATIC.value
    assert second[0].action == "already_materialized"
    assert len(discord.sent) == 1


async def test_due_scheduler_requires_final_sync_or_explicit_fresh_cache_opt_in(
    database: Database,
) -> None:
    await _seed(database, event_count=1)
    discord = RecordingDiscord()
    final_sync = ConfigurableFinalCalendarSync(succeeds=False)
    scheduler = PublicationScheduler(
        SqlAlchemyUnitOfWork(database),
        _engine(database, discord),
        RecordingAlerts(),
        grace_period=timedelta(hours=2),
        calendar_max_safe_age=timedelta(days=2),
        final_calendar_sync=final_sync,
    )
    checked_at = datetime(2026, 8, 10, 18, 30, tzinfo=UTC)

    blocked = await scheduler.run_due(now=checked_at, correlation_id="final-sync-blocked")

    assert blocked[0].action == "final_calendar_sync_failed"
    assert discord.sent == []
    async with database.session() as session, session.begin():
        await session.execute(
            update(GuildConfigModel)
            .where(GuildConfigModel.guild_id == GUILD_ID)
            .values(allow_stale_calendar_cache=True)
        )

    allowed = await scheduler.run_due(now=checked_at, correlation_id="final-sync-opt-in")

    assert allowed[0].action == PublicationState.SUCCEEDED_AUTOMATIC.value
    assert len(discord.sent) == 1
    assert final_sync.calls == [
        (GUILD_ID, "final-sync-blocked"),
        (GUILD_ID, "final-sync-opt-in"),
    ]
    async with database.session() as session:
        audit_actions = list(
            await session.scalars(
                select(AuditLogModel.action).where(
                    AuditLogModel.action == "publication.stale_calendar_cache_accepted"
                )
            )
        )
    assert audit_actions == ["publication.stale_calendar_cache_accepted"]


async def test_two_scheduler_instances_cannot_duplicate_the_same_slot(
    database: Database,
) -> None:
    await _seed(database, event_count=1)
    discord = RecordingDiscord()
    first_engine = _engine(database, discord)
    second_engine = _engine(database, discord)
    first_scheduler = PublicationScheduler(
        SqlAlchemyUnitOfWork(database),
        first_engine,
        RecordingAlerts(),
        grace_period=timedelta(hours=2),
        calendar_max_safe_age=timedelta(days=2),
        final_calendar_sync=ConfigurableFinalCalendarSync(),
    )
    second_scheduler = PublicationScheduler(
        SqlAlchemyUnitOfWork(database),
        second_engine,
        RecordingAlerts(),
        grace_period=timedelta(hours=2),
        calendar_max_safe_age=timedelta(days=2),
        final_calendar_sync=ConfigurableFinalCalendarSync(),
    )
    checked_at = datetime(2026, 8, 10, 18, 30, tzinfo=UTC)

    decisions = await asyncio.gather(
        first_scheduler.run_due(now=checked_at, correlation_id="worker-one"),
        second_scheduler.run_due(now=checked_at, correlation_id="worker-two"),
    )

    assert len(discord.sent) == 1
    assert all(batch[0].run_id is not None for batch in decisions)
    assert decisions[0][0].run_id == decisions[1][0].run_id
    async with database.session() as session:
        runs = list(await session.scalars(select(PublicationRunModel)))
    assert len(runs) == 1
    assert runs[0].state == PublicationState.SUCCEEDED_AUTOMATIC.value
