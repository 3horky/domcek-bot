"""Admin-owned configuration and calendar source use cases."""

from __future__ import annotations

import unicodedata
import uuid
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, time
from enum import Enum
from typing import Any, Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from domcek_bot.application.audit import AuditWriter
from domcek_bot.application.auth.authorization import Capability, Principal
from domcek_bot.application.calendar.sync import CalendarSyncResult
from domcek_bot.application.records import (
    CalendarSourceRecord,
    GuildConfigRecord,
    ReactionConfigRecord,
)
from domcek_bot.application.unit_of_work import UnitOfWork
from domcek_bot.domain.enums import SyncStatus


class SettingsValidationError(ValueError):
    pass


class CalendarSynchronizer(Protocol):
    async def synchronize(
        self, source_id: uuid.UUID, *, force_full: bool = False
    ) -> CalendarSyncResult: ...


class ReactionTargetValidator(Protocol):
    async def validate_reaction_targets(
        self,
        guild_id: int,
        *,
        emoji_ids: tuple[int, ...],
        channel_ids: tuple[int, ...],
    ) -> None: ...


class DiscordSettingsTargetValidator(Protocol):
    async def validate_settings_targets(
        self,
        guild_id: int,
        *,
        channel_ids: tuple[int, ...],
        category_ids: tuple[int, ...],
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class SettingsSnapshot:
    guild: GuildConfigRecord
    calendars: tuple[CalendarSourceRecord, ...]
    reactions: ReactionConfigRecord


class SettingsService:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        synchronizer: CalendarSynchronizer | None = None,
        reaction_validator: ReactionTargetValidator | None = None,
        discord_settings_validator: DiscordSettingsTargetValidator | None = None,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._synchronizer = synchronizer
        self._reaction_validator = reaction_validator
        self._discord_settings_validator = discord_settings_validator

    async def get(self, principal: Principal) -> SettingsSnapshot:
        principal.require(Capability.MANAGE_SETTINGS)
        async with self._unit_of_work.transaction() as repositories:
            guild = await repositories.guild_configs.get(principal.guild_id)
            if guild is None:
                raise LookupError("guild configuration not found")
            calendars = await repositories.calendar_sources.list_for_guild(principal.guild_id)
            reactions = await repositories.reaction_configs.get(principal.guild_id)
        return SettingsSnapshot(
            guild=guild,
            calendars=tuple(calendars),
            reactions=reactions or ReactionConfigRecord(guild_id=principal.guild_id),
        )

    async def update_publication(
        self,
        *,
        expected_version: int,
        timezone: str,
        publication_weekday: int,
        publication_time: time,
        automatic_publication_enabled: bool,
        publish_google_descriptions: bool,
        generated_intro_enabled: bool,
        everyone_mention_enabled: bool,
        announcement_channel_id: int | None,
        command_channel_id: int | None,
        moderator_channel_id: int | None,
        projects_category_id: int | None,
        archive_category_id: int | None,
        closing_message: str | None,
        principal: Principal,
        correlation_id: str,
        alert_calendar_sync_enabled: bool | None = None,
        alert_publication_enabled: bool | None = None,
        alert_channel_operations_enabled: bool | None = None,
        alert_role_operations_enabled: bool | None = None,
        alert_publication_reminder_enabled: bool | None = None,
        allow_stale_calendar_cache: bool = False,
    ) -> GuildConfigRecord:
        principal.require(Capability.MANAGE_SETTINGS)
        normalized_timezone = _timezone(timezone)
        if not 0 <= publication_weekday <= 6:
            raise SettingsValidationError("publication weekday must be between 0 and 6")
        if not everyone_mention_enabled:
            raise SettingsValidationError("every successful publication must mention @everyone")
        ids = (
            announcement_channel_id,
            command_channel_id,
            moderator_channel_id,
            projects_category_id,
            archive_category_id,
        )
        if any(value is not None and value <= 0 for value in ids):
            raise SettingsValidationError("Discord identifiers must be positive")
        channel_ids = tuple(
            value
            for value in (announcement_channel_id, command_channel_id, moderator_channel_id)
            if value is not None
        )
        category_ids = tuple(
            value for value in (projects_category_id, archive_category_id) if value is not None
        )
        if channel_ids or category_ids:
            if self._discord_settings_validator is None:
                raise SettingsValidationError("Discord target validation is unavailable")
            try:
                await self._discord_settings_validator.validate_settings_targets(
                    principal.guild_id,
                    channel_ids=channel_ids,
                    category_ids=category_ids,
                )
            except Exception as exc:
                raise SettingsValidationError(
                    "selected Discord channel or category is unavailable"
                ) from exc
        normalized_closing = _optional_text(closing_message, 2000)
        async with self._unit_of_work.transaction() as repositories:
            current = await repositories.guild_configs.get(principal.guild_id)
            if current is None:
                raise LookupError("guild configuration not found")
            updated = replace(
                current,
                timezone=normalized_timezone,
                publication_weekday=publication_weekday,
                publication_time=publication_time.replace(tzinfo=None),
                automatic_publication_enabled=automatic_publication_enabled,
                publish_google_descriptions=publish_google_descriptions,
                generated_intro_enabled=generated_intro_enabled,
                everyone_mention_enabled=True,
                allow_stale_calendar_cache=allow_stale_calendar_cache,
                alert_calendar_sync_enabled=current.alert_calendar_sync_enabled
                if alert_calendar_sync_enabled is None
                else alert_calendar_sync_enabled,
                alert_publication_enabled=current.alert_publication_enabled
                if alert_publication_enabled is None
                else alert_publication_enabled,
                alert_channel_operations_enabled=current.alert_channel_operations_enabled
                if alert_channel_operations_enabled is None
                else alert_channel_operations_enabled,
                alert_role_operations_enabled=current.alert_role_operations_enabled
                if alert_role_operations_enabled is None
                else alert_role_operations_enabled,
                alert_publication_reminder_enabled=current.alert_publication_reminder_enabled
                if alert_publication_reminder_enabled is None
                else alert_publication_reminder_enabled,
                announcement_channel_id=announcement_channel_id,
                command_channel_id=command_channel_id,
                moderator_channel_id=moderator_channel_id,
                projects_category_id=projects_category_id,
                archive_category_id=archive_category_id,
                closing_message=normalized_closing,
            )
            version = await repositories.guild_configs.update(
                updated, expected_version=expected_version
            )
            await AuditWriter(repositories.audit_logs).success(
                guild_id=principal.guild_id,
                actor_user_id=principal.user_id,
                action="settings.publication.updated",
                object_type="guild_config",
                object_id=str(principal.guild_id),
                correlation_id=correlation_id,
                before_value=_safe_record(current),
                after_value=_safe_record(replace(updated, version=version)),
            )
        return replace(updated, version=version)

    async def add_calendar(
        self,
        *,
        external_calendar_id: str,
        display_name: str,
        priority: int,
        active: bool,
        principal: Principal,
        correlation_id: str,
    ) -> CalendarSourceRecord:
        principal.require(Capability.MANAGE_SETTINGS)
        record = CalendarSourceRecord(
            id=uuid.uuid4(),
            guild_id=principal.guild_id,
            provider="google",
            external_calendar_id=_required_text(external_calendar_id, 512, "calendar ID"),
            display_name=_required_text(display_name, 200, "calendar name"),
            priority=_priority(priority),
            active=active,
        )
        async with self._unit_of_work.transaction() as repositories:
            await repositories.calendar_sources.add(record)
            await AuditWriter(repositories.audit_logs).success(
                guild_id=principal.guild_id,
                actor_user_id=principal.user_id,
                action="calendar_source.created",
                object_type="calendar_source",
                object_id=str(record.id),
                correlation_id=correlation_id,
                after_value=_safe_record(record),
            )
        return record

    async def update_calendar(
        self,
        source_id: uuid.UUID,
        *,
        expected_version: int,
        external_calendar_id: str,
        display_name: str,
        priority: int,
        active: bool,
        principal: Principal,
        correlation_id: str,
    ) -> CalendarSourceRecord:
        principal.require(Capability.MANAGE_SETTINGS)
        async with self._unit_of_work.transaction() as repositories:
            current = await repositories.calendar_sources.get(source_id)
            if current is None or current.guild_id != principal.guild_id:
                raise LookupError("calendar source not found")
            new_external_id = _required_text(external_calendar_id, 512, "calendar ID")
            identity_changed = new_external_id != current.external_calendar_id
            updated = replace(
                current,
                external_calendar_id=new_external_id,
                display_name=_required_text(display_name, 200, "calendar name"),
                priority=_priority(priority),
                active=active,
                sync_status=SyncStatus.NEVER if identity_changed else current.sync_status,
                sync_token=None if identity_changed else current.sync_token,
                sync_token_query_key=None if identity_changed else current.sync_token_query_key,
                last_sync_error=None if identity_changed else current.last_sync_error,
            )
            version = await repositories.calendar_sources.update(
                updated, expected_version=expected_version
            )
            await AuditWriter(repositories.audit_logs).success(
                guild_id=principal.guild_id,
                actor_user_id=principal.user_id,
                action="calendar_source.updated",
                object_type="calendar_source",
                object_id=str(source_id),
                correlation_id=correlation_id,
                before_value=_safe_record(current),
                after_value=_safe_record(replace(updated, version=version)),
            )
        return replace(updated, version=version)

    async def update_reactions(
        self,
        record: ReactionConfigRecord,
        *,
        expected_version: int,
        principal: Principal,
        correlation_id: str,
    ) -> ReactionConfigRecord:
        principal.require(Capability.MANAGE_SETTINGS)
        if record.guild_id != principal.guild_id:
            raise SettingsValidationError("reaction configuration belongs to another guild")
        validated = validate_reaction_config(record)
        if self._reaction_validator is not None:
            validation_channels = set(
                validated.auto_reaction_channel_ids if validated.auto_reaction_enabled else ()
            )
            if validated.seen_enabled:
                async with self._unit_of_work.transaction() as repositories:
                    guild = await repositories.guild_configs.get(principal.guild_id)
                if guild is not None and guild.announcement_channel_id is not None:
                    validation_channels.add(guild.announcement_channel_id)
            emoji_ids = tuple(
                value
                for enabled, value in (
                    (validated.seen_enabled, validated.seen_emoji_id),
                    (validated.auto_reaction_enabled, validated.auto_reaction_emoji_id),
                    (validated.mention_reaction_enabled, validated.mention_reaction_emoji_id),
                )
                if enabled and value is not None
            )
            await self._reaction_validator.validate_reaction_targets(
                principal.guild_id,
                emoji_ids=emoji_ids,
                channel_ids=tuple(sorted(validation_channels)),
            )
        async with self._unit_of_work.transaction() as repositories:
            current = await repositories.reaction_configs.get(principal.guild_id)
            if current is None:
                if expected_version not in {0, 1}:
                    raise SettingsValidationError("reaction configuration version is invalid")
                await repositories.reaction_configs.add(validated)
                version = 1
            else:
                version = await repositories.reaction_configs.update(
                    validated, expected_version=expected_version
                )
            result = replace(validated, version=version)
            await AuditWriter(repositories.audit_logs).success(
                guild_id=principal.guild_id,
                actor_user_id=principal.user_id,
                action="settings.reactions.updated",
                object_type="reaction_config",
                object_id=str(principal.guild_id),
                correlation_id=correlation_id,
                before_value=None if current is None else _safe_record(current),
                after_value=_safe_record(result),
            )
        return result

    async def sync_calendar(
        self,
        source_id: uuid.UUID,
        *,
        force_full: bool,
        principal: Principal,
        correlation_id: str,
    ) -> CalendarSyncResult:
        principal.require(Capability.MANAGE_SETTINGS)
        if self._synchronizer is None:
            raise RuntimeError("calendar synchronizer is unavailable")
        async with self._unit_of_work.transaction() as repositories:
            source = await repositories.calendar_sources.get(source_id)
        if source is None or source.guild_id != principal.guild_id:
            raise LookupError("calendar source not found")
        result = await self._synchronizer.synchronize(source_id, force_full=force_full)
        async with self._unit_of_work.transaction() as repositories:
            await AuditWriter(repositories.audit_logs).success(
                guild_id=principal.guild_id,
                actor_user_id=principal.user_id,
                action="calendar_source.synced",
                object_type="calendar_source",
                object_id=str(source_id),
                correlation_id=correlation_id,
                after_value={"mode": result.mode.value, "received": result.received},
            )
        return result


def validate_reaction_config(record: ReactionConfigRecord) -> ReactionConfigRecord:
    channels = tuple(sorted(set(record.auto_reaction_channel_ids)))
    if any(channel_id <= 0 for channel_id in channels):
        raise SettingsValidationError("reaction channels must be positive Discord IDs")
    for enabled, emoji_id, unicode_value, label in (
        (record.seen_enabled, record.seen_emoji_id, record.seen_emoji_unicode, "seen"),
        (
            record.auto_reaction_enabled,
            record.auto_reaction_emoji_id,
            record.auto_reaction_emoji_unicode,
            "automatic",
        ),
        (
            record.mention_reaction_enabled,
            record.mention_reaction_emoji_id,
            record.mention_reaction_emoji_unicode,
            "mention",
        ),
    ):
        if emoji_id is not None and emoji_id <= 0:
            raise SettingsValidationError(f"{label} emoji ID must be positive")
        value = _optional_text(unicode_value, 32)
        if value is not None and not _is_unicode_emoji(value):
            raise SettingsValidationError(f"{label} Unicode value is not an emoji")
        if emoji_id is not None and value is not None:
            raise SettingsValidationError(f"{label} reaction cannot use two emoji values")
        if enabled and emoji_id is None and value is None:
            raise SettingsValidationError(f"enabled {label} reaction must select an emoji")
    if record.auto_reaction_enabled and not channels:
        raise SettingsValidationError("automatic reactions require at least one channel")
    return replace(
        record,
        seen_emoji_unicode=_optional_text(record.seen_emoji_unicode, 32),
        auto_reaction_emoji_unicode=_optional_text(record.auto_reaction_emoji_unicode, 32),
        mention_reaction_emoji_unicode=_optional_text(record.mention_reaction_emoji_unicode, 32),
        auto_reaction_channel_ids=channels,
    )


def _timezone(value: str) -> str:
    normalized = value.strip()
    try:
        ZoneInfo(normalized)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise SettingsValidationError("timezone is invalid") from exc
    return normalized


def _is_unicode_emoji(value: str) -> bool:
    if any(character in "\r\n" for character in value):
        return False
    categories = {unicodedata.category(character) for character in value}
    has_symbol = bool(categories & {"So", "Sk"})
    has_keycap = "\u20e3" in value
    return has_symbol or has_keycap


def _priority(value: int) -> int:
    if not 0 <= value <= 10_000:
        raise SettingsValidationError("calendar priority must be between 0 and 10000")
    return value


def _required_text(value: str, maximum: int, label: str) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise SettingsValidationError(f"{label} is invalid")
    return normalized


def _optional_text(value: str | None, maximum: int) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > maximum:
        raise SettingsValidationError("text is too long")
    return normalized


def _safe_record(record: Any) -> dict[str, object]:
    values = asdict(record)
    return {
        key: _json_safe(value)
        for key, value in values.items()
        if key not in {"sync_token", "sync_token_query_key"}
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_json_safe(item) for item in value]
    return value
