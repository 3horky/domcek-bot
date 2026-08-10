"""Conservative, pure readiness evaluation for post-cutover publication cycles."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from itertools import pairwise
from zoneinfo import ZoneInfo

from domcek_bot.application.operations import OperationsSummary
from domcek_bot.application.publication.history import PublicationHistoryEntry
from domcek_bot.application.records import CalendarSourceRecord
from domcek_bot.domain.enums import PublicationMode, PublicationState, SyncStatus


def build_stabilization_report(
    *,
    guild_id: int,
    entries: Sequence[PublicationHistoryEntry],
    operations: OperationsSummary,
    calendars: Sequence[CalendarSourceRecord],
    automatic_publication_enabled: bool,
    open_incident_count: int,
    cycles: int,
    cutover_at: datetime,
    observed_at: datetime,
    timezone_name: str,
    calendar_max_safe_age: timedelta,
    backup_restore_verified: bool,
    discord_output_verified: bool,
) -> dict[str, object]:
    _require_aware(cutover_at, "cutover_at")
    _require_aware(observed_at, "observed_at")
    if cycles < 3:
        raise ValueError("at least three production cycles are required")
    if cutover_at > observed_at:
        raise ValueError("cutover timestamp cannot be in the future")

    eligible = sorted(
        (
            entry
            for entry in entries
            if entry.run.scheduled_for >= cutover_at
            and entry.run.completed_at is not None
            and entry.run.completed_at >= cutover_at
        ),
        key=lambda entry: (entry.run.scheduled_for, entry.run.id),
        reverse=True,
    )
    selected = eligible[:cycles]
    distinct_slots = len({entry.run.slot_key for entry in selected}) == len(selected)
    zone = ZoneInfo(timezone_name)
    local_dates = [entry.run.scheduled_for.astimezone(zone).date() for entry in selected]
    consecutive_slots = len(selected) == cycles and all(
        newer - older == timedelta(days=7) for newer, older in pairwise(local_dates)
    )

    report_entries: list[dict[str, object]] = []
    has_anomaly = False
    for index, entry in enumerate(selected):
        completed_at = entry.run.completed_at
        if completed_at is None:  # filtered above; defensive invariant for future callers
            raise ValueError("selected stabilization cycle is incomplete")
        messages = entry.messages
        item_content = {
            str(item.external_event_id): (item.final_title, item.final_description)
            for item in entry.items
            if item.external_event_id is not None
        }
        older_content: dict[str, tuple[str | None, str | None]] = {}
        if index + 1 < len(selected):
            older_content = {
                str(item.external_event_id): (item.final_title, item.final_description)
                for item in selected[index + 1].items
                if item.external_event_id is not None
            }
        repeated = sorted(item_content.keys() & older_content.keys())
        changed_repeated = sorted(
            event_id for event_id in repeated if item_content[event_id] != older_content[event_id]
        )
        everyone_count = sum((message.content or "").count("@everyone") for message in messages)
        seen_target_count = sum(message.seen_target for message in messages)
        unsent_count = sum(message.discord_message_id is None for message in messages)
        reaction_warnings = sum(message.reaction_error is not None for message in messages)
        automatic_success = (
            entry.run.state is PublicationState.SUCCEEDED_AUTOMATIC
            and entry.run.mode is PublicationMode.AUTOMATIC
        )
        anomalies = {
            "run_not_successful_automatic": not automatic_success,
            "run_warning_codes": list(entry.run.warning_codes),
            "everyone_count_not_one": everyone_count != 1,
            "seen_target_count_not_one": seen_target_count != 1,
            "unsent_messages": unsent_count,
            "reaction_warnings": reaction_warnings,
            "repeated_event_content_changed": changed_repeated,
        }
        has_anomaly = has_anomaly or any(bool(value) for value in anomalies.values())
        report_entries.append(
            {
                "run_id": str(entry.run.id),
                "slot_key": entry.run.slot_key,
                "scheduled_for": entry.run.scheduled_for.isoformat(),
                "mode": entry.run.mode.value,
                "state": entry.run.state.value,
                "completed_at": completed_at.isoformat(),
                "composer_version": entry.run.composer_version,
                "item_count": len(entry.items),
                "message_count": len(messages),
                "everyone_count": everyone_count,
                "seen_target_count": seen_target_count,
                "repeated_external_event_ids": repeated,
                "changed_repeated_external_event_ids": changed_repeated,
                "warning_codes": list(entry.run.warning_codes),
                "anomalies": anomalies,
            }
        )

    process_by_name = {process.process_name: process for process in operations.processes}
    bot = process_by_name.get("bot")
    worker = process_by_name.get("worker")
    active_calendars = tuple(calendar for calendar in calendars if calendar.active)
    calendar_health = [
        {
            "source_id": str(calendar.id),
            "status": calendar.sync_status.value,
            "last_sync_success_at": (
                calendar.last_sync_success_at.isoformat()
                if calendar.last_sync_success_at is not None
                else None
            ),
            "fresh": _calendar_is_fresh(calendar, observed_at, calendar_max_safe_age),
        }
        for calendar in active_calendars
    ]
    all_calendars_fresh = bool(active_calendars) and all(
        bool(item["fresh"]) for item in calendar_health
    )
    readiness = {
        "enough_consecutive_post_cutover_automatic_cycles": (
            len(selected) == cycles and distinct_slots and consecutive_slots and not has_anomaly
        ),
        "automatic_publication_enabled": automatic_publication_enabled,
        "no_open_publication_incidents": open_incident_count == 0,
        "bot_heartbeat_healthy": bool(bot and bot.healthy),
        "bot_gateway_connected": bool(bot and bot.state == "connected"),
        "exactly_one_active_bot": operations.active_instance_counts.get("bot", 0) == 1,
        "worker_heartbeat_healthy": bool(worker and worker.healthy),
        "worker_state_running": bool(worker and worker.state == "running"),
        "exactly_one_active_worker": operations.active_instance_counts.get("worker", 0) == 1,
        "worker_execution_mode_live": bool(
            worker and worker.details.get("publication_execution_mode") == "live"
        ),
        "all_active_calendars_fresh": all_calendars_fresh,
        "backup_restore_verified": backup_restore_verified,
        "discord_output_manually_verified": discord_output_verified,
    }
    last_sync = max(
        (
            calendar.last_sync_success_at
            for calendar in active_calendars
            if calendar.last_sync_success_at is not None
        ),
        default=None,
    )
    return {
        "guild_id": guild_id,
        "requested_cycles": cycles,
        "observed_cycles": len(selected),
        "cutover_at": cutover_at.isoformat(),
        "observed_at": observed_at.isoformat(),
        "last_calendar_sync_at": last_sync.isoformat() if last_sync else None,
        "calendar_health": calendar_health,
        "automatic_publication_enabled": automatic_publication_enabled,
        "open_publication_incident_count": open_incident_count,
        "readiness": readiness,
        "ready_for_legacy_retirement": all(readiness.values()),
        "cycles": report_entries,
    }


def _calendar_is_fresh(
    calendar: CalendarSourceRecord,
    observed_at: datetime,
    maximum_age: timedelta,
) -> bool:
    success = calendar.last_sync_success_at
    return bool(
        calendar.sync_status is SyncStatus.SUCCEEDED
        and success is not None
        and success <= observed_at
        and observed_at - success <= maximum_age
        and calendar.last_sync_error is None
    )


def _require_aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
