"""Versioned manual-event and INFO-announcement editorial operations."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime, timedelta
from typing import Literal, overload

from domcek_bot.application.auth.authorization import (
    AuthorizationDenied,
    Capability,
    Principal,
)
from domcek_bot.application.publication.formatting import valid_public_url
from domcek_bot.application.records import (
    AuditLogRecord,
    InfoAnnouncementRecord,
    ManualEventRecord,
)
from domcek_bot.application.repositories import (
    InfoAnnouncementRepository,
    ManualEventRepository,
)
from domcek_bot.application.unit_of_work import UnitOfWork
from domcek_bot.domain.enums import AuditResult
from domcek_bot.domain.errors import DomainValidationError, OptimisticLockError
from domcek_bot.domain.time import timezone


class ContentValidationError(ValueError):
    pass


class ContentObjectNotFound(LookupError):
    pass


EditableRecord = ManualEventRecord | InfoAnnouncementRecord


@dataclass(slots=True)
class ContentConflict(RuntimeError):
    current: EditableRecord | None


@dataclass(frozen=True, slots=True)
class ManualEventValues:
    title: str
    is_all_day: bool
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    timezone: str = "Europe/Bratislava"
    description: str | None = None
    link_url: str | None = None
    active: bool = True

    def __post_init__(self) -> None:
        _validate_title(self.title)
        _validate_optional_text(self.description, "description", 4096)
        _validate_url(self.link_url, "link URL")
        object.__setattr__(self, "title", self.title.strip())
        object.__setattr__(self, "description", _optional_stripped(self.description))
        object.__setattr__(self, "link_url", _optional_stripped(self.link_url))
        try:
            timezone(self.timezone)
        except DomainValidationError as exc:
            raise ContentValidationError("timezone is not a valid IANA timezone") from exc
        if self.is_all_day:
            if self.starts_on is None:
                raise ContentValidationError("all-day event requires a start date")
            if self.starts_at is not None or self.ends_at is not None:
                raise ContentValidationError("all-day event cannot contain date-time values")
            end = self.ends_on or self.starts_on + timedelta(days=1)
            if end <= self.starts_on:
                raise ContentValidationError("all-day event end must be after its start")
            object.__setattr__(self, "ends_on", end)
        else:
            if self.starts_at is None:
                raise ContentValidationError("timed event requires a start date-time")
            if self.starts_on is not None or self.ends_on is not None:
                raise ContentValidationError("timed event cannot contain all-day dates")
            _require_aware(self.starts_at, "event start")
            if self.ends_at is not None:
                _require_aware(self.ends_at, "event end")
                if self.ends_at <= self.starts_at:
                    raise ContentValidationError("event end must be after its start")


@dataclass(frozen=True, slots=True)
class CreateManualEvent:
    values: ManualEventValues


@dataclass(frozen=True, slots=True)
class UpdateManualEvent:
    event_id: uuid.UUID
    expected_version: int
    values: ManualEventValues

    def __post_init__(self) -> None:
        if self.expected_version < 1:
            raise ContentValidationError("expected version must be positive")


@dataclass(frozen=True, slots=True)
class InfoAnnouncementValues:
    title: str
    description: str
    valid_from: date
    valid_until: date
    link_url: str | None = None
    image_url: str | None = None
    active: bool = True

    def __post_init__(self) -> None:
        _validate_title(self.title)
        if not self.description.strip():
            raise ContentValidationError("INFO description cannot be blank")
        _validate_optional_text(self.description, "INFO description", 4096)
        if self.valid_until < self.valid_from:
            raise ContentValidationError("INFO validity end cannot precede its start")
        _validate_url(self.link_url, "link URL")
        _validate_url(self.image_url, "image URL")
        object.__setattr__(self, "title", self.title.strip())
        object.__setattr__(self, "description", self.description.strip())
        object.__setattr__(self, "link_url", _optional_stripped(self.link_url))
        object.__setattr__(self, "image_url", _optional_stripped(self.image_url))


@dataclass(frozen=True, slots=True)
class CreateInfoAnnouncement:
    values: InfoAnnouncementValues


@dataclass(frozen=True, slots=True)
class UpdateInfoAnnouncement:
    announcement_id: uuid.UUID
    expected_version: int
    values: InfoAnnouncementValues

    def __post_init__(self) -> None:
        if self.expected_version < 1:
            raise ContentValidationError("expected version must be positive")


class ContentEditorialService:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def list_manual(self, *, principal: Principal) -> list[ManualEventRecord]:
        principal.require(Capability.EDIT_CONTENT)
        async with self._unit_of_work.transaction() as repositories:
            return await repositories.manual_events.list_for_guild(principal.guild_id)

    async def create_manual(
        self,
        command: CreateManualEvent,
        *,
        principal: Principal,
        correlation_id: str,
        now: datetime | None = None,
    ) -> ManualEventRecord:
        timestamp = _aware_now(now)
        record = ManualEventRecord(
            id=uuid.uuid4(),
            guild_id=principal.guild_id,
            created_by_user_id=principal.user_id,
            updated_by_user_id=principal.user_id,
            **asdict(command.values),
        )
        denied = False
        async with self._unit_of_work.transaction() as repositories:
            try:
                principal.require(Capability.EDIT_CONTENT)
            except AuthorizationDenied:
                denied = True
                await repositories.audit_logs.add(
                    _audit(
                        principal,
                        "manual_event.create_denied",
                        "manual_event",
                        record.id,
                        None,
                        None,
                        AuditResult.FAILED,
                        correlation_id,
                        timestamp,
                    )
                )
            else:
                await repositories.manual_events.add(record)
                await repositories.audit_logs.add(
                    _audit(
                        principal,
                        "manual_event.created",
                        "manual_event",
                        record.id,
                        None,
                        record,
                        AuditResult.SUCCEEDED,
                        correlation_id,
                        timestamp,
                    )
                )
        if denied:
            raise AuthorizationDenied("manual-event creation is not allowed")
        return record

    async def update_manual(
        self,
        command: UpdateManualEvent,
        *,
        principal: Principal,
        correlation_id: str,
        now: datetime | None = None,
    ) -> ManualEventRecord:
        timestamp = _aware_now(now)
        denied = False
        result: ManualEventRecord | None = None
        async with self._unit_of_work.transaction() as repositories:
            current = await repositories.manual_events.get(command.event_id)
            if current is None or current.guild_id != principal.guild_id:
                raise ContentObjectNotFound("manual event was not found")
            try:
                principal.require(Capability.EDIT_CONTENT)
            except AuthorizationDenied:
                denied = True
                await repositories.audit_logs.add(
                    _audit(
                        principal,
                        "manual_event.update_denied",
                        "manual_event",
                        current.id,
                        current,
                        None,
                        AuditResult.FAILED,
                        correlation_id,
                        timestamp,
                    )
                )
            else:
                if current.version != command.expected_version:
                    raise ContentConflict(current)
                candidate = replace(
                    current,
                    updated_by_user_id=principal.user_id,
                    **asdict(command.values),
                )
                result = await _update_manual_record(
                    repositories.manual_events,
                    candidate,
                    command.expected_version,
                )
                await repositories.audit_logs.add(
                    _audit(
                        principal,
                        "manual_event.updated",
                        "manual_event",
                        current.id,
                        current,
                        result,
                        AuditResult.SUCCEEDED,
                        correlation_id,
                        timestamp,
                    )
                )
        if denied:
            raise AuthorizationDenied("manual-event update is not allowed")
        if result is None:
            raise RuntimeError("manual-event update produced no result")
        return result

    async def delete_manual(
        self,
        event_id: uuid.UUID,
        expected_version: int,
        *,
        principal: Principal,
        correlation_id: str,
        now: datetime | None = None,
    ) -> ManualEventRecord:
        if expected_version < 1:
            raise ContentValidationError("expected version must be positive")
        return await self._soft_delete(
            object_id=event_id,
            expected_version=expected_version,
            principal=principal,
            correlation_id=correlation_id,
            now=_aware_now(now),
            kind="manual_event",
        )

    async def list_info(self, *, principal: Principal) -> list[InfoAnnouncementRecord]:
        principal.require(Capability.EDIT_CONTENT)
        async with self._unit_of_work.transaction() as repositories:
            return await repositories.info_announcements.list_for_guild(principal.guild_id)

    async def create_info(
        self,
        command: CreateInfoAnnouncement,
        *,
        principal: Principal,
        correlation_id: str,
        now: datetime | None = None,
    ) -> InfoAnnouncementRecord:
        timestamp = _aware_now(now)
        record = InfoAnnouncementRecord(
            id=uuid.uuid4(),
            guild_id=principal.guild_id,
            created_by_user_id=principal.user_id,
            updated_by_user_id=principal.user_id,
            **asdict(command.values),
        )
        denied = False
        async with self._unit_of_work.transaction() as repositories:
            try:
                principal.require(Capability.EDIT_CONTENT)
            except AuthorizationDenied:
                denied = True
                await repositories.audit_logs.add(
                    _audit(
                        principal,
                        "info_announcement.create_denied",
                        "info_announcement",
                        record.id,
                        None,
                        None,
                        AuditResult.FAILED,
                        correlation_id,
                        timestamp,
                    )
                )
            else:
                await repositories.info_announcements.add(record)
                await repositories.audit_logs.add(
                    _audit(
                        principal,
                        "info_announcement.created",
                        "info_announcement",
                        record.id,
                        None,
                        record,
                        AuditResult.SUCCEEDED,
                        correlation_id,
                        timestamp,
                    )
                )
        if denied:
            raise AuthorizationDenied("INFO-announcement creation is not allowed")
        return record

    async def update_info(
        self,
        command: UpdateInfoAnnouncement,
        *,
        principal: Principal,
        correlation_id: str,
        now: datetime | None = None,
    ) -> InfoAnnouncementRecord:
        timestamp = _aware_now(now)
        denied = False
        result: InfoAnnouncementRecord | None = None
        async with self._unit_of_work.transaction() as repositories:
            current = await repositories.info_announcements.get(command.announcement_id)
            if current is None or current.guild_id != principal.guild_id:
                raise ContentObjectNotFound("INFO announcement was not found")
            try:
                principal.require(Capability.EDIT_CONTENT)
            except AuthorizationDenied:
                denied = True
                await repositories.audit_logs.add(
                    _audit(
                        principal,
                        "info_announcement.update_denied",
                        "info_announcement",
                        current.id,
                        current,
                        None,
                        AuditResult.FAILED,
                        correlation_id,
                        timestamp,
                    )
                )
            else:
                if current.version != command.expected_version:
                    raise ContentConflict(current)
                candidate = replace(
                    current,
                    updated_by_user_id=principal.user_id,
                    **asdict(command.values),
                )
                result = await _update_info_record(
                    repositories.info_announcements,
                    candidate,
                    command.expected_version,
                )
                await repositories.audit_logs.add(
                    _audit(
                        principal,
                        "info_announcement.updated",
                        "info_announcement",
                        current.id,
                        current,
                        result,
                        AuditResult.SUCCEEDED,
                        correlation_id,
                        timestamp,
                    )
                )
        if denied:
            raise AuthorizationDenied("INFO-announcement update is not allowed")
        if result is None:
            raise RuntimeError("INFO-announcement update produced no result")
        return result

    async def delete_info(
        self,
        announcement_id: uuid.UUID,
        expected_version: int,
        *,
        principal: Principal,
        correlation_id: str,
        now: datetime | None = None,
    ) -> InfoAnnouncementRecord:
        if expected_version < 1:
            raise ContentValidationError("expected version must be positive")
        return await self._soft_delete(
            object_id=announcement_id,
            expected_version=expected_version,
            principal=principal,
            correlation_id=correlation_id,
            now=_aware_now(now),
            kind="info_announcement",
        )

    @overload
    async def _soft_delete(
        self,
        *,
        object_id: uuid.UUID,
        expected_version: int,
        principal: Principal,
        correlation_id: str,
        now: datetime,
        kind: Literal["manual_event"],
    ) -> ManualEventRecord: ...

    @overload
    async def _soft_delete(
        self,
        *,
        object_id: uuid.UUID,
        expected_version: int,
        principal: Principal,
        correlation_id: str,
        now: datetime,
        kind: Literal["info_announcement"],
    ) -> InfoAnnouncementRecord: ...

    async def _soft_delete(
        self,
        *,
        object_id: uuid.UUID,
        expected_version: int,
        principal: Principal,
        correlation_id: str,
        now: datetime,
        kind: Literal["manual_event", "info_announcement"],
    ) -> EditableRecord:
        denied = False
        result: EditableRecord | None = None
        async with self._unit_of_work.transaction() as repositories:
            current: EditableRecord | None
            if kind == "manual_event":
                current = await repositories.manual_events.get(object_id)
            else:
                current = await repositories.info_announcements.get(object_id)
            if current is None or current.guild_id != principal.guild_id:
                raise ContentObjectNotFound(f"{kind.replace('_', ' ')} was not found")
            try:
                principal.require(Capability.EDIT_CONTENT)
            except AuthorizationDenied:
                denied = True
                await repositories.audit_logs.add(
                    _audit(
                        principal,
                        f"{kind}.delete_denied",
                        kind,
                        object_id,
                        current,
                        None,
                        AuditResult.FAILED,
                        correlation_id,
                        now,
                    )
                )
            else:
                if current.version != expected_version:
                    raise ContentConflict(current)
                candidate = replace(
                    current,
                    active=False,
                    deleted_at=now,
                    updated_by_user_id=principal.user_id,
                )
                try:
                    if isinstance(candidate, ManualEventRecord):
                        version = await repositories.manual_events.update(
                            candidate, expected_version=expected_version
                        )
                    else:
                        version = await repositories.info_announcements.update(
                            candidate, expected_version=expected_version
                        )
                except OptimisticLockError as exc:
                    latest = (
                        await repositories.manual_events.get(object_id)
                        if kind == "manual_event"
                        else await repositories.info_announcements.get(object_id)
                    )
                    raise ContentConflict(latest) from exc
                result = replace(candidate, version=version)
                await repositories.audit_logs.add(
                    _audit(
                        principal,
                        f"{kind}.deleted",
                        kind,
                        object_id,
                        current,
                        result,
                        AuditResult.SUCCEEDED,
                        correlation_id,
                        now,
                    )
                )
        if denied:
            raise AuthorizationDenied(f"{kind} deletion is not allowed")
        if result is None:
            raise RuntimeError(f"{kind} deletion produced no result")
        return result


async def _update_manual_record(
    repository: ManualEventRepository,
    candidate: ManualEventRecord,
    expected_version: int,
) -> ManualEventRecord:
    try:
        version = await repository.update(candidate, expected_version=expected_version)
    except OptimisticLockError as exc:
        latest = await repository.get(candidate.id)
        raise ContentConflict(latest) from exc
    return replace(candidate, version=version)


async def _update_info_record(
    repository: InfoAnnouncementRepository,
    candidate: InfoAnnouncementRecord,
    expected_version: int,
) -> InfoAnnouncementRecord:
    try:
        version = await repository.update(candidate, expected_version=expected_version)
    except OptimisticLockError as exc:
        latest = await repository.get(candidate.id)
        raise ContentConflict(latest) from exc
    return replace(candidate, version=version)


def _validate_title(value: str) -> None:
    title = value.strip()
    if not title:
        raise ContentValidationError("title cannot be blank")
    if len(title) > 256:
        raise ContentValidationError("title exceeds Discord limit")


def _validate_optional_text(value: str | None, label: str, limit: int) -> None:
    if value is not None and len(value.strip()) > limit:
        raise ContentValidationError(f"{label} exceeds Discord limit")


def _validate_url(value: str | None, label: str) -> None:
    if value is not None and not valid_public_url(value.strip()):
        raise ContentValidationError(f"{label} must be a public HTTP or HTTPS URL")


def _optional_stripped(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


def _require_aware(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ContentValidationError(f"{label} must include a timezone")


def _aware_now(value: datetime | None) -> datetime:
    timestamp = value or datetime.now(UTC)
    _require_aware(timestamp, "audit time")
    return timestamp


def _audit(
    principal: Principal,
    action: str,
    object_type: str,
    object_id: uuid.UUID,
    before: EditableRecord | None,
    after: EditableRecord | None,
    result: AuditResult,
    correlation_id: str,
    timestamp: datetime,
) -> AuditLogRecord:
    return AuditLogRecord(
        id=uuid.uuid4(),
        guild_id=principal.guild_id,
        actor_user_id=principal.user_id,
        action=action,
        object_type=object_type,
        object_id=str(object_id),
        before_value=_record_json(before),
        after_value=_record_json(after),
        result=result,
        correlation_id=correlation_id,
        created_at=timestamp,
    )


def _record_json(record: EditableRecord | None) -> dict[str, object] | None:
    if record is None:
        return None
    values = asdict(record)
    values.pop("guild_id", None)
    values.pop("created_by_user_id", None)
    values.pop("updated_by_user_id", None)
    return {
        key: (
            value.isoformat()
            if isinstance(value, (date, datetime))
            else str(value)
            if isinstance(value, uuid.UUID)
            else value
        )
        for key, value in values.items()
    }
