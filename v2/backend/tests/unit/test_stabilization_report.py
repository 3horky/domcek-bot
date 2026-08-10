from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from domcek_bot.application.operations import (
    OperationsSummary,
    ProcessStatus,
    PublicationMetrics,
)
from domcek_bot.application.publication.history import PublicationHistoryEntry
from domcek_bot.application.publication.stabilization import build_stabilization_report
from domcek_bot.application.records import (
    CalendarSourceRecord,
    PublicationItemRecord,
    PublicationMessageRecord,
    PublicationRunRecord,
)
from domcek_bot.domain.enums import (
    PublicationItemType,
    PublicationMode,
    PublicationState,
    SyncStatus,
)

GUILD_ID = 1535774834955391047
OBSERVED_AT = datetime(2026, 2, 3, 12, tzinfo=UTC)
CUTOVER_AT = datetime(2026, 1, 1, tzinfo=UTC)
REPEATED_EVENT_ID = uuid.uuid4()


def _entry(
    scheduled_for: datetime,
    *,
    state: PublicationState = PublicationState.SUCCEEDED_AUTOMATIC,
    mode: PublicationMode = PublicationMode.AUTOMATIC,
    title: str = "Upravený titulok",
    description: str = "Zachovaný redakčný popis",
) -> PublicationHistoryEntry:
    run_id = uuid.uuid4()
    run = PublicationRunRecord(
        id=run_id,
        guild_id=GUILD_ID,
        slot_key=f"{GUILD_ID}:{scheduled_for.date().isoformat()}T20:00:Europe/Bratislava",
        scheduled_for=scheduled_for,
        mode=mode,
        state=state,
        attempt=1,
        idempotency_key=str(run_id),
        composer_version="e4-v2",
        intro_text="Úvod",
        intro_prompt_version="v1",
        intro_used_fallback=False,
        completed_at=scheduled_for + timedelta(minutes=1),
    )
    item = PublicationItemRecord(
        id=uuid.uuid4(),
        publication_run_id=run_id,
        item_type=PublicationItemType.EXTERNAL_EVENT,
        position=0,
        final_title=title,
        final_description=description,
        external_event_id=REPEATED_EVENT_ID,
    )
    message = PublicationMessageRecord(
        id=uuid.uuid4(),
        publication_run_id=run_id,
        position=0,
        discord_channel_id=123,
        part_key="part-1",
        nonce="nonce",
        content="@everyone Úvod",
        embeds=(),
        allowed_mentions=("everyone",),
        seen_target=True,
        discord_message_id=456,
    )
    return PublicationHistoryEntry(run, (item,), (message,))


def _operations() -> OperationsSummary:
    processes = tuple(
        ProcessStatus(
            process_name=name,
            instance_id=uuid.uuid4(),
            state="running" if name == "worker" else "connected",
            healthy=True,
            started_at=OBSERVED_AT - timedelta(days=1),
            last_seen_at=OBSERVED_AT,
            details={"publication_execution_mode": "live"} if name == "worker" else {},
        )
        for name in ("bot", "worker")
    )
    return OperationsSummary(
        observed_at=OBSERVED_AT,
        processes=processes,
        active_instance_counts={"bot": 1, "worker": 1},
        calendars=(),
        publication_metrics=PublicationMetrics(3, 3, 0, 0, 0),
        recent_tasks=(),
        next_slot_key="next",
        next_scheduled_for=OBSERVED_AT + timedelta(days=6),
    )


def _calendar(
    *,
    status: SyncStatus = SyncStatus.SUCCEEDED,
    last_success: datetime | None = OBSERVED_AT - timedelta(hours=1),
) -> CalendarSourceRecord:
    return CalendarSourceRecord(
        id=uuid.uuid4(),
        guild_id=GUILD_ID,
        provider="google",
        external_calendar_id=str(uuid.uuid4()),
        display_name="Kalendár",
        sync_status=status,
        last_sync_success_at=last_success,
        last_sync_error="sync_failed" if status is SyncStatus.FAILED else None,
    )


def _healthy_entries() -> list[PublicationHistoryEntry]:
    return [_entry(datetime(2026, 1, day, 19, tzinfo=UTC)) for day in (26, 19, 12)]


def _report(
    *,
    entries: list[PublicationHistoryEntry] | None = None,
    calendars: tuple[CalendarSourceRecord, ...] | None = None,
    automatic_publication_enabled: bool = True,
    operations: OperationsSummary | None = None,
) -> dict[str, object]:
    return build_stabilization_report(
        guild_id=GUILD_ID,
        entries=entries or _healthy_entries(),
        operations=operations or _operations(),
        calendars=calendars or (_calendar(),),
        automatic_publication_enabled=automatic_publication_enabled,
        open_incident_count=0,
        cycles=3,
        cutover_at=CUTOVER_AT,
        observed_at=OBSERVED_AT,
        timezone_name="Europe/Bratislava",
        calendar_max_safe_age=timedelta(hours=6),
        backup_restore_verified=True,
        discord_output_verified=True,
    )


def test_three_consecutive_post_cutover_automatic_cycles_can_pass() -> None:
    report = _report()
    assert report["ready_for_legacy_retirement"] is True


def test_manual_cycle_cannot_count() -> None:
    entries = _healthy_entries()
    entries[1] = replace(
        entries[1],
        run=replace(
            entries[1].run,
            state=PublicationState.SUCCEEDED_MANUAL,
            mode=PublicationMode.MANUAL,
        ),
    )
    assert _report(entries=entries)["ready_for_legacy_retirement"] is False


def test_pre_cutover_cycle_and_missing_week_cannot_count() -> None:
    pre_cutover = _healthy_entries()
    pre_cutover[2] = _entry(datetime(2025, 12, 29, 19, tzinfo=UTC))
    assert _report(entries=pre_cutover)["ready_for_legacy_retirement"] is False

    gap = [_entry(datetime(2026, 1, day, 19, tzinfo=UTC)) for day in (26, 19, 5)]
    assert _report(entries=gap)["ready_for_legacy_retirement"] is False


def test_changed_repeated_editorial_content_cannot_count() -> None:
    entries = _healthy_entries()
    entries[0] = _entry(datetime(2026, 1, 26, 19, tzinfo=UTC), description="Iný popis")
    report = _report(entries=entries)
    assert report["ready_for_legacy_retirement"] is False
    cycles = report["cycles"]
    assert isinstance(cycles, list)
    assert cycles[0]["changed_repeated_external_event_ids"] == [str(REPEATED_EVENT_ID)]


def test_every_active_calendar_must_be_fresh_and_successful() -> None:
    failed = _calendar(status=SyncStatus.FAILED, last_success=None)
    assert _report(calendars=(_calendar(), failed))["ready_for_legacy_retirement"] is False
    stale = _calendar(last_success=OBSERVED_AT - timedelta(days=2))
    assert _report(calendars=(stale,))["ready_for_legacy_retirement"] is False


def test_automatic_publication_must_still_be_enabled() -> None:
    assert _report(automatic_publication_enabled=False)["ready_for_legacy_retirement"] is False


def test_unreviewed_run_warning_cannot_count_as_anomaly_free() -> None:
    entries = _healthy_entries()
    entries[0] = replace(
        entries[0],
        run=replace(entries[0].run, warning_codes=("intro_generator_fallback",)),
    )
    report = _report(entries=entries)
    assert report["ready_for_legacy_retirement"] is False
    cycles = report["cycles"]
    assert isinstance(cycles, list)
    assert cycles[0]["anomalies"]["run_warning_codes"] == ["intro_generator_fallback"]


def test_duplicate_or_not_running_process_cannot_retire_legacy() -> None:
    duplicate = replace(_operations(), active_instance_counts={"bot": 1, "worker": 2})
    assert _report(operations=duplicate)["ready_for_legacy_retirement"] is False

    current = _operations()
    unhealthy_state = replace(
        current,
        processes=tuple(
            replace(process, state="starting") if process.process_name == "worker" else process
            for process in current.processes
        ),
    )
    assert _report(operations=unhealthy_state)["ready_for_legacy_retirement"] is False
