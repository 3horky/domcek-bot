from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select, text

from domcek_bot.application.audit import AuditQueryService
from domcek_bot.application.auth.authorization import AppRole, AuthorizationDenied, Principal
from domcek_bot.application.editor.content import (
    ContentConflict,
    ContentEditorialService,
    ContentObjectNotFound,
    ContentValidationError,
    CreateInfoAnnouncement,
    CreateManualEvent,
    InfoAnnouncementValues,
    ManualEventValues,
    UpdateInfoAnnouncement,
    UpdateManualEvent,
)
from domcek_bot.application.records import AuditLogRecord, GuildConfigRecord
from domcek_bot.config import Settings
from domcek_bot.domain.enums import AuditResult
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.models import AuditLogModel, Base
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.skipif(
    "TEST_DATABASE_URL" not in os.environ,
    reason="integration database not configured",
)

GUILD_ID = 1535774834955391047
OTHER_GUILD_ID = GUILD_ID + 1
USER_ID = 1535771583841439765
NOW = datetime(2026, 8, 9, 10, tzinfo=UTC)


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


def _principal(role: AppRole, *, guild_id: int = GUILD_ID) -> Principal:
    return Principal(
        guild_id=guild_id,
        user_id=USER_ID,
        username="content-editor",
        display_name="Content Editor",
        avatar_url=None,
        discord_role_ids=frozenset(),
        app_roles=frozenset({role}),
    )


async def _service(database: Database) -> tuple[SqlAlchemyUnitOfWork, ContentEditorialService]:
    unit_of_work = SqlAlchemyUnitOfWork(database)
    async with unit_of_work.transaction() as repositories:
        await repositories.guild_configs.add(GuildConfigRecord(guild_id=GUILD_ID))
    return unit_of_work, ContentEditorialService(unit_of_work)


async def test_manual_event_lifecycle_is_versioned_soft_deleted_and_audited(
    database: Database,
) -> None:
    unit_of_work, service = await _service(database)
    created = await service.create_manual(
        CreateManualEvent(
            ManualEventValues(
                title="  Ručná udalosť  ",
                description="  Redakčný popis  ",
                is_all_day=True,
                starts_on=date(2026, 8, 12),
                link_url=" https://example.test/event ",
            )
        ),
        principal=_principal(AppRole.TEAM_MOD),
        correlation_id="manual-create",
        now=NOW,
    )
    assert created.title == "Ručná udalosť"
    assert created.ends_on == date(2026, 8, 13)
    assert created.version == 1
    assert created.guild_id == GUILD_ID

    updated = await service.update_manual(
        UpdateManualEvent(
            created.id,
            1,
            ManualEventValues(
                title="Časovaná udalosť",
                description=None,
                is_all_day=False,
                starts_at=NOW + timedelta(days=2),
                ends_at=NOW + timedelta(days=2, hours=2),
                active=False,
            ),
        ),
        principal=_principal(AppRole.ADMIN),
        correlation_id="manual-update",
        now=NOW + timedelta(minutes=1),
    )
    assert updated.version == 2
    assert updated.starts_on is None
    assert not updated.active

    with pytest.raises(ContentConflict) as conflict:
        await service.update_manual(
            UpdateManualEvent(
                created.id,
                1,
                ManualEventValues(
                    title="Stará zmena",
                    is_all_day=False,
                    starts_at=NOW + timedelta(days=3),
                ),
            ),
            principal=_principal(AppRole.ADMIN),
            correlation_id="manual-stale",
            now=NOW + timedelta(minutes=2),
        )
    assert conflict.value.current is not None
    assert conflict.value.current.version == 2

    deleted = await service.delete_manual(
        created.id,
        2,
        principal=_principal(AppRole.TEAM_MOD),
        correlation_id="manual-delete",
        now=NOW + timedelta(minutes=3),
    )
    assert deleted.version == 3
    assert deleted.deleted_at == NOW + timedelta(minutes=3)
    assert not deleted.active

    assert [
        record.id for record in await service.list_manual(principal=_principal(AppRole.ADMIN))
    ] == [created.id]
    async with unit_of_work.transaction() as repositories:
        audit = await repositories.audit_logs.list_for_object("manual_event", str(created.id))
    assert [entry.action for entry in audit] == [
        "manual_event.created",
        "manual_event.updated",
        "manual_event.deleted",
    ]
    assert all(entry.result is AuditResult.SUCCEEDED for entry in audit)
    assert audit[-1].after_value is not None
    assert audit[-1].after_value["version"] == 3


async def test_info_lifecycle_supports_inclusive_last_day_and_safe_image_url(
    database: Database,
) -> None:
    unit_of_work, service = await _service(database)
    created = await service.create_info(
        CreateInfoAnnouncement(
            InfoAnnouncementValues(
                title="INFO",
                description="Dôležitý oznam",
                valid_from=date(2026, 8, 9),
                valid_until=date(2026, 8, 9),
                image_url="https://cdn.example.test/image.png",
            )
        ),
        principal=_principal(AppRole.ADMIN),
        correlation_id="info-create",
        now=NOW,
    )
    assert created.valid_from == created.valid_until
    assert created.version == 1

    updated = await service.update_info(
        UpdateInfoAnnouncement(
            created.id,
            1,
            InfoAnnouncementValues(
                title="INFO 2",
                description="Upravený oznam",
                valid_from=date(2026, 8, 9),
                valid_until=date(2026, 8, 16),
                active=False,
            ),
        ),
        principal=_principal(AppRole.TEAM_MOD),
        correlation_id="info-update",
        now=NOW + timedelta(minutes=1),
    )
    assert updated.version == 2
    assert updated.valid_until == date(2026, 8, 16)

    deleted = await service.delete_info(
        created.id,
        2,
        principal=_principal(AppRole.ADMIN),
        correlation_id="info-delete",
        now=NOW + timedelta(minutes=2),
    )
    assert deleted.version == 3
    assert deleted.deleted_at is not None

    async with unit_of_work.transaction() as repositories:
        audit = await repositories.audit_logs.list_for_object("info_announcement", str(created.id))
    assert [entry.correlation_id for entry in audit] == [
        "info-create",
        "info-update",
        "info-delete",
    ]


async def test_publisher_is_denied_and_cross_guild_records_are_hidden(
    database: Database,
) -> None:
    _, service = await _service(database)
    with pytest.raises(AuthorizationDenied):
        await service.create_info(
            CreateInfoAnnouncement(
                InfoAnnouncementValues(
                    title="Zakázané INFO",
                    description="Bez redakčného oprávnenia",
                    valid_from=date(2026, 8, 9),
                    valid_until=date(2026, 8, 10),
                )
            ),
            principal=_principal(AppRole.PUBLISHER),
            correlation_id="publisher-denied",
            now=NOW,
        )

    async with database.session() as session:
        denied = (
            await session.scalars(
                select(AuditLogModel).where(AuditLogModel.correlation_id == "publisher-denied")
            )
        ).one()
    assert denied.result == AuditResult.FAILED.value
    assert denied.after_value is None

    created = await service.create_manual(
        CreateManualEvent(
            ManualEventValues(
                title="Domáca udalosť",
                is_all_day=True,
                starts_on=date(2026, 8, 10),
            )
        ),
        principal=_principal(AppRole.ADMIN),
        correlation_id="cross-guild-seed",
        now=NOW,
    )
    with pytest.raises(ContentObjectNotFound):
        await service.update_manual(
            UpdateManualEvent(
                created.id,
                1,
                ManualEventValues(
                    title="Cudzia zmena",
                    is_all_day=True,
                    starts_on=date(2026, 8, 11),
                ),
            ),
            principal=_principal(AppRole.ADMIN, guild_id=OTHER_GUILD_ID),
            correlation_id="cross-guild-attempt",
            now=NOW,
        )


def test_content_values_reject_unsafe_shapes_and_urls() -> None:
    with pytest.raises(ContentValidationError, match="timezone"):
        ManualEventValues(
            title="Udalosť",
            is_all_day=False,
            starts_at=datetime(2026, 8, 10, 10),
        )
    with pytest.raises(ContentValidationError, match="public HTTP"):
        InfoAnnouncementValues(
            title="INFO",
            description="Oznam",
            valid_from=date(2026, 8, 9),
            valid_until=date(2026, 8, 10),
            image_url="file:///etc/passwd",
        )
    for private_url in (
        "http://localhost/private.png",
        "http://127.0.0.1/private.png",
        "http://10.20.30.40/private.png",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/private.png",
    ):
        with pytest.raises(ContentValidationError, match="public HTTP"):
            InfoAnnouncementValues(
                title="INFO",
                description="Oznam",
                valid_from=date(2026, 8, 9),
                valid_until=date(2026, 8, 10),
                image_url=private_url,
            )
    with pytest.raises(ContentValidationError, match="cannot precede"):
        InfoAnnouncementValues(
            title="INFO",
            description="Oznam",
            valid_from=date(2026, 8, 10),
            valid_until=date(2026, 8, 9),
        )


async def test_audit_query_is_guild_isolated_and_role_filtered(database: Database) -> None:
    unit_of_work, content = await _service(database)
    created = await content.create_manual(
        CreateManualEvent(
            ManualEventValues(
                title="Auditovaná udalosť",
                is_all_day=True,
                starts_on=date(2026, 8, 12),
            )
        ),
        principal=_principal(AppRole.TEAM_MOD),
        correlation_id="editorial-audit",
        now=NOW,
    )
    async with unit_of_work.transaction() as repositories:
        await repositories.guild_configs.add(GuildConfigRecord(guild_id=OTHER_GUILD_ID))
        await repositories.audit_logs.add(
            AuditLogRecord(
                id=uuid.uuid4(),
                guild_id=GUILD_ID,
                actor_user_id=USER_ID,
                action="role.admin.granted",
                object_type="discord_role",
                object_id="role-1",
                result=AuditResult.SUCCEEDED,
                correlation_id="admin-only-audit",
                created_at=NOW + timedelta(minutes=1),
            )
        )
        await repositories.audit_logs.add(
            AuditLogRecord(
                id=uuid.uuid4(),
                guild_id=OTHER_GUILD_ID,
                actor_user_id=USER_ID,
                action="manual_event.updated",
                object_type="manual_event",
                object_id="foreign-record",
                result=AuditResult.SUCCEEDED,
                correlation_id="foreign-audit",
                created_at=NOW + timedelta(minutes=2),
            )
        )

    audit = AuditQueryService(unit_of_work)
    admin_records = await audit.list_recent(principal=_principal(AppRole.ADMIN), limit=100)
    assert [record.correlation_id for record in admin_records] == [
        "admin-only-audit",
        "editorial-audit",
    ]

    team_records = await audit.list_recent(principal=_principal(AppRole.TEAM_MOD), limit=100)
    assert [record.object_id for record in team_records] == [str(created.id)]

    with pytest.raises(AuthorizationDenied):
        await audit.list_recent(principal=_principal(AppRole.PUBLISHER), limit=100)
