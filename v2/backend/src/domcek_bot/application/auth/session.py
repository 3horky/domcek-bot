"""Opaque server-session creation, verification and revocation."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from domcek_bot.application.records import WebSessionRecord
from domcek_bot.application.unit_of_work import UnitOfWork


class InvalidSession(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class IssuedSession:
    record: WebSessionRecord
    session_token: str
    csrf_token: str


class SessionService:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        *,
        secret: str,
        lifetime: timedelta,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._secret = secret.encode()
        self._lifetime = lifetime

    async def create(
        self, *, guild_id: int, user_id: int, now: datetime | None = None
    ) -> IssuedSession:
        current = _aware_now(now)
        session_token = secrets.token_urlsafe(48)
        csrf_token = secrets.token_urlsafe(32)
        record = WebSessionRecord(
            id=uuid.uuid4(),
            guild_id=guild_id,
            discord_user_id=user_id,
            session_token_hash=self.hash_token(session_token),
            csrf_token_hash=self.hash_token(csrf_token),
            created_at=current,
            last_seen_at=current,
            expires_at=current + self._lifetime,
        )
        async with self._unit_of_work.transaction() as repositories:
            await repositories.web_sessions.add(record)
        return IssuedSession(record, session_token, csrf_token)

    async def authenticate(
        self, session_token: str | None, *, now: datetime | None = None
    ) -> WebSessionRecord:
        if not session_token:
            raise InvalidSession("session is missing")
        current = _aware_now(now)
        async with self._unit_of_work.transaction() as repositories:
            record = await repositories.web_sessions.get_active_by_token_hash(
                self.hash_token(session_token), now=current
            )
            if record is None:
                raise InvalidSession("session is invalid or expired")
            await repositories.web_sessions.touch(record.id, seen_at=current)
        return record

    def verify_csrf(self, record: WebSessionRecord, cookie: str | None, header: str | None) -> None:
        if not cookie or not header or not hmac.compare_digest(cookie, header):
            raise InvalidSession("CSRF token is missing or does not match")
        if not hmac.compare_digest(record.csrf_token_hash, self.hash_token(header)):
            raise InvalidSession("CSRF token is invalid")

    async def revoke(self, record: WebSessionRecord, *, now: datetime | None = None) -> None:
        current = _aware_now(now)
        async with self._unit_of_work.transaction() as repositories:
            await repositories.web_sessions.revoke(record.id, revoked_at=current)

    def hash_token(self, token: str) -> str:
        return hmac.new(self._secret, token.encode(), hashlib.sha256).hexdigest()


def _aware_now(value: datetime | None) -> datetime:
    current = value or datetime.now(UTC)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("session time must be timezone-aware")
    return current
