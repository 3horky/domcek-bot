"""Generate a read-only E14 report for the latest publication cycles."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime, timedelta

from domcek_bot.application.auth.authorization import AppRole, Principal
from domcek_bot.application.operations import RuntimeOperationsService
from domcek_bot.application.publication.history import PublicationHistoryService
from domcek_bot.application.publication.stabilization import build_stabilization_report
from domcek_bot.config import ProcessKind, load_settings
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


async def generate(
    *,
    guild_id: int,
    cycles: int,
    cutover_at: datetime,
    backup_restore_verified: bool = False,
    discord_output_verified: bool = False,
) -> dict[str, object]:
    settings = load_settings(ProcessKind.MIGRATION)
    database = Database(settings)
    unit_of_work = SqlAlchemyUnitOfWork(database)
    history = PublicationHistoryService(unit_of_work)
    principal = Principal(
        guild_id=guild_id,
        user_id=0,
        username="stabilization-report",
        display_name="Stabilization report",
        avatar_url=None,
        discord_role_ids=frozenset(),
        app_roles=frozenset({AppRole.ADMIN}),
    )
    try:
        entries = await history.list(principal, limit=100)
        operations = await RuntimeOperationsService(unit_of_work).summary(principal)
        async with unit_of_work.transaction() as repositories:
            open_incident_count = await repositories.publication_runs.count_open_incidents(guild_id)
            guild = await repositories.guild_configs.get(guild_id)
            calendars = await repositories.calendar_sources.list_for_guild(guild_id)
    finally:
        await database.close()
    if guild is None:
        raise LookupError("guild configuration not found")
    return build_stabilization_report(
        guild_id=guild_id,
        entries=entries,
        operations=operations,
        calendars=calendars,
        automatic_publication_enabled=guild.automatic_publication_enabled,
        open_incident_count=open_incident_count,
        cycles=cycles,
        cutover_at=cutover_at,
        observed_at=datetime.now(UTC),
        timezone_name=guild.timezone,
        calendar_max_safe_age=timedelta(minutes=settings.calendar_max_safe_age_minutes),
        backup_restore_verified=backup_restore_verified,
        discord_output_verified=discord_output_verified,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guild-id", type=int, required=True)
    parser.add_argument("--cycles", type=int, default=3, choices=range(3, 11))
    parser.add_argument(
        "--cutover-at",
        type=datetime.fromisoformat,
        required=True,
        help="Explicitný produkčný cutover timestamp s časovým pásmom.",
    )
    parser.add_argument(
        "--backup-restore-verified",
        action="store_true",
        help="Potvrď iba po úspešnej produkčnej restore rehearsal.",
    )
    parser.add_argument(
        "--discord-output-verified",
        action="store_true",
        help="Potvrď iba po manuálnom porovnaní všetkých reportovaných Discord správ.",
    )
    args = parser.parse_args()
    result = asyncio.run(
        generate(
            guild_id=args.guild_id,
            cycles=args.cycles,
            cutover_at=args.cutover_at,
            backup_restore_verified=args.backup_restore_verified,
            discord_output_verified=args.discord_output_verified,
        )
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
