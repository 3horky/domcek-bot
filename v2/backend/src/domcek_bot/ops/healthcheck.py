"""Container healthcheck for the Discord bot and publication worker."""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import timedelta

from domcek_bot.application.operations import RuntimeOperationsService
from domcek_bot.config import ProcessKind, load_settings
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

EXPECTED_STATES = {
    ProcessKind.BOT: "connected",
    ProcessKind.WORKER: "running",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify one fresh Carlo runtime instance in PostgreSQL."
    )
    parser.add_argument(
        "--process",
        required=True,
        choices=(ProcessKind.BOT.value, ProcessKind.WORKER.value),
    )
    parser.add_argument("--stale-seconds", type=int, default=90)
    return parser


async def _check(process: ProcessKind, stale_seconds: int) -> int:
    if stale_seconds <= 0:
        print("unhealthy reason=invalid_freshness", file=sys.stderr)
        return 2

    database: Database | None = None
    try:
        settings = load_settings(process)
        if settings.discord_guild_id is None:  # guarded by validate_for; keeps type narrowing local
            print("unhealthy reason=missing_guild", file=sys.stderr)
            return 2
        database = Database(settings)
        health = await RuntimeOperationsService(SqlAlchemyUnitOfWork(database)).process_health(
            guild_id=settings.discord_guild_id,
            process_name=process.value,
            expected_state=EXPECTED_STATES[process],
            expected_execution_mode=(
                settings.publication_execution_mode.value if process is ProcessKind.WORKER else None
            ),
            stale_after=timedelta(seconds=stale_seconds),
        )
    except Exception as exc:  # healthcheck must fail closed without leaking configuration
        print(f"unhealthy reason=check_failed type={type(exc).__name__}", file=sys.stderr)
        return 1
    finally:
        if database is not None:
            await database.close()

    stream = sys.stdout if health.healthy else sys.stderr
    print(
        f"{'healthy' if health.healthy else 'unhealthy'} "
        f"process={process.value} reason={health.reason} "
        f"active_instances={health.active_instances}",
        file=stream,
    )
    return 0 if health.healthy else 1


def run() -> None:
    args = _parser().parse_args()
    process = ProcessKind(args.process)
    raise SystemExit(asyncio.run(_check(process, args.stale_seconds)))


if __name__ == "__main__":
    run()
