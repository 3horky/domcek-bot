"""Idempotent creation of the first server configuration."""

from __future__ import annotations

from domcek_bot.application.records import GuildConfigRecord
from domcek_bot.application.unit_of_work import UnitOfWork


async def ensure_guild_config(unit_of_work: UnitOfWork, desired: GuildConfigRecord) -> bool:
    """Create the initial guild row once and never overwrite administered values."""
    async with unit_of_work.transaction() as repositories:
        current = await repositories.guild_configs.get(desired.guild_id)
        if current is not None:
            return False
        await repositories.guild_configs.add(desired)
        return True
