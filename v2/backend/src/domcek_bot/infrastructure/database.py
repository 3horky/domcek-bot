"""Async PostgreSQL lifecycle, readiness and transaction boundary."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from domcek_bot.config import Settings


class DatabaseUnavailableError(RuntimeError):
    """Raised when PostgreSQL cannot answer within the readiness deadline."""


class DatabaseProtocol(Protocol):
    async def ping(self) -> None: ...

    async def close(self) -> None: ...


class Database:
    def __init__(self, settings: Settings) -> None:
        self._timeout = settings.database_connect_timeout_seconds
        self._engine: AsyncEngine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
        )
        self._sessions = async_sessionmaker(self._engine, expire_on_commit=False)

    async def ping(self) -> None:
        try:
            async with asyncio.timeout(self._timeout):
                async with self._engine.connect() as connection:
                    await connection.execute(text("SELECT 1"))
        except (TimeoutError, OSError, RuntimeError) as exc:
            raise DatabaseUnavailableError("database readiness check failed") from exc
        except Exception as exc:  # SQLAlchemy/driver errors remain internal
            raise DatabaseUnavailableError("database readiness check failed") from exc

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncConnection]:
        async with self._engine.begin() as connection:
            yield connection

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield an uncommitted ORM session; the caller owns its transaction."""

        async with self._sessions() as session:
            yield session

    async def close(self) -> None:
        await self._engine.dispose()
