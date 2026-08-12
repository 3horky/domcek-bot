from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime, time
from typing import Any, cast

import pytest
from sqlalchemy import select, text

from domcek_bot.application.alerts import AlertCategory, ConfiguredModeratorAlerts
from domcek_bot.application.auth.authorization import AppRole, Principal
from domcek_bot.application.discord_admin import (
    DiscordAdministrationService,
    DiscordDirectory,
    DiscordMemberOption,
    LastAdminRemovalDenied,
)
from domcek_bot.application.records import GuildConfigRecord, ReactionConfigRecord
from domcek_bot.application.settings import SettingsService, SettingsValidationError
from domcek_bot.application.undo import UndoService
from domcek_bot.config import AppEnvironment, Settings
from domcek_bot.domain.errors import OptimisticLockError
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.models import AuditLogModel, Base
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.skipif(
    "TEST_DATABASE_URL" not in os.environ,
    reason="integration database not configured",
)

GUILD_ID = 1535774834955391047


@pytest.fixture
async def database() -> AsyncIterator[Database]:
    database = Database(
        Settings(app_env=AppEnvironment.TEST, database_url=os.environ["TEST_DATABASE_URL"])
    )
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    async with database.transaction() as connection:
        await connection.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))
    try:
        yield database
    finally:
        async with database.transaction() as connection:
            await connection.execute(text(f"TRUNCATE TABLE {table_names} CASCADE"))
        await database.close()


def _principal(role: AppRole = AppRole.ADMIN) -> Principal:
    return Principal(
        guild_id=GUILD_ID,
        user_id=42,
        username="admin",
        display_name="Admin",
        avatar_url=None,
        discord_role_ids=frozenset(),
        app_roles=frozenset({role}),
    )


class FakeDiscordAdministration:
    assignable = True
    admin_count = 1
    changes: list[tuple[int, int, bool]]

    def __init__(self) -> None:
        self.changes = []
        self.reaction_tests: list[tuple[int, int, str]] = []
        self.member_roles: dict[int, set[int]] = {101: {900}, 102: {900}}
        self.fail_after_role_change = False

    async def directory(self, guild_id: int) -> DiscordDirectory:
        del guild_id
        return DiscordDirectory((), (), (), ())

    async def search_members(
        self, guild_id: int, query: str, *, limit: int = 25
    ) -> tuple[DiscordMemberOption, ...]:
        del guild_id, query, limit
        return ()

    async def role_is_assignable(self, guild_id: int, role_id: int) -> bool:
        del guild_id, role_id
        return self.assignable

    async def get_member(self, guild_id: int, member_id: int) -> DiscordMemberOption:
        del guild_id
        return DiscordMemberOption(
            member_id,
            "member",
            "Member",
            None,
            tuple(sorted(self.member_roles.get(member_id, set()))),
        )

    async def count_role_members(self, guild_id: int, role_id: int) -> int:
        del guild_id, role_id
        await asyncio.sleep(0.01)
        return self.admin_count

    async def set_member_role(
        self, guild_id: int, member_id: int, role_id: int, *, enabled: bool, reason: str
    ) -> DiscordMemberOption:
        del guild_id, reason
        await asyncio.sleep(0.01)
        self.changes.append((member_id, role_id, enabled))
        roles = self.member_roles.setdefault(member_id, set())
        if enabled:
            roles.add(role_id)
        else:
            roles.discard(role_id)
        if not enabled:
            self.admin_count -= 1
        if self.fail_after_role_change:
            raise RuntimeError("connection lost after Discord accepted the role change")
        return DiscordMemberOption(member_id, "member", "Member", None, tuple(sorted(roles)))

    async def test_reaction(self, guild_id: int, channel_id: int, emoji: str) -> int:
        self.reaction_tests.append((guild_id, channel_id, emoji))
        return 123


class FakeSettingsTargetValidator:
    def __init__(self) -> None:
        self.calls: list[tuple[int, tuple[int, ...], tuple[int, ...]]] = []
        self.available = True

    async def validate_settings_targets(
        self,
        guild_id: int,
        *,
        channel_ids: tuple[int, ...],
        category_ids: tuple[int, ...],
    ) -> None:
        self.calls.append((guild_id, channel_ids, category_ids))
        if not self.available:
            raise RuntimeError("Discord object unavailable")


class FakeReactionTargetValidator:
    def __init__(self) -> None:
        self.calls: list[tuple[int, tuple[int, ...], tuple[int, ...]]] = []

    async def validate_reaction_targets(
        self,
        guild_id: int,
        *,
        emoji_ids: tuple[int, ...],
        channel_ids: tuple[int, ...],
    ) -> None:
        self.calls.append((guild_id, emoji_ids, channel_ids))


class RecordingAlertTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str, str]] = []

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
        del summary, correlation_id, run_id
        assert moderator_channel_id is not None
        self.calls.append((guild_id, title, str(moderator_channel_id)))


async def test_settings_are_versioned_validated_and_audited(database: Database) -> None:
    uow = SqlAlchemyUnitOfWork(database)
    async with uow.transaction() as repositories:
        await repositories.guild_configs.add(GuildConfigRecord(guild_id=GUILD_ID))
    validator = FakeSettingsTargetValidator()
    service = SettingsService(uow, discord_settings_validator=validator)

    updated = await service.update_publication(
        expected_version=1,
        timezone="Europe/Prague",
        publication_weekday=2,
        publication_time=time(18, 30),
        automatic_publication_enabled=False,
        publish_google_descriptions=True,
        generated_intro_enabled=False,
        everyone_mention_enabled=True,
        announcement_channel_id=111,
        command_channel_id=222,
        moderator_channel_id=333,
        projects_category_id=444,
        archive_category_id=555,
        closing_message="  Dovidenia  ",
        principal=_principal(),
        correlation_id="settings-1",
    )
    assert updated.version == 2
    assert updated.closing_message == "Dovidenia"
    assert updated.publication_time == time(18, 30)
    assert validator.calls == [(GUILD_ID, (111, 222, 333), (444, 555))]

    with pytest.raises(SettingsValidationError, match="must mention @everyone"):
        await service.update_publication(
            expected_version=2,
            timezone="Europe/Bratislava",
            publication_weekday=0,
            publication_time=time(20),
            automatic_publication_enabled=True,
            publish_google_descriptions=False,
            generated_intro_enabled=True,
            everyone_mention_enabled=False,
            announcement_channel_id=None,
            command_channel_id=None,
            moderator_channel_id=None,
            projects_category_id=None,
            archive_category_id=None,
            closing_message=None,
            principal=_principal(),
            correlation_id="settings-everyone-required",
        )

    with pytest.raises(OptimisticLockError):
        await service.update_publication(
            expected_version=1,
            timezone="Europe/Bratislava",
            publication_weekday=0,
            publication_time=time(20),
            automatic_publication_enabled=True,
            publish_google_descriptions=False,
            generated_intro_enabled=True,
            everyone_mention_enabled=True,
            announcement_channel_id=None,
            command_channel_id=None,
            moderator_channel_id=None,
            projects_category_id=None,
            archive_category_id=None,
            closing_message=None,
            principal=_principal(),
            correlation_id="settings-stale",
        )

    with pytest.raises(SettingsValidationError):
        await service.update_publication(
            expected_version=2,
            timezone="Not/A-Timezone",
            publication_weekday=0,
            publication_time=time(20),
            automatic_publication_enabled=True,
            publish_google_descriptions=False,
            generated_intro_enabled=True,
            everyone_mention_enabled=True,
            announcement_channel_id=None,
            command_channel_id=None,
            moderator_channel_id=None,
            projects_category_id=None,
            archive_category_id=None,
            closing_message=None,
            principal=_principal(),
            correlation_id="settings-invalid",
        )

    validator.available = False
    with pytest.raises(SettingsValidationError, match="channel or category is unavailable"):
        await service.update_publication(
            expected_version=2,
            timezone="Europe/Bratislava",
            publication_weekday=0,
            publication_time=time(20),
            automatic_publication_enabled=True,
            publish_google_descriptions=False,
            generated_intro_enabled=True,
            everyone_mention_enabled=True,
            announcement_channel_id=999,
            command_channel_id=None,
            moderator_channel_id=None,
            projects_category_id=None,
            archive_category_id=None,
            closing_message=None,
            principal=_principal(),
            correlation_id="settings-missing-discord-target",
        )


async def test_alert_category_toggle_is_enforced_at_delivery(database: Database) -> None:
    uow = SqlAlchemyUnitOfWork(database)
    async with uow.transaction() as repositories:
        await repositories.guild_configs.add(
            GuildConfigRecord(
                guild_id=GUILD_ID,
                moderator_channel_id=333,
                alert_calendar_sync_enabled=False,
            )
        )
    transport = RecordingAlertTransport()
    alerts = ConfiguredModeratorAlerts(uow, transport, AlertCategory.CALENDAR)
    await alerts.send_alert(
        guild_id=GUILD_ID,
        moderator_channel_id=999,
        title="Sync zlyhal",
        summary="safe",
        correlation_id="disabled",
        run_id=None,
    )
    assert transport.calls == []

    async with uow.transaction() as repositories:
        current = await repositories.guild_configs.get(GUILD_ID)
        assert current is not None
        await repositories.guild_configs.update(
            replace(current, alert_calendar_sync_enabled=True),
            expected_version=current.version,
        )
    await alerts.send_alert(
        guild_id=GUILD_ID,
        moderator_channel_id=999,
        title="Sync zlyhal",
        summary="safe",
        correlation_id="enabled",
        run_id=None,
    )
    assert transport.calls == [(GUILD_ID, "📅 Kalendár · Sync zlyhal", "333")]


async def test_calendar_identity_reset_and_reaction_round_trip(database: Database) -> None:
    uow = SqlAlchemyUnitOfWork(database)
    async with uow.transaction() as repositories:
        await repositories.guild_configs.add(
            GuildConfigRecord(guild_id=GUILD_ID, announcement_channel_id=111)
        )
    validator = FakeReactionTargetValidator()
    service = SettingsService(uow, reaction_validator=validator)
    source = await service.add_calendar(
        external_calendar_id="old@example.test",
        display_name="Program",
        priority=20,
        active=True,
        principal=_principal(),
        correlation_id="calendar-create",
    )
    async with uow.transaction() as repositories:
        await repositories.calendar_sources.mark_sync_succeeded(
            source.id,
            sync_token="secret-token",
            sync_token_query_key="query-v1",
            completed_at=datetime.now(UTC),
            was_full_sync=True,
        )
        synced = await repositories.calendar_sources.get(source.id)
    assert synced is not None
    changed = await service.update_calendar(
        source.id,
        expected_version=synced.version,
        external_calendar_id="new@example.test",
        display_name="Program 2",
        priority=10,
        active=True,
        principal=_principal(),
        correlation_id="calendar-change",
    )
    assert changed.sync_token is None
    assert changed.sync_token_query_key is None
    assert changed.sync_status.value == "never"

    reactions = await service.update_reactions(
        ReactionConfigRecord(
            guild_id=GUILD_ID,
            seen_enabled=True,
            seen_emoji_unicode="👀",
            auto_reaction_enabled=True,
            auto_reaction_emoji_id=987,
            auto_reaction_channel_ids=(333, 222, 333),
            mention_reaction_enabled=False,
        ),
        expected_version=1,
        principal=_principal(),
        correlation_id="reactions-create",
    )
    assert reactions.auto_reaction_channel_ids == (222, 333)
    assert validator.calls == [(GUILD_ID, (987,), (111, 222, 333))]
    snapshot = await service.get(_principal())
    assert snapshot.reactions == reactions

    with pytest.raises(SettingsValidationError):
        await service.update_reactions(
            replace(reactions, seen_emoji_id=12),
            expected_version=reactions.version,
            principal=_principal(),
            correlation_id="reactions-invalid",
        )

    with pytest.raises(SettingsValidationError, match="is not an emoji"):
        await service.update_reactions(
            replace(
                reactions,
                seen_emoji_unicode="not emoji",
                seen_emoji_id=None,
            ),
            expected_version=reactions.version,
            principal=_principal(),
            correlation_id="reactions-not-emoji",
        )


async def test_team_mod_cannot_open_settings(database: Database) -> None:
    uow = SqlAlchemyUnitOfWork(database)
    async with uow.transaction() as repositories:
        await repositories.guild_configs.add(GuildConfigRecord(guild_id=GUILD_ID))
    with pytest.raises(PermissionError):
        await SettingsService(uow).get(_principal(AppRole.TEAM_MOD))


async def test_role_management_protects_last_admin_and_uses_configured_roles(
    database: Database,
) -> None:
    uow = SqlAlchemyUnitOfWork(database)
    async with uow.transaction() as repositories:
        await repositories.guild_configs.add(
            GuildConfigRecord(guild_id=GUILD_ID, admin_role_id=900, team_mod_role_id=901)
        )
    gateway = FakeDiscordAdministration()
    service = DiscordAdministrationService(uow, gateway)
    with pytest.raises(LastAdminRemovalDenied):
        await service.set_application_role(
            member_id=101,
            role="admin",
            enabled=False,
            principal=_principal(),
            correlation_id="last-admin",
        )
    assert gateway.changes == []

    gateway.admin_count = 2
    member = await service.set_application_role(
        member_id=101,
        role="admin",
        enabled=False,
        principal=_principal(),
        correlation_id="remove-admin",
    )
    assert member.id == 101
    assert member.undo_id is not None
    assert gateway.changes == [(101, 900, False)]

    undone = await UndoService(uow, gateway, cast(Any, gateway)).undo(
        uuid.UUID(member.undo_id),
        principal=_principal(),
        correlation_id="undo-remove-admin",
    )
    assert undone.state.value == "undone"
    assert gateway.changes[-1] == (101, 900, True)

    replay = await UndoService(uow, gateway, cast(Any, gateway)).undo(
        uuid.UUID(member.undo_id),
        principal=_principal(),
        correlation_id="undo-remove-admin-replay",
    )
    assert replay.state.value == "undone"
    assert gateway.changes.count((101, 900, True)) == 1

    with pytest.raises(PermissionError):
        await service.set_application_role(
            member_id=102,
            role="team_mod",
            enabled=True,
            principal=_principal(AppRole.TEAM_MOD),
            correlation_id="team-mod-role-denied",
        )
    async with database.transaction() as connection:
        denied_reasons = (
            await connection.scalars(
                select(AuditLogModel.after_value).where(
                    AuditLogModel.action == "role.change_denied"
                )
            )
        ).all()
    assert {value["reason"] for value in denied_reasons} == {
        "last_admin_protection",
        "AuthorizationDenied",
    }


async def test_reaction_test_uses_explicit_visible_draft_emoji(database: Database) -> None:
    uow = SqlAlchemyUnitOfWork(database)
    async with uow.transaction() as repositories:
        await repositories.guild_configs.add(GuildConfigRecord(guild_id=GUILD_ID))
    gateway = FakeDiscordAdministration()
    service = DiscordAdministrationService(uow, gateway)

    message_id = await service.test_configured_reaction(
        kind="seen",
        channel_id=111,
        emoji_id=None,
        emoji_unicode="🎉",
        principal=_principal(),
        correlation_id="visible-draft-reaction",
    )

    assert message_id == 123
    assert gateway.reaction_tests == [(GUILD_ID, 111, "🎉")]
    async with database.transaction() as connection:
        audit = await connection.scalar(
            select(AuditLogModel.after_value).where(AuditLogModel.action == "reaction.tested")
        )
    assert audit is not None
    assert audit["emoji_unicode"] == "🎉"

    with pytest.raises(ValueError, match="two emoji"):
        await service.test_configured_reaction(
            kind="seen",
            channel_id=111,
            emoji_id=987,
            emoji_unicode="🎉",
            principal=_principal(),
            correlation_id="invalid-double-emoji",
        )


async def test_role_undo_survives_ambiguous_crash_after_discord_effect(
    database: Database,
) -> None:
    uow = SqlAlchemyUnitOfWork(database)
    async with uow.transaction() as repositories:
        await repositories.guild_configs.add(
            GuildConfigRecord(guild_id=GUILD_ID, team_mod_role_id=901)
        )
    gateway = FakeDiscordAdministration()
    gateway.fail_after_role_change = True
    service = DiscordAdministrationService(uow, gateway)

    with pytest.raises(RuntimeError, match="connection lost"):
        await service.set_application_role(
            member_id=101,
            role="team_mod",
            enabled=True,
            principal=_principal(),
            correlation_id="ambiguous-role-change",
        )

    assert 901 in gateway.member_roles[101]
    operations = await UndoService(uow, gateway, cast(Any, gateway)).list_available(
        principal=_principal(), scope="roles"
    )
    assert len(operations) == 1

    gateway.fail_after_role_change = False
    result = await UndoService(uow, gateway, cast(Any, gateway)).undo(
        operations[0].id,
        principal=_principal(),
        correlation_id="undo-ambiguous-role-change",
    )
    assert result.state.value == "undone"
    assert 901 not in gateway.member_roles[101]


async def test_concurrent_admin_removals_cannot_remove_both_admins(database: Database) -> None:
    uow = SqlAlchemyUnitOfWork(database)
    async with uow.transaction() as repositories:
        await repositories.guild_configs.add(
            GuildConfigRecord(guild_id=GUILD_ID, admin_role_id=900)
        )
    gateway = FakeDiscordAdministration()
    gateway.admin_count = 2
    service = DiscordAdministrationService(uow, gateway)

    results = await asyncio.gather(
        service.set_application_role(
            member_id=101,
            role="admin",
            enabled=False,
            principal=_principal(),
            correlation_id="remove-admin-one",
        ),
        service.set_application_role(
            member_id=102,
            role="admin",
            enabled=False,
            principal=_principal(),
            correlation_id="remove-admin-two",
        ),
        return_exceptions=True,
    )

    assert sum(isinstance(result, DiscordMemberOption) for result in results) == 1
    assert sum(isinstance(result, LastAdminRemovalDenied) for result in results) == 1
    assert len(gateway.changes) == 1
    assert gateway.admin_count == 1
