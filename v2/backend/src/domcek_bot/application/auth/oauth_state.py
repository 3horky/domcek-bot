"""Short-lived signed OAuth state with strict local return paths."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit


class InvalidOAuthState(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class OAuthState:
    value: str
    return_to: str
    expires_at: datetime


class OAuthStateCodec:
    def __init__(self, *, secret: str, lifetime: timedelta) -> None:
        self._secret = secret.encode()
        self._lifetime = lifetime

    def issue(self, return_to: str, *, now: datetime | None = None) -> OAuthState:
        current = _aware_now(now)
        safe_return = safe_return_path(return_to)
        expires = current + self._lifetime
        payload = json.dumps(
            {
                "exp": int(expires.timestamp()),
                "nonce": secrets.token_urlsafe(24),
                "return_to": safe_return,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        encoded = _encode(payload)
        signature = _encode(hmac.new(self._secret, encoded.encode(), hashlib.sha256).digest())
        return OAuthState(f"{encoded}.{signature}", safe_return, expires)

    def verify(
        self,
        supplied: str | None,
        cookie: str | None,
        *,
        now: datetime | None = None,
    ) -> OAuthState:
        if not supplied or not cookie or not hmac.compare_digest(supplied, cookie):
            raise InvalidOAuthState("OAuth state is missing or does not match")
        try:
            encoded, signature = supplied.split(".", 1)
            expected = _encode(hmac.new(self._secret, encoded.encode(), hashlib.sha256).digest())
            if not hmac.compare_digest(signature, expected):
                raise InvalidOAuthState("OAuth state signature is invalid")
            payload = json.loads(_decode(encoded))
            expires = datetime.fromtimestamp(int(payload["exp"]), tz=UTC)
            return_to = safe_return_path(str(payload["return_to"]))
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise InvalidOAuthState("OAuth state is malformed") from exc
        if _aware_now(now) > expires:
            raise InvalidOAuthState("OAuth state has expired")
        return OAuthState(supplied, return_to, expires)


def safe_return_path(value: str | None) -> str:
    candidate = value or "/"
    parsed = urlsplit(candidate)
    if (
        not candidate.startswith("/")
        or candidate.startswith("//")
        or "\\" in candidate
        or parsed.scheme
        or parsed.netloc
        or any(ord(character) < 32 for character in candidate)
    ):
        raise InvalidOAuthState("return path is not allowed")
    return candidate


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _aware_now(value: datetime | None) -> datetime:
    current = value or datetime.now(UTC)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("OAuth state time must be timezone-aware")
    return current
