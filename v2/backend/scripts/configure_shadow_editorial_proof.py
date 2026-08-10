"""Idempotently add one editorial override used by the E12 shadow rehearsal."""

from __future__ import annotations

import argparse
import asyncio
import uuid

from domcek_bot.application.auth.authorization import AppRole, Principal
from domcek_bot.application.editor.events import EventEditorialService, UpdateEventOverride
from domcek_bot.config import ProcessKind, load_settings
from domcek_bot.domain.enums import DescriptionState
from domcek_bot.infrastructure.database import Database
from domcek_bot.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


async def configure(
    *, guild_id: int, actor_user_id: int, event_id: uuid.UUID, description: str
) -> None:
    database = Database(load_settings(ProcessKind.MIGRATION))
    unit_of_work = SqlAlchemyUnitOfWork(database)
    principal = Principal(
        guild_id=guild_id,
        user_id=actor_user_id,
        username="staging-editorial-proof",
        display_name="Staging editorial proof",
        avatar_url=None,
        discord_role_ids=frozenset(),
        app_roles=frozenset({AppRole.ADMIN}),
    )
    try:
        async with unit_of_work.transaction() as repositories:
            current = await repositories.event_overrides.get(event_id)
        if (
            current is not None
            and current.description_state is DescriptionState.CUSTOM
            and current.public_description == description.strip()
        ):
            print(f"Ponechaná existujúca redakčná úprava udalosti {event_id}.")
            return

        updated = await EventEditorialService(unit_of_work).update_instance(
            UpdateEventOverride(
                event_id=event_id,
                expected_version=current.version if current is not None else 0,
                public_title=current.public_title if current is not None else None,
                description_state=DescriptionState.CUSTOM,
                public_description=description,
                inclusion_decision=(current.inclusion_decision if current is not None else None),
            ),
            principal=principal,
            correlation_id="e12-shadow-editorial-proof",
        )
        print(f"Uložená redakčná úprava udalosti {event_id}, verzia {updated.version}.")
    finally:
        await database.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guild-id", type=int, required=True)
    parser.add_argument("--actor-user-id", type=int, required=True)
    parser.add_argument("--event-id", type=uuid.UUID, required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--confirm-shadow", action="store_true", required=True)
    args = parser.parse_args()
    asyncio.run(
        configure(
            guild_id=args.guild_id,
            actor_user_id=args.actor_user_id,
            event_id=args.event_id,
            description=args.description,
        )
    )


if __name__ == "__main__":
    main()
