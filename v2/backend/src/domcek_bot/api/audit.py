"""Role-filtered audit read API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from domcek_bot.api.dependencies import (
    AuthContext,
    authenticated_context,
    services,
)
from domcek_bot.api.errors import ApplicationError
from domcek_bot.application.auth.authorization import AuthorizationDenied
from domcek_bot.application.records import AuditLogRecord

router = APIRouter(prefix="/api/v1/audit")


@router.get("")
async def recent_audit(
    request: Request,
    context: Annotated[AuthContext, Depends(authenticated_context)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[dict[str, object]]:
    try:
        records = await services(request).audit.list_recent(
            principal=context.principal,
            limit=limit,
        )
    except AuthorizationDenied as exc:
        raise ApplicationError(
            "forbidden",
            "Prístup bol odmietnutý",
            "Audit nie je dostupný pre vašu rolu.",
            403,
        ) from exc
    return [_audit_json(record) for record in records]


def _audit_json(value: AuditLogRecord) -> dict[str, object]:
    return {
        "id": str(value.id),
        "actor_user_id": str(value.actor_user_id) if value.actor_user_id else None,
        "action": value.action,
        "object_type": value.object_type,
        "object_id": value.object_id,
        "before": value.before_value,
        "after": value.after_value,
        "result": value.result.value,
        "correlation_id": value.correlation_id,
        "created_at": value.created_at.isoformat() if value.created_at else None,
    }
