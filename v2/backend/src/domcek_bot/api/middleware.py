"""Request context and correlation identifiers."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from collections import defaultdict, deque
from collections.abc import Callable
from http.cookies import SimpleCookie
from math import ceil
from uuid import uuid4

import structlog
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from domcek_bot.api.dependencies import SESSION_COOKIE

CORRELATION_HEADER = "X-Correlation-ID"
VALID_CORRELATION_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class RateLimitMiddleware:
    """Bounded per-process limiter for OAuth and authenticated mutations."""

    _MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

    def __init__(
        self,
        app: ASGIApp,
        *,
        window_seconds: int,
        oauth_limit: int,
        mutation_limit: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.app = app
        self._window = float(window_seconds)
        self._oauth_limit = oauth_limit
        self._mutation_limit = mutation_limit
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        category = self._category(scope)
        if category is None:
            await self.app(scope, receive, send)
            return
        name, limit = category
        now = self._clock()
        key = f"{name}:{self._client_key(scope)}"
        retry_after = await self._record(key, limit, now)
        if retry_after is None:
            await self.app(scope, receive, send)
            return
        correlation_id = str(scope.get("state", {}).get("correlation_id", "unknown"))
        body = json.dumps(
            {
                "type": "https://domcek.invalid/problems/rate_limited",
                "title": "Príliš veľa požiadaviek",
                "status": 429,
                "detail": "Počkajte chvíľu a skúste požiadavku znova.",
                "code": "rate_limited",
                "correlation_id": correlation_id,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/problem+json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"retry-after", str(retry_after).encode()),
                    (b"cache-control", b"no-store"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})

    def _category(self, scope: Scope) -> tuple[str, int] | None:
        path = str(scope.get("path", ""))
        method = str(scope.get("method", "GET")).upper()
        if path in {
            "/api/v1/auth/discord/login",
            "/api/v1/auth/discord/callback",
        }:
            return f"oauth:{path}", self._oauth_limit
        if path.startswith("/api/v1/") and method in self._MUTATING_METHODS:
            return "mutation", self._mutation_limit
        return None

    def _client_key(self, scope: Scope) -> str:
        headers = Headers(scope=scope)
        session = _cookie_value(headers.get("cookie"), SESSION_COOKIE)
        if session:
            return "session:" + hashlib.sha256(session.encode()).hexdigest()[:32]
        client = scope.get("client")
        host = str(client[0]) if client else "unknown"
        return "client:" + host

    async def _record(self, key: str, limit: int, now: float) -> int | None:
        cutoff = now - self._window
        async with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= limit:
                return max(1, ceil(hits[0] + self._window - now))
            hits.append(now)
            if len(self._hits) > 10_000:
                self._remove_idle(cutoff)
        return None

    def _remove_idle(self, cutoff: float) -> None:
        idle = [key for key, hits in self._hits.items() if not hits or hits[-1] <= cutoff]
        for key in idle:
            self._hits.pop(key, None)


def _cookie_value(raw_cookie: str | None, name: str) -> str | None:
    if not raw_cookie:
        return None
    cookies = SimpleCookie()
    try:
        cookies.load(raw_cookie)
    except ValueError:
        return None
    morsel = cookies.get(name)
    return morsel.value if morsel is not None else None


class CorrelationIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        supplied = Headers(scope=scope).get(CORRELATION_HEADER)
        correlation_id = (
            supplied if supplied and VALID_CORRELATION_ID.fullmatch(supplied) else str(uuid4())
        )
        scope.setdefault("state", {})["correlation_id"] = correlation_id
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((CORRELATION_HEADER.lower().encode(), correlation_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            structlog.contextvars.unbind_contextvars("correlation_id")


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path", ""))

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                existing_names = {name.lower() for name, _ in headers}
                headers.extend(
                    [
                        (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                    ]
                )
                if path.startswith("/api/v1/") and b"cache-control" not in existing_names:
                    headers.append((b"cache-control", b"no-store"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)
