"""Idempotently attach the two E0 read-only calendars to the local shadow guild."""

from __future__ import annotations

import argparse
import asyncio
import os

from domcek_bot.application.auth.authorization import AppRole, Principal
from domcek_bot.application.settings import SettingsService
from domcek_bot.config import ProcessKind, load_settings
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


async def configure(*, guild_id: int, actor_user_id: int) -> None:
    settings = load_settings(ProcessKind.MIGRATION)
    calendars = (
        (
            os.environ.get("E3_TEST_PRIMARY_CALENDAR_ID", "").strip(),
            "Carlo test - hlavný kalendár",
            10,
        ),
        (
            os.environ.get("E3_TEST_SECONDARY_CALENDAR_ID", "").strip(),
            "Carlo test - doplnkový kalendár",
            20,
        ),
    )
    if any(not calendar_id for calendar_id, _, _ in calendars):
        raise SystemExit("Chýbajú E3_TEST_PRIMARY_CALENDAR_ID/E3_TEST_SECONDARY_CALENDAR_ID.")

    database = Database(settings)
    unit_of_work = SqlAlchemyUnitOfWork(database)
    principal = Principal(
        guild_id=guild_id,
        user_id=actor_user_id,
        username="staging-bootstrap",
        display_name="Staging bootstrap",
        avatar_url=None,
        discord_role_ids=frozenset(),
        app_roles=frozenset({AppRole.ADMIN}),
    )
    try:
        async with unit_of_work.transaction() as repositories:
            guild = await repositories.guild_configs.get(guild_id)
            existing = await repositories.calendar_sources.list_for_guild(guild_id)
        if guild is None:
            raise SystemExit(f"Guild {guild_id} ešte nemá Carlo konfiguráciu.")
        existing_ids = {source.external_calendar_id for source in existing}
        service = SettingsService(unit_of_work)
        for calendar_id, name, priority in calendars:
            if calendar_id in existing_ids:
                print(f"Ponechaný existujúci zdroj: {name}")
                continue
            created = await service.add_calendar(
                external_calendar_id=calendar_id,
                display_name=name,
                priority=priority,
                active=True,
                principal=principal,
                correlation_id="e12-shadow-calendar-bootstrap",
            )
            print(f"Pridaný zdroj {created.id}: {name}")
    finally:
        await database.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guild-id", type=int, required=True)
    parser.add_argument("--actor-user-id", type=int, required=True)
    parser.add_argument("--confirm-shadow", action="store_true", required=True)
    args = parser.parse_args()
    asyncio.run(configure(guild_id=args.guild_id, actor_user_id=args.actor_user_id))


if __name__ == "__main__":
    main()
