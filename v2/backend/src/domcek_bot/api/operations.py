"""Authenticated operational status without per-render external API calls."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from domcek_bot.api.dependencies import AuthContext, authenticated_context, services
from domcek_bot.api.errors import ApplicationError
from domcek_bot.application.auth.authorization import AuthorizationDenied

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])


@router.get("/summary", response_class=JSONResponse)
async def operations_summary(
    request: Request,
    context: Annotated[AuthContext, Depends(authenticated_context)],
) -> JSONResponse:
    operations = services(request).operations
    if operations is None:
        raise ApplicationError(
            "operations_unavailable",
            "Prevádzkový stav nie je dostupný",
            "Carlo zatiaľ nevie zostaviť rozšírenú diagnostiku.",
            503,
        )
    try:
        summary = await operations.summary(context.principal)
    except AuthorizationDenied as exc:
        raise ApplicationError(
            "operations_forbidden",
            "Prístup nebol povolený",
            "Na zobrazenie prevádzkového stavu nemáte oprávnenie.",
            403,
        ) from exc
    except LookupError as exc:
        raise ApplicationError(
            "guild_not_configured",
            "Server nie je nakonfigurovaný",
            "Prevádzkový stav zatiaľ nie je dostupný.",
            409,
        ) from exc

    metrics = summary.publication_metrics
    return JSONResponse(
        {
            "observed_at": summary.observed_at.isoformat(),
            "next_publication": {
                "slot_key": summary.next_slot_key,
                "scheduled_for": summary.next_scheduled_for.isoformat(),
            },
            "processes": [
                {
                    "process_name": process.process_name,
                    "instance_id": str(process.instance_id),
                    "state": process.state,
                    "healthy": process.healthy,
                    "started_at": process.started_at.isoformat(),
                    "last_seen_at": process.last_seen_at.isoformat(),
                    "details": process.details,
                }
                for process in summary.processes
            ],
            "active_instance_counts": summary.active_instance_counts,
            "calendars": [
                {
                    "id": str(calendar.id),
                    "display_name": calendar.display_name,
                    "active": calendar.active,
                    "sync_status": calendar.sync_status.value,
                    "last_sync_attempt_at": _iso(calendar.last_sync_attempt_at),
                    "last_sync_success_at": _iso(calendar.last_sync_success_at),
                    "last_sync_error": calendar.last_sync_error,
                }
                for calendar in summary.calendars
            ],
            "publication_metrics": {
                "sample_size": metrics.sample_size,
                "successful": metrics.successful,
                "failed": metrics.failed,
                "in_progress": metrics.in_progress,
                "skipped": metrics.skipped,
            },
            "recent_tasks": [
                {
                    "id": str(task.id),
                    "task_type": task.task_type,
                    "state": task.state.value,
                    "scheduled_for": task.scheduled_for.isoformat(),
                    "started_at": _iso(task.started_at),
                    "completed_at": _iso(task.completed_at),
                    "error_code": task.error_code,
                }
                for task in summary.recent_tasks
            ],
        }
    )


def _iso(value: object) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else None
