"""Versioned instance-event editorial updates with guild isolation and audit."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime

from domcek_bot.application.auth.authorization import (
    AuthorizationDenied,
    Capability,
    Principal,
)
from domcek_bot.application.records import (
    AuditLogRecord,
    EventOverrideRecord,
    EventSeriesOverrideRecord,
    ExternalEventRecord,
)
from domcek_bot.application.unit_of_work import UnitOfWork
from domcek_bot.domain.enums import AuditResult, DescriptionState, InclusionDecision
from domcek_bot.domain.errors import OptimisticLockError


class EditorialValidationError(ValueError):
    pass


class EditorialObjectNotFound(LookupError):
    pass


@dataclass(slots=True)
class EditorialConflict(RuntimeError):
    current: EventOverrideRecord | None


@dataclass(slots=True)
class SeriesEditorialConflict(RuntimeError):
    current: EventSeriesOverrideRecord | None


@dataclass(frozen=True, slots=True)
class UpdateEventOverride:
    event_id: uuid.UUID
    expected_version: int
    public_title: str | None
    description_state: DescriptionState
    public_description: str | None
    inclusion_decision: InclusionDecision | None = None

    def __post_init__(self) -> None:
        if self.expected_version < 0:
            raise EditorialValidationError("expected version cannot be negative")
        if self.public_title is not None:
            title = self.public_title.strip()
            if not title:
                raise EditorialValidationError("public title cannot be blank")
            if len(title) > 256:
                raise EditorialValidationError("public title exceeds Discord limit")
            object.__setattr__(self, "public_title", title)
        if self.description_state is DescriptionState.CUSTOM:
            if self.public_description is None:
                raise EditorialValidationError("custom description requires a value")
            description = self.public_description.strip()
            if len(description) > 4096:
                raise EditorialValidationError("public description exceeds Discord limit")
            object.__setattr__(self, "public_description", description)
        elif self.public_description is not None:
            raise EditorialValidationError(
                "only a custom description can contain a public description value"
            )


@dataclass(frozen=True, slots=True)
class UpdateSeriesOverride:
    event_id: uuid.UUID
    expected_version: int
    public_title: str | None
    description_state: DescriptionState
    public_description: str | None

    def __post_init__(self) -> None:
        if self.expected_version < 0:
            raise EditorialValidationError("expected version cannot be negative")
        if self.public_title is not None:
            title = self.public_title.strip()
            if not title:
                raise EditorialValidationError("public title cannot be blank")
            if len(title) > 256:
                raise EditorialValidationError("public title exceeds Discord limit")
            object.__setattr__(self, "public_title", title)
        if self.description_state is DescriptionState.CUSTOM:
            if self.public_description is None:
                raise EditorialValidationError("custom description requires a value")
            description = self.public_description.strip()
            if len(description) > 4096:
                raise EditorialValidationError("public description exceeds Discord limit")
            object.__setattr__(self, "public_description", description)
        elif self.public_description is not None:
            raise EditorialValidationError(
                "only a custom description can contain a public description value"
            )


class EventEditorialService:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def update_instance(
        self,
        command: UpdateEventOverride,
        *,
        principal: Principal,
        correlation_id: str,
        now: datetime | None = None,
    ) -> EventOverrideRecord:
        changed_inclusion = False
        denied = False
        current: EventOverrideRecord | None = None
        result: EventOverrideRecord | None = None
        timestamp = _aware_now(now)
        async with self._unit_of_work.transaction() as repositories:
            event = await repositories.external_events.get(command.event_id)
            if event is None:
                raise EditorialObjectNotFound("event was not found")
            source = await repositories.calendar_sources.get(event.calendar_source_id)
            if source is None or source.guild_id != principal.guild_id:
                raise EditorialObjectNotFound("event was not found")
            current = await repositories.event_overrides.get(command.event_id)
            inclusion = (
                command.inclusion_decision
                if command.inclusion_decision is not None
                else (current.inclusion_decision if current is not None else InclusionDecision.AUTO)
            )
            changed_inclusion = inclusion != (
                current.inclusion_decision if current else InclusionDecision.AUTO
            )
            try:
                principal.require(Capability.EDIT_CONTENT)
                if changed_inclusion:
                    principal.require(Capability.FORCE_INCLUSION)
            except AuthorizationDenied:
                denied = True
                await repositories.audit_logs.add(
                    _audit(
                        principal=principal,
                        command=command,
                        current=current,
                        after=None,
                        result=AuditResult.FAILED,
                        correlation_id=correlation_id,
                        timestamp=timestamp,
                        action="event_override.update_denied",
                    )
                )
            else:
                if current is None:
                    if command.expected_version != 0:
                        raise EditorialConflict(None)
                    result = EventOverrideRecord(
                        external_event_id=command.event_id,
                        public_title=command.public_title,
                        description_state=command.description_state,
                        public_description=command.public_description,
                        inclusion_decision=inclusion,
                        updated_by_user_id=principal.user_id,
                    )
                    await repositories.event_overrides.add(result)
                else:
                    if command.expected_version != current.version:
                        raise EditorialConflict(current)
                    candidate = replace(
                        current,
                        public_title=command.public_title,
                        description_state=command.description_state,
                        public_description=command.public_description,
                        inclusion_decision=inclusion,
                        updated_by_user_id=principal.user_id,
                    )
                    try:
                        version = await repositories.event_overrides.update(
                            candidate, expected_version=command.expected_version
                        )
                    except OptimisticLockError as exc:
                        latest = await repositories.event_overrides.get(command.event_id)
                        raise EditorialConflict(latest) from exc
                    result = replace(candidate, version=version)
                await repositories.audit_logs.add(
                    _audit(
                        principal=principal,
                        command=command,
                        current=current,
                        after=result,
                        result=AuditResult.SUCCEEDED,
                        correlation_id=correlation_id,
                        timestamp=timestamp,
                        action="event_override.updated",
                    )
                )
        if denied:
            raise AuthorizationDenied("event editorial update is not allowed for this principal")
        if result is None:
            raise RuntimeError("event editorial update produced no result")
        return result

    async def update_series(
        self,
        command: UpdateSeriesOverride,
        *,
        principal: Principal,
        correlation_id: str,
        now: datetime | None = None,
    ) -> EventSeriesOverrideRecord:
        timestamp = _aware_now(now)
        denied = False
        result: EventSeriesOverrideRecord | None = None
        async with self._unit_of_work.transaction() as repositories:
            event = await repositories.external_events.get(command.event_id)
            if event is None:
                raise EditorialObjectNotFound("event was not found")
            source = await repositories.calendar_sources.get(event.calendar_source_id)
            if source is None or source.guild_id != principal.guild_id:
                raise EditorialObjectNotFound("event was not found")
            if event.series_key is None:
                raise EditorialValidationError("event is not part of a recurring series")
            effective_key, effective_at, effective_date = _series_effective_identity(event)
            current = await repositories.event_series_overrides.get_effective(
                event.calendar_source_id,
                event.series_key,
                effective_key,
            )
            try:
                principal.require(Capability.EDIT_CONTENT)
            except AuthorizationDenied:
                denied = True
                await repositories.audit_logs.add(
                    _series_audit(
                        principal=principal,
                        event_id=event.id,
                        current=current,
                        after=None,
                        result=AuditResult.FAILED,
                        correlation_id=correlation_id,
                        timestamp=timestamp,
                        action="event_series_override.update_denied",
                    )
                )
            else:
                if current is None:
                    if command.expected_version != 0:
                        raise SeriesEditorialConflict(None)
                    result = EventSeriesOverrideRecord(
                        id=uuid.uuid4(),
                        calendar_source_id=event.calendar_source_id,
                        series_key=event.series_key,
                        effective_from_key=effective_key,
                        effective_all_day=event.is_all_day,
                        effective_from_at=effective_at,
                        effective_from_date=effective_date,
                        public_title=command.public_title,
                        description_state=command.description_state,
                        public_description=command.public_description,
                        updated_by_user_id=principal.user_id,
                    )
                    await repositories.event_series_overrides.add(result)
                else:
                    if current.version != command.expected_version:
                        raise SeriesEditorialConflict(current)
                    candidate = replace(
                        current,
                        public_title=command.public_title,
                        description_state=command.description_state,
                        public_description=command.public_description,
                        updated_by_user_id=principal.user_id,
                    )
                    try:
                        version = await repositories.event_series_overrides.update(
                            candidate, expected_version=command.expected_version
                        )
                    except OptimisticLockError as exc:
                        latest = await repositories.event_series_overrides.get_effective(
                            event.calendar_source_id,
                            event.series_key,
                            effective_key,
                        )
                        raise SeriesEditorialConflict(latest) from exc
                    result = replace(candidate, version=version)
                await repositories.audit_logs.add(
                    _series_audit(
                        principal=principal,
                        event_id=event.id,
                        current=current,
                        after=result,
                        result=AuditResult.SUCCEEDED,
                        correlation_id=correlation_id,
                        timestamp=timestamp,
                        action="event_series_override.updated",
                    )
                )
        if denied:
            raise AuthorizationDenied("series editorial update is not allowed")
        if result is None:
            raise RuntimeError("series editorial update produced no result")
        return result


def _audit(
    *,
    principal: Principal,
    command: UpdateEventOverride,
    current: EventOverrideRecord | None,
    after: EventOverrideRecord | None,
    result: AuditResult,
    correlation_id: str,
    timestamp: datetime,
    action: str,
) -> AuditLogRecord:
    return AuditLogRecord(
        id=uuid.uuid4(),
        guild_id=principal.guild_id,
        actor_user_id=principal.user_id,
        action=action,
        object_type="event_override",
        object_id=str(command.event_id),
        before_value=_override_json(current),
        after_value=_override_json(after),
        result=result,
        correlation_id=correlation_id,
        created_at=timestamp,
    )


def _override_json(value: EventOverrideRecord | None) -> dict[str, object] | None:
    if value is None:
        return None
    return {
        "public_title": value.public_title,
        "description_state": value.description_state.value,
        "public_description": value.public_description,
        "inclusion_decision": value.inclusion_decision.value,
        "version": value.version,
    }


def _series_audit(
    *,
    principal: Principal,
    event_id: uuid.UUID,
    current: EventSeriesOverrideRecord | None,
    after: EventSeriesOverrideRecord | None,
    result: AuditResult,
    correlation_id: str,
    timestamp: datetime,
    action: str,
) -> AuditLogRecord:
    return AuditLogRecord(
        id=uuid.uuid4(),
        guild_id=principal.guild_id,
        actor_user_id=principal.user_id,
        action=action,
        object_type="event_series_override",
        object_id=str(after.id if after is not None else current.id if current else event_id),
        before_value=_series_json(current),
        after_value=_series_json(after),
        result=result,
        correlation_id=correlation_id,
        created_at=timestamp,
    )


def _series_json(value: EventSeriesOverrideRecord | None) -> dict[str, object] | None:
    if value is None:
        return None
    return {
        "id": str(value.id),
        "effective_from_key": value.effective_from_key,
        "public_title": value.public_title,
        "description_state": value.description_state.value,
        "public_description": value.public_description,
        "version": value.version,
    }


def _series_effective_identity(
    event: ExternalEventRecord,
) -> tuple[str, datetime | None, date | None]:
    if event.is_all_day:
        value = event.original_start_key or (
            event.starts_on.isoformat() if event.starts_on is not None else None
        )
        if value is None:
            raise EditorialValidationError("all-day occurrence has no effective date")
        try:
            effective_date = date.fromisoformat(value)
        except ValueError as exc:
            raise EditorialValidationError("all-day occurrence key is invalid") from exc
        return value, None, effective_date
    value = event.original_start_key or (
        event.starts_at.isoformat() if event.starts_at is not None else None
    )
    if value is None:
        raise EditorialValidationError("timed occurrence has no effective time")
    try:
        effective_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EditorialValidationError("timed occurrence key is invalid") from exc
    if effective_at.tzinfo is None or effective_at.utcoffset() is None:
        raise EditorialValidationError("timed occurrence key must be timezone-aware")
    return value, effective_at, None


def _aware_now(value: datetime | None) -> datetime:
    timestamp = value or datetime.now(UTC)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise EditorialValidationError("audit time must be timezone-aware")
    return timestamp
