from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text

from domcek_bot.application.auth.authorization import AppRole, AuthorizationDenied, Principal
from domcek_bot.application.channels import (
    ArchiveDecisionConflict,
    ChannelManagementService,
    ChannelOperationError,
    CreatedChannel,
    archive_channel_name,
    normalize_channel_emoji,
    normalize_channel_name,
)
from domcek_bot.application.records import GuildConfigRecord
from domcek_bot.config import Settings
from domcek_bot.domain.enums import ArchiveState
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.models import Base, ChannelArchiveRequestModel, IntegrationTaskModel
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.skipif(
    "TEST_DATABASE_URL" not in os.environ,
    reason="integration database not configured",
)

GUILD_ID = 1535774834955391047
USER_ID = 1535771583841439765
PROJECTS_CATEGORY = 1535776011872903208
ARCHIVE_CATEGORY = 1535776178097492048
NOW = datetime(2026, 8, 9, 20, 0, tzinfo=UTC)


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


class RecordingChannels:
    def __init__(self) -> None:
        self.created: list[tuple[str, tuple[int, ...], tuple[int, ...]]] = []
        self.archived: list[tuple[int, str]] = []
        self.channel_names = {7000: "projekt-alfa"}
        self.channel_categories: dict[int, int | None] = {7000: PROJECTS_CATEGORY}
        self.ambiguous_after_archive = False
        self.crash_after_create = False
        self.created_markers: dict[str, CreatedChannel] = {}

    async def get_text_channel(self, *, guild_id: int, channel_id: int) -> CreatedChannel:
        assert guild_id == GUILD_ID
        name = self.channel_names.get(channel_id)
        if name is None:
            raise RuntimeError("channel unavailable")
        return CreatedChannel(
            channel_id,
            name,
            f"https://discord.test/channels/{guild_id}/{channel_id}",
            self.channel_categories[channel_id],
        )

    async def create_text_channel(
        self,
        *,
        guild_id: int,
        category_id: int,
        name: str,
        member_ids: tuple[int, ...],
        role_ids: tuple[int, ...],
        operation_marker: str,
        reason: str,
    ) -> CreatedChannel:
        assert guild_id == GUILD_ID
        assert category_id == PROJECTS_CATEGORY
        assert reason.startswith("Carlo request")
        self.created.append((name, member_ids, role_ids))
        created = CreatedChannel(
            5000,
            name,
            f"https://discord.test/channels/{guild_id}/5000",
            category_id,
        )
        self.created_markers[operation_marker] = created
        if self.crash_after_create:
            self.crash_after_create = False
            raise SimulatedProcessCrash
        return created

    async def find_created_text_channel(
        self,
        *,
        guild_id: int,
        category_id: int,
        operation_marker: str,
    ) -> CreatedChannel | None:
        assert guild_id == GUILD_ID
        created = self.created_markers.get(operation_marker)
        if created is not None and created.category_id != category_id:
            return None
        return created

    async def archive_text_channel(
        self,
        *,
        guild_id: int,
        channel_id: int,
        archive_category_id: int,
        archived_name: str,
        reason: str,
    ) -> CreatedChannel:
        assert guild_id == GUILD_ID
        assert archive_category_id == ARCHIVE_CATEGORY
        assert reason.startswith("Carlo archive")
        self.archived.append((channel_id, archived_name))
        self.channel_names[channel_id] = archived_name
        self.channel_categories[channel_id] = archive_category_id
        if self.ambiguous_after_archive:
            raise RuntimeError("connection lost after Discord applied the change")
        return CreatedChannel(
            channel_id,
            archived_name,
            "https://discord.test/archived",
            archive_category_id,
        )


def _principal(role: AppRole, user_id: int = USER_ID) -> Principal:
    return Principal(
        guild_id=GUILD_ID,
        user_id=user_id,
        username=role.value,
        display_name=role.value,
        avatar_url=None,
        discord_role_ids=frozenset(),
        app_roles=frozenset({role}),
    )


class SimulatedProcessCrash(BaseException):
    pass


async def _service(database: Database) -> tuple[ChannelManagementService, RecordingChannels]:
    uow = SqlAlchemyUnitOfWork(database)
    async with uow.transaction() as repositories:
        await repositories.guild_configs.add(
            GuildConfigRecord(
                guild_id=GUILD_ID,
                projects_category_id=PROJECTS_CATEGORY,
                archive_category_id=ARCHIVE_CATEGORY,
            )
        )
    gateway = RecordingChannels()
    return ChannelManagementService(uow, gateway), gateway


async def test_channel_creation_is_normalized_authorized_and_idempotent(
    database: Database,
) -> None:
    service, gateway = await _service(database)
    team_mod = _principal(AppRole.TEAM_MOD)

    first = await service.create_channel(
        name="  Nový Žltý Projekt  ",
        member_ids=(11, 11, 12),
        role_ids=(21,),
        idempotency_key="interaction-123",
        principal=team_mod,
        correlation_id="channel-first",
        emoji="🛠️",
        now=NOW,
    )
    replay = await service.create_channel(
        name="iný názov sa už nepoužije",
        member_ids=(),
        role_ids=(),
        idempotency_key="interaction-123",
        principal=team_mod,
        correlation_id="channel-replay",
        now=NOW,
    )

    assert first == replay
    assert first.name == "🛠️・novy-zlty-projekt"
    assert gateway.created == [("🛠️・novy-zlty-projekt", (USER_ID, 11, 12), (21,))]
    with pytest.raises(AuthorizationDenied):
        await service.create_channel(
            name="zakázané",
            member_ids=(),
            role_ids=(),
            idempotency_key="publisher-attempt",
            principal=_principal(AppRole.PUBLISHER),
            correlation_id="publisher",
            now=NOW,
        )

    async with database.session() as session:
        tasks = list(await session.scalars(select(IntegrationTaskModel)))
    assert len(tasks) == 1
    assert tasks[0].result_value == {
        "channel_id": 5000,
        "name": "🛠️・novy-zlty-projekt",
        "jump_url": f"https://discord.test/channels/{GUILD_ID}/5000",
        "category_id": PROJECTS_CATEGORY,
    }
    assert normalize_channel_emoji("  🏡  ") == "🏡"


async def test_channel_creation_recovers_crash_after_discord_without_duplicate(
    database: Database,
) -> None:
    service, gateway = await _service(database)
    gateway.crash_after_create = True
    team_mod = _principal(AppRole.TEAM_MOD)

    with pytest.raises(SimulatedProcessCrash):
        await service.create_channel(
            name="Projekt po páde",
            member_ids=(),
            role_ids=(),
            idempotency_key="crash-recovery-key",
            principal=team_mod,
            correlation_id="before-crash",
            now=NOW,
        )

    recovered = await service.create_channel(
        name="Projekt po páde",
        member_ids=(),
        role_ids=(),
        idempotency_key="crash-recovery-key",
        principal=team_mod,
        correlation_id="after-crash",
        now=NOW + timedelta(seconds=1),
    )

    assert recovered.channel_id == 5000
    assert len(gateway.created) == 1
    async with database.session() as session:
        task = (await session.scalars(select(IntegrationTaskModel))).one()
    assert task.state == "succeeded"
    assert task.result_value is not None
    assert task.result_value["channel_id"] == 5000


async def test_archive_request_is_single_use_and_requires_fresh_admin_authorization(
    database: Database,
) -> None:
    service, gateway = await _service(database)
    request = await service.request_archive(
        channel_id=7000,
        reason="Projekt je dokončený.",
        principal=_principal(AppRole.TEAM_MOD),
        correlation_id="archive-request",
        now=NOW,
    )
    duplicate = await service.request_archive(
        channel_id=7000,
        reason="Iný text nesmie vytvoriť druhú žiadosť.",
        principal=_principal(AppRole.TEAM_MOD),
        correlation_id="archive-duplicate",
        now=NOW,
    )
    assert duplicate.id == request.id
    with pytest.raises(AuthorizationDenied):
        await service.decide_archive(
            request.id,
            approve=True,
            principal=_principal(AppRole.TEAM_MOD),
            correlation_id="not-admin",
            now=NOW,
        )

    result = await service.decide_archive(
        request.id,
        approve=True,
        principal=_principal(AppRole.ADMIN, USER_ID + 10),
        correlation_id="archive-approved",
        now=NOW + timedelta(minutes=1),
    )
    assert result.state is ArchiveState.EXECUTED
    assert gateway.archived == [(7000, "projekt-alfa-2026-08-09")]
    with pytest.raises(ArchiveDecisionConflict, match="already decided"):
        await service.decide_archive(
            request.id,
            approve=False,
            principal=_principal(AppRole.ADMIN, USER_ID + 10),
            correlation_id="second-click",
            now=NOW + timedelta(minutes=2),
        )

    async with database.session() as session:
        stored = await session.get(ChannelArchiveRequestModel, request.id)
    assert stored is not None and stored.state == ArchiveState.EXECUTED.value


async def test_archive_recovery_reconciles_effect_applied_before_process_failure(
    database: Database,
) -> None:
    service, gateway = await _service(database)
    request = await service.request_archive(
        channel_id=7000,
        reason="Projekt je dokončený.",
        principal=_principal(AppRole.TEAM_MOD),
        correlation_id="archive-ambiguous-request",
        now=NOW,
    )
    gateway.ambiguous_after_archive = True

    with pytest.raises(ChannelOperationError, match="Discord archive operation failed"):
        await service.decide_archive(
            request.id,
            approve=True,
            principal=_principal(AppRole.ADMIN, USER_ID + 10),
            correlation_id="archive-ambiguous",
            now=NOW + timedelta(minutes=1),
        )

    async with database.session() as session:
        interrupted = await session.get(ChannelArchiveRequestModel, request.id)
    assert interrupted is not None and interrupted.state == ArchiveState.ARCHIVING.value

    gateway.ambiguous_after_archive = False
    recovered = await service.recover_archives(GUILD_ID, correlation_id="startup-recovery")

    assert [item.state for item in recovered] == [ArchiveState.EXECUTED]
    assert gateway.archived == [(7000, "projekt-alfa-2026-08-09")]
    async with database.session() as session:
        stored = await session.get(ChannelArchiveRequestModel, request.id)
    assert stored is not None and stored.state == ArchiveState.EXECUTED.value


def test_channel_names_are_deterministic_and_bounded() -> None:
    assert normalize_channel_name("  Červený tím 2026 ") == "cerveny-tim-2026"
    assert len(archive_channel_name("x" * 150, NOW)) == 100
    with pytest.raises(ValueError, match="empty"):
        normalize_channel_name("♥♥♥")
