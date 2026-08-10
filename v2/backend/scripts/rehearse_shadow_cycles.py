"""Compose read-only shadow drafts for explicit historical/future reference instants."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from datetime import datetime

from domcek_bot.application.publication.intro import FALLBACK_TEXT
from domcek_bot.application.publication.service import PublicationDraftService
from domcek_bot.config import ProcessKind, load_settings
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("reference time must contain a UTC offset")
    return parsed


async def rehearse(*, guild_id: int, reference_times: list[datetime]) -> None:
    database = Database(load_settings(ProcessKind.MIGRATION))
    drafts = PublicationDraftService(SqlAlchemyUnitOfWork(database))
    result: list[dict[str, object]] = []
    try:
        for reference_time in reference_times:
            draft = await drafts.compose_next(
                guild_id,
                reference_time=reference_time,
                intro_text=FALLBACK_TEXT,
            )
            canonical = draft.canonical_json()
            result.append(
                {
                    "reference_time": reference_time.isoformat(),
                    "slot_key": draft.slot_key,
                    "scheduled_for": draft.scheduled_for.isoformat(),
                    "window_starts_at": draft.window_starts_at.isoformat(),
                    "window_ends_at": draft.window_ends_at.isoformat(),
                    "draft_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
                    "public_items": [
                        {
                            "kind": item.kind.value,
                            "source_id": item.source_id,
                            "title": item.title,
                            "description": item.description,
                            "display_time": item.display_time,
                        }
                        for item in draft.public_items
                    ],
                    "excluded_events": [
                        {
                            "source_id": item.source_id,
                            "title": item.title,
                            "reason": item.exclusion_reason.value
                            if item.exclusion_reason is not None
                            else None,
                        }
                        for item in draft.editor_events
                        if not item.included
                    ],
                    "message_count": len(draft.messages),
                    "warning_codes": [warning.code.value for warning in draft.warnings],
                }
            )
    finally:
        await database.close()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guild-id", type=int, required=True)
    parser.add_argument("--reference-time", type=_aware, action="append", required=True)
    parser.add_argument("--confirm-read-only", action="store_true", required=True)
    args = parser.parse_args()
    asyncio.run(rehearse(guild_id=args.guild_id, reference_times=args.reference_time))


if __name__ == "__main__":
    main()
