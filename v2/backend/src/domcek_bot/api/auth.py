"""Discord OAuth login, server session and current-user endpoints."""

from __future__ import annotations

from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse

from domcek_bot.api.dependencies import (
    CSRF_COOKIE,
    OAUTH_STATE_COOKIE,
    SESSION_COOKIE,
    AuthContext,
    authenticated_context,
    csrf_context,
    services,
)
from domcek_bot.api.errors import ApplicationError
from domcek_bot.application.auth.contracts import DiscordIdentityError, DiscordMemberNotFound
from domcek_bot.application.auth.oauth_state import InvalidOAuthState
from domcek_bot.application.auth.service import REQUIRED_OAUTH_SCOPES, LoginDenied
from domcek_bot.config import Settings

router = APIRouter(prefix="/api/v1")


@router.get("/auth/discord/login", include_in_schema=False)
async def discord_login(request: Request, return_to: str = Query(default="/")) -> RedirectResponse:
    settings = _settings(request)
    state = services(request).oauth_state.issue(return_to)
    query = urlencode(
        {
            "client_id": settings.resolved_discord_oauth_client_id,
            "redirect_uri": settings.discord_oauth_redirect_uri,
            "response_type": "code",
            "scope": " ".join(sorted(REQUIRED_OAUTH_SCOPES)),
            "state": state.value,
            "prompt": "consent",
        }
    )
    response = RedirectResponse(f"https://discord.com/oauth2/authorize?{query}", status_code=302)
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state.value,
        max_age=settings.oauth_state_lifetime_minutes * 60,
        secure=settings.secure_cookies,
        httponly=True,
        samesite="lax",
        path="/api/v1/auth/discord/callback",
    )
    return response


@router.get("/auth/discord/callback", include_in_schema=False)
async def discord_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    settings = _settings(request)
    try:
        verified = services(request).oauth_state.verify(
            state, request.cookies.get(OAUTH_STATE_COOKIE)
        )
        if error is not None or not code:
            raise LoginDenied("Discord authorization was cancelled")
        result = await services(request).auth.login(code)
    except InvalidOAuthState as exc:
        raise ApplicationError(
            "oauth_state_rejected",
            "Prihlásenie bolo odmietnuté",
            "Prihlasovacia požiadavka vypršala alebo nebola platná.",
            400,
        ) from exc
    except (LoginDenied, DiscordMemberNotFound) as exc:
        raise ApplicationError(
            "login_denied",
            "Prístup nebol povolený",
            "Discord účet nemá prístup k tejto administrácii.",
            403,
        ) from exc
    except DiscordIdentityError as exc:
        raise ApplicationError(
            "discord_oauth_unavailable",
            "Discord prihlásenie zlyhalo",
            "Prihlásenie momentálne nie je dostupné. Skúste to neskôr.",
            503,
        ) from exc

    response = RedirectResponse(
        f"{settings.frontend_base_url.rstrip('/')}{verified.return_to}", status_code=303
    )
    response.delete_cookie(OAUTH_STATE_COOKIE, path="/api/v1/auth/discord/callback")
    response.set_cookie(
        SESSION_COOKIE,
        result.session.session_token,
        max_age=settings.session_lifetime_hours * 3600,
        secure=settings.secure_cookies,
        httponly=True,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        result.session.csrf_token,
        max_age=settings.session_lifetime_hours * 3600,
        secure=settings.secure_cookies,
        httponly=False,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/session")
async def current_session(
    context: Annotated[AuthContext, Depends(authenticated_context)],
) -> dict[str, object]:
    principal = context.principal
    return {
        "authenticated": True,
        "user": {
            "id": str(principal.user_id),
            "username": principal.username,
            "display_name": principal.display_name,
            "avatar_url": principal.avatar_url,
        },
        "guild_id": str(principal.guild_id),
        "roles": sorted(role.value for role in principal.app_roles),
        "capabilities": sorted(capability.value for capability in principal.capabilities),
        "expires_at": context.session.expires_at.isoformat(),
    }


@router.post("/auth/logout", status_code=204)
async def logout(
    request: Request,
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> Response:
    await services(request).sessions.revoke(context.session)
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return response


def _settings(request: Request) -> Settings:
    value = getattr(request.app.state, "settings", None)
    if not isinstance(value, Settings):
        raise RuntimeError("API settings are missing")
    return value
