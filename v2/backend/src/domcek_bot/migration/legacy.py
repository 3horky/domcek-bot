"""Read-only legacy SQLite inventory and idempotent PostgreSQL importer."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
import uuid
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import create_async_engine

from domcek_bot.application.publication.formatting import valid_public_url
from domcek_bot.application.records import ReactionConfigRecord
from domcek_bot.application.settings import SettingsValidationError, validate_reaction_config
from domcek_bot.infrastructure.models import (
    AuditLogModel,
    CalendarSourceModel,
    EventOverrideModel,
    ExternalEventModel,
    GuildConfigModel,
    InfoAnnouncementModel,
    ManualEventModel,
    ReactionConfigChannelModel,
    ReactionConfigModel,
)

MIGRATION_NAMESPACE = uuid.UUID("4311800d-f2a1-53dd-80b8-d3a4f7aeb234")
CUSTOM_EMOJI = re.compile(r"^<a?:[A-Za-z0-9_]+:(\d+)>$")
EVENT_DATETIME = re.compile(
    r"^\s*(?P<day>\d{1,2})\.(?P<month>\d{1,2})\.?(?:\s*//\s*(?P<hour>\d{1,2}):(?P<minute>\d{2}))?\s*$"
)
WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


class LegacyMigrationError(RuntimeError):
    """A safe, user-correctable migration problem."""


@dataclass(frozen=True, slots=True)
class LegacyAnnouncement:
    id: int
    kind: str
    title: str
    description: str
    event_datetime: str | None
    day: str | None
    link_url: str | None
    image_url: str | None
    visible_from: str | None
    visible_to: str | None
    created_at: str


@dataclass(frozen=True, slots=True)
class MigrationItem:
    legacy_id: int
    migration_key: str
    target_id: str
    kind: str
    action: str
    active: bool
    title: str
    starts_at: str | None = None
    ends_at: str | None = None
    starts_on: str | None = None
    ends_on: str | None = None
    valid_from: str | None = None
    valid_until: str | None = None
    match_candidates: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MigrationReport:
    format_version: int
    source_sha256: str
    as_of: str
    inventory: dict[str, int]
    settings: dict[str, Any]
    issues: tuple[dict[str, Any], ...]
    items: tuple[MigrationItem, ...]
    result: dict[str, int] | None = None

    def json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def stable_id(kind: str, legacy_id: int | str) -> uuid.UUID:
    return uuid.uuid5(MIGRATION_NAMESPACE, f"carlo-legacy:{kind}:{legacy_id}")


def read_legacy(source: Path) -> tuple[list[LegacyAnnouncement], dict[str, Any], str]:
    resolved = source.resolve(strict=True)
    digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
    uri = f"{resolved.as_uri()}?mode=ro&immutable=1"
    try:
        connection = sqlite3.connect(uri, uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        if not {"announcements", "bot_settings"}.issubset(tables):
            raise LegacyMigrationError("Zdroj nemá očakávané legacy tabuľky.")
        rows = connection.execute(
            "SELECT id, typ, title, description, datetime, day, link, image, "
            "visible_from, visible_to, created_at FROM announcements ORDER BY id"
        ).fetchall()
        raw_settings = connection.execute(
            "SELECT key, value FROM bot_settings ORDER BY key"
        ).fetchall()
    except sqlite3.Error as exc:
        raise LegacyMigrationError("Legacy SQLite sa nepodarilo bezpečne prečítať.") from exc
    finally:
        if "connection" in locals():
            connection.close()
    announcements = [
        LegacyAnnouncement(
            id=int(row["id"]),
            kind=str(row["typ"]),
            title=str(row["title"]),
            description=str(row["description"]),
            event_datetime=row["datetime"],
            day=row["day"],
            link_url=_optional(row["link"]),
            image_url=_optional(row["image"]),
            visible_from=row["visible_from"],
            visible_to=row["visible_to"],
            created_at=str(row["created_at"]),
        )
        for row in rows
    ]
    settings: dict[str, Any] = {}
    for row in raw_settings:
        value = row["value"]
        try:
            settings[str(row["key"])] = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            settings[str(row["key"])] = value
    return announcements, settings, digest


def build_report(source: Path, *, as_of: date) -> MigrationReport:
    announcements, settings, digest = read_legacy(source)
    issues: list[dict[str, Any]] = []
    items: list[MigrationItem] = []
    inventory = {
        "announcements_total": len(announcements),
        "info_total": 0,
        "event_total": 0,
        "active_as_of": 0,
        "future_as_of": 0,
        "expired_as_of": 0,
        "invalid": 0,
        "duplicates": 0,
    }
    duplicate_keys: dict[tuple[str, str, str | None, str | None], list[int]] = {}
    for announcement in announcements:
        duplicate_key = (
            announcement.kind.casefold(),
            _normalized_title(announcement.title),
            announcement.event_datetime,
            announcement.visible_to,
        )
        duplicate_keys.setdefault(duplicate_key, []).append(announcement.id)
        try:
            item = _plan_item(announcement, as_of=as_of)
        except LegacyMigrationError as exc:
            inventory["invalid"] += 1
            issues.append(
                {"legacy_id": announcement.id, "code": "invalid_record", "detail": str(exc)}
            )
            continue
        inventory[f"{announcement.kind.casefold()}_total"] = (
            inventory.get(f"{announcement.kind.casefold()}_total", 0) + 1
        )
        state = _date_state(announcement, as_of)
        inventory[f"{state}_as_of"] += 1
        items.append(item)
        for field, value in (("link", announcement.link_url), ("image", announcement.image_url)):
            if value and not _public_http_url(value):
                issues.append(
                    {"legacy_id": announcement.id, "code": f"invalid_{field}_url", "detail": value}
                )
    for ids in duplicate_keys.values():
        if len(ids) > 1:
            inventory["duplicates"] += len(ids) - 1
            issues.append({"legacy_ids": ids, "code": "possible_duplicate"})
    return MigrationReport(
        format_version=1,
        source_sha256=digest,
        as_of=as_of.isoformat(),
        inventory=inventory,
        settings=_mapped_settings(settings),
        issues=tuple(issues),
        items=tuple(items),
    )


async def enrich_google_matches(
    report: MigrationReport, *, target_url: str, guild_id: int
) -> MigrationReport:
    engine = create_async_engine(target_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            rows = (
                await connection.execute(
                    select(
                        ExternalEventModel.id,
                        ExternalEventModel.source_title,
                        ExternalEventModel.starts_at,
                        ExternalEventModel.starts_on,
                    )
                    .join(
                        CalendarSourceModel,
                        CalendarSourceModel.id == ExternalEventModel.calendar_source_id,
                    )
                    .where(CalendarSourceModel.guild_id == guild_id)
                )
            ).all()
    finally:
        await engine.dispose()
    candidates: dict[tuple[str, str, str], list[str]] = {}
    timezone = ZoneInfo("Europe/Bratislava")
    for event_id, title, starts_at, starts_on in rows:
        if starts_at is not None:
            local_key = starts_at.astimezone(timezone).replace(second=0, microsecond=0).isoformat()
            key = (_normalized_title(title or ""), "timed", local_key)
        elif starts_on is not None:
            key = (_normalized_title(title or ""), "all_day", starts_on.isoformat())
        else:
            continue
        candidates.setdefault(key, []).append(str(event_id))
    enriched: list[MigrationItem] = []
    for item in report.items:
        if item.kind != "event" or not item.active:
            enriched.append(item)
            continue
        if item.starts_at is not None:
            match_key = (_normalized_title(item.title), "timed", item.starts_at)
        elif item.starts_on is not None:
            match_key = (_normalized_title(item.title), "all_day", item.starts_on)
        else:
            enriched.append(item)
            continue
        matches = tuple(candidates.get(match_key, ()))
        if matches:
            enriched.append(replace(item, action="review_google_match", match_candidates=matches))
        else:
            enriched.append(item)
    return replace(report, items=tuple(enriched))


async def import_report(
    report: MigrationReport,
    announcements: list[LegacyAnnouncement],
    *,
    target_url: str,
    guild_id: int,
    actor_user_id: int,
    approve_unmatched: bool,
    approved_matches: dict[int, str],
    apply_settings: bool,
) -> MigrationReport:
    engine = create_async_engine(target_url, pool_pre_ping=True)
    by_id = {item.id: item for item in announcements}
    result = {
        "inserted_info": 0,
        "inserted_manual": 0,
        "inserted_overrides": 0,
        "skipped_existing": 0,
        "needs_review": 0,
        "settings_changed": 0,
    }
    try:
        async with engine.begin() as connection:
            guild_exists = await connection.scalar(
                select(GuildConfigModel.guild_id).where(GuildConfigModel.guild_id == guild_id)
            )
            if guild_exists is None:
                raise LegacyMigrationError(
                    "Cieľ neobsahuje konfiguráciu zvoleného Discord servera."
                )
            for item in report.items:
                source = by_id[item.legacy_id]
                if item.action == "review_google_match":
                    approved = approved_matches.get(item.legacy_id)
                    if approved is None or approved not in item.match_candidates:
                        result["needs_review"] += 1
                        continue
                    inserted = await _insert_override(
                        connection,
                        item,
                        source,
                        approved,
                        guild_id=guild_id,
                        actor_user_id=actor_user_id,
                    )
                    result["inserted_overrides" if inserted else "skipped_existing"] += 1
                elif item.kind == "event":
                    if item.active and not approve_unmatched:
                        result["needs_review"] += 1
                        continue
                    inserted = await _insert_manual(
                        connection,
                        item,
                        source,
                        guild_id=guild_id,
                        actor_user_id=actor_user_id,
                    )
                    result["inserted_manual" if inserted else "skipped_existing"] += 1
                elif item.kind == "info":
                    inserted = await _insert_info(
                        connection,
                        item,
                        source,
                        guild_id=guild_id,
                        actor_user_id=actor_user_id,
                    )
                    result["inserted_info" if inserted else "skipped_existing"] += 1
            if apply_settings:
                result["settings_changed"] = await _apply_settings(
                    connection,
                    report.settings,
                    guild_id=guild_id,
                    actor_user_id=actor_user_id,
                    source_sha256=report.source_sha256,
                )
    finally:
        await engine.dispose()
    return replace(report, result=result)


async def _insert_info(
    connection: Any,
    item: MigrationItem,
    source: LegacyAnnouncement,
    *,
    guild_id: int,
    actor_user_id: int,
) -> bool:
    if item.valid_from is None or item.valid_until is None:
        raise LegacyMigrationError("INFO plán nemá platný interval.")
    values = {
        "id": uuid.UUID(item.target_id),
        "guild_id": guild_id,
        "title": source.title.strip(),
        "description": source.description.strip(),
        "link_url": source.link_url if _public_http_url(source.link_url) else None,
        "image_url": source.image_url if _public_http_url(source.image_url) else None,
        "valid_from": date.fromisoformat(item.valid_from),
        "valid_until": date.fromisoformat(item.valid_until),
        "active": item.active,
        "created_by_user_id": actor_user_id,
        "updated_by_user_id": actor_user_id,
        "deleted_at": None if item.active else datetime.now(UTC),
        "version": 1,
    }
    inserted = await connection.execute(
        pg_insert(InfoAnnouncementModel)
        .values(**values)
        .on_conflict_do_nothing(index_elements=["id"])
    )
    if inserted.rowcount:
        await _audit(connection, item, guild_id, actor_user_id, "legacy_info_imported")
    return bool(inserted.rowcount)


async def _insert_manual(
    connection: Any,
    item: MigrationItem,
    source: LegacyAnnouncement,
    *,
    guild_id: int,
    actor_user_id: int,
) -> bool:
    values: dict[str, Any] = {
        "id": uuid.UUID(item.target_id),
        "guild_id": guild_id,
        "title": source.title.strip(),
        "description": source.description.strip() or None,
        "is_all_day": item.starts_on is not None,
        "starts_at": datetime.fromisoformat(item.starts_at) if item.starts_at else None,
        "ends_at": datetime.fromisoformat(item.ends_at) if item.ends_at else None,
        "starts_on": date.fromisoformat(item.starts_on) if item.starts_on else None,
        "ends_on": date.fromisoformat(item.ends_on) if item.ends_on else None,
        "timezone": "Europe/Bratislava",
        "link_url": source.link_url if _public_http_url(source.link_url) else None,
        "active": item.active,
        "created_by_user_id": actor_user_id,
        "updated_by_user_id": actor_user_id,
        "deleted_at": None if item.active else datetime.now(UTC),
        "version": 1,
    }
    inserted = await connection.execute(
        pg_insert(ManualEventModel).values(**values).on_conflict_do_nothing(index_elements=["id"])
    )
    if inserted.rowcount:
        await _audit(connection, item, guild_id, actor_user_id, "legacy_manual_imported")
    return bool(inserted.rowcount)


async def _insert_override(
    connection: Any,
    item: MigrationItem,
    source: LegacyAnnouncement,
    external_event_id: str,
    *,
    guild_id: int,
    actor_user_id: int,
) -> bool:
    event_id = uuid.UUID(external_event_id)
    event = await connection.execute(
        select(ExternalEventModel.source_title, ExternalEventModel.source_description)
        .join(
            CalendarSourceModel,
            CalendarSourceModel.id == ExternalEventModel.calendar_source_id,
        )
        .where(
            ExternalEventModel.id == event_id,
            CalendarSourceModel.guild_id == guild_id,
        )
    )
    current = event.one_or_none()
    if current is None:
        raise LegacyMigrationError(f"Schválená Google udalosť {event_id} už neexistuje.")
    source_title = (current.source_title or "").strip()
    source_description = (current.source_description or "").strip()
    legacy_title = source.title.strip()
    legacy_description = source.description.strip()
    title_changed = legacy_title != source_title
    description_changed = legacy_description != source_description
    if not title_changed and not description_changed:
        return False
    values = {
        "external_event_id": event_id,
        "public_title": legacy_title if title_changed else None,
        "description_state": "custom" if description_changed else "inherit",
        "public_description": legacy_description if description_changed else None,
        "inclusion_decision": "auto",
        "version": 1,
        "updated_by_user_id": actor_user_id,
    }
    inserted = await connection.execute(
        pg_insert(EventOverrideModel)
        .values(**values)
        .on_conflict_do_nothing(index_elements=["external_event_id"])
    )
    if inserted.rowcount:
        await _audit(
            connection,
            item,
            guild_id,
            actor_user_id,
            "legacy_event_override_imported",
            object_type="event_override",
            object_id=str(event_id),
        )
    return bool(inserted.rowcount)


async def _audit(
    connection: Any,
    item: MigrationItem,
    guild_id: int,
    actor_user_id: int,
    action: str,
    *,
    object_type: str | None = None,
    object_id: str | None = None,
) -> None:
    await connection.execute(
        pg_insert(AuditLogModel)
        .values(
            id=stable_id("audit", item.migration_key),
            guild_id=guild_id,
            actor_user_id=actor_user_id,
            action=action,
            object_type=object_type or item.kind,
            object_id=object_id or item.target_id,
            before_value=None,
            after_value={"legacy_id": item.legacy_id, "migration_key": item.migration_key},
            result="succeeded",
            correlation_id=f"legacy-migration:{item.legacy_id}",
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )


async def _apply_settings(
    connection: Any,
    settings: dict[str, Any],
    *,
    guild_id: int,
    actor_user_id: int,
    source_sha256: str,
) -> int:
    changed = 0
    schedule = settings.get("publication")
    if isinstance(schedule, dict):
        values = {
            "publication_weekday": schedule["weekday"],
            "publication_time": time.fromisoformat(schedule["time"]),
            "automatic_publication_enabled": schedule["active"],
        }
        current = await connection.execute(
            select(
                GuildConfigModel.publication_weekday,
                GuildConfigModel.publication_time,
                GuildConfigModel.automatic_publication_enabled,
            ).where(GuildConfigModel.guild_id == guild_id)
        )
        if tuple(current.one()) != tuple(values.values()):
            await connection.execute(
                update(GuildConfigModel)
                .where(GuildConfigModel.guild_id == guild_id)
                .values(**values, version=GuildConfigModel.version + 1)
            )
            changed += 1
    reaction = settings.get("reaction")
    if isinstance(reaction, dict):
        emoji_id = reaction.get("emoji_id")
        emoji_unicode = reaction.get("emoji_unicode")
        try:
            validated_reaction = validate_reaction_config(
                ReactionConfigRecord(
                    guild_id=guild_id,
                    seen_enabled=True,
                    seen_emoji_id=emoji_id,
                    seen_emoji_unicode=emoji_unicode,
                    auto_reaction_enabled=bool(reaction.get("channel_ids")),
                    auto_reaction_emoji_id=emoji_id,
                    auto_reaction_emoji_unicode=emoji_unicode,
                    mention_reaction_enabled=True,
                    mention_reaction_emoji_id=emoji_id,
                    mention_reaction_emoji_unicode=emoji_unicode,
                    auto_reaction_channel_ids=tuple(
                        int(value) for value in reaction.get("channel_ids", ())
                    ),
                )
            )
        except (SettingsValidationError, TypeError, ValueError) as exc:
            raise LegacyMigrationError("Legacy nastavenie reakcií nie je platné.") from exc
        insert = pg_insert(ReactionConfigModel).values(
            guild_id=guild_id,
            seen_enabled=validated_reaction.seen_enabled,
            seen_emoji_id=validated_reaction.seen_emoji_id,
            seen_emoji_unicode=validated_reaction.seen_emoji_unicode,
            auto_reaction_enabled=validated_reaction.auto_reaction_enabled,
            auto_reaction_emoji_id=validated_reaction.auto_reaction_emoji_id,
            auto_reaction_emoji_unicode=validated_reaction.auto_reaction_emoji_unicode,
            mention_reaction_enabled=validated_reaction.mention_reaction_enabled,
            mention_reaction_emoji_id=validated_reaction.mention_reaction_emoji_id,
            mention_reaction_emoji_unicode=validated_reaction.mention_reaction_emoji_unicode,
            version=1,
        )
        update_values = {
            "seen_enabled": insert.excluded.seen_enabled,
            "seen_emoji_id": insert.excluded.seen_emoji_id,
            "seen_emoji_unicode": insert.excluded.seen_emoji_unicode,
            "auto_reaction_enabled": insert.excluded.auto_reaction_enabled,
            "auto_reaction_emoji_id": insert.excluded.auto_reaction_emoji_id,
            "auto_reaction_emoji_unicode": insert.excluded.auto_reaction_emoji_unicode,
            "mention_reaction_enabled": insert.excluded.mention_reaction_enabled,
            "mention_reaction_emoji_id": insert.excluded.mention_reaction_emoji_id,
            "mention_reaction_emoji_unicode": insert.excluded.mention_reaction_emoji_unicode,
            "version": ReactionConfigModel.version + 1,
        }
        outcome = await connection.execute(
            insert.on_conflict_do_update(
                index_elements=["guild_id"],
                set_=update_values,
                where=(
                    ReactionConfigModel.seen_enabled.is_distinct_from(insert.excluded.seen_enabled)
                    | ReactionConfigModel.seen_emoji_id.is_distinct_from(
                        insert.excluded.seen_emoji_id
                    )
                    | ReactionConfigModel.seen_emoji_unicode.is_distinct_from(
                        insert.excluded.seen_emoji_unicode
                    )
                    | ReactionConfigModel.auto_reaction_enabled.is_distinct_from(
                        insert.excluded.auto_reaction_enabled
                    )
                    | ReactionConfigModel.auto_reaction_emoji_id.is_distinct_from(
                        insert.excluded.auto_reaction_emoji_id
                    )
                    | ReactionConfigModel.auto_reaction_emoji_unicode.is_distinct_from(
                        insert.excluded.auto_reaction_emoji_unicode
                    )
                    | ReactionConfigModel.mention_reaction_emoji_id.is_distinct_from(
                        insert.excluded.mention_reaction_emoji_id
                    )
                    | ReactionConfigModel.mention_reaction_enabled.is_distinct_from(
                        insert.excluded.mention_reaction_enabled
                    )
                    | ReactionConfigModel.mention_reaction_emoji_unicode.is_distinct_from(
                        insert.excluded.mention_reaction_emoji_unicode
                    )
                ),
            )
        )
        changed += int(bool(outcome.rowcount))
        channels = validated_reaction.auto_reaction_channel_ids
        if channels:
            channel_insert = await connection.execute(
                pg_insert(ReactionConfigChannelModel)
                .values([{"guild_id": guild_id, "discord_channel_id": value} for value in channels])
                .on_conflict_do_nothing()
            )
            changed += int(channel_insert.rowcount or 0)
    if changed:
        await connection.execute(
            pg_insert(AuditLogModel)
            .values(
                id=stable_id("audit", f"settings:{source_sha256}:{guild_id}"),
                guild_id=guild_id,
                actor_user_id=actor_user_id,
                action="legacy_settings_imported",
                object_type="guild_config",
                object_id=str(guild_id),
                before_value=None,
                after_value={"source_sha256": source_sha256, "changes": changed},
                result="succeeded",
                correlation_id=f"legacy-migration:settings:{source_sha256[:12]}",
            )
            .on_conflict_do_nothing(index_elements=["id"])
        )
    return changed


def _plan_item(announcement: LegacyAnnouncement, *, as_of: date) -> MigrationItem:
    if not announcement.title.strip():
        raise LegacyMigrationError("Prázdny titulok.")
    kind = announcement.kind.casefold()
    active = _date_state(announcement, as_of) != "expired"
    target_id = stable_id(kind, announcement.id)
    if kind == "info":
        valid_from = _legacy_date(announcement.visible_from, "visible_from")
        valid_until = _legacy_date(announcement.visible_to, "visible_to")
        if valid_until < valid_from:
            raise LegacyMigrationError("INFO má koniec platnosti pred začiatkom.")
        return MigrationItem(
            legacy_id=announcement.id,
            migration_key=f"legacy-announcement:{announcement.id}",
            target_id=str(target_id),
            kind=kind,
            action="import_info" if active else "import_info_inactive",
            active=active,
            title=announcement.title.strip(),
            valid_from=valid_from.isoformat(),
            valid_until=valid_until.isoformat(),
        )
    if kind != "event":
        raise LegacyMigrationError(f"Neznámy typ oznamu: {announcement.kind}")
    local = _legacy_event_datetime(announcement)
    warnings = ("legacy_event_end_inferred_60_minutes",)
    if isinstance(local, datetime):
        return MigrationItem(
            legacy_id=announcement.id,
            migration_key=f"legacy-announcement:{announcement.id}",
            target_id=str(target_id),
            kind=kind,
            action="import_manual" if active else "import_manual_inactive",
            active=active,
            title=announcement.title.strip(),
            starts_at=local.isoformat(),
            ends_at=(local + timedelta(hours=1)).isoformat(),
            warnings=warnings,
        )
    return MigrationItem(
        legacy_id=announcement.id,
        migration_key=f"legacy-announcement:{announcement.id}",
        target_id=str(target_id),
        kind=kind,
        action="import_manual" if active else "import_manual_inactive",
        active=active,
        title=announcement.title.strip(),
        starts_on=local.isoformat(),
        ends_on=(local + timedelta(days=1)).isoformat(),
    )


def _legacy_event_datetime(announcement: LegacyAnnouncement) -> datetime | date:
    value = announcement.event_datetime or ""
    match = EVENT_DATETIME.fullmatch(value)
    if match is None:
        raise LegacyMigrationError(f"Neplatný dátum udalosti: {value!r}")
    reference = _legacy_date(
        announcement.visible_to or announcement.visible_from, "event reference year"
    )
    event_date = date(reference.year, int(match["month"]), int(match["day"]))
    if match["hour"] is None:
        return event_date
    return datetime.combine(
        event_date,
        time(int(match["hour"]), int(match["minute"])),
        tzinfo=ZoneInfo("Europe/Bratislava"),
    )


def _legacy_date(value: str | None, field: str) -> date:
    try:
        return datetime.strptime((value or "").strip(), "%d.%m.%Y").date()
    except ValueError as exc:
        raise LegacyMigrationError(f"Neplatný {field}: {value!r}") from exc


def _date_state(
    announcement: LegacyAnnouncement, as_of: date
) -> Literal["active", "future", "expired"]:
    start = _legacy_date(announcement.visible_from, "visible_from")
    end = _legacy_date(announcement.visible_to, "visible_to")
    if end < as_of:
        return "expired"
    if start > as_of:
        return "future"
    return "active"


def _mapped_settings(settings: dict[str, Any]) -> dict[str, Any]:
    mapped: dict[str, Any] = {
        "unsupported": {
            key: settings[key]
            for key in settings.keys()
            - {"publish_schedule", "schedule_active", "reaction_emoji", "auto_react_channels"}
        }
    }
    schedule = settings.get("publish_schedule")
    if isinstance(schedule, dict):
        day = str(schedule.get("day", "")).casefold()
        value = str(schedule.get("time", ""))
        if day in WEEKDAYS and re.fullmatch(r"\d{2}:\d{2}", value):
            mapped["publication"] = {
                "weekday": WEEKDAYS[day],
                "time": value,
                "active": bool(settings.get("schedule_active", True)),
            }
    emoji = str(settings.get("reaction_emoji", "✅"))
    custom = CUSTOM_EMOJI.fullmatch(emoji)
    channels = settings.get("auto_react_channels", [])
    mapped["reaction"] = {
        "emoji_id": int(custom.group(1)) if custom else None,
        "emoji_unicode": None if custom else emoji,
        "channel_ids": sorted({int(value) for value in channels})
        if isinstance(channels, list)
        else [],
    }
    return mapped


def markdown(report: MigrationReport) -> str:
    lines = [
        "# Report migrácie legacy údajov",
        "",
        f"- Zdroj SHA-256: `{report.source_sha256}`",
        f"- Referenčný deň: `{report.as_of}`",
        f"- Záznamy spolu: **{report.inventory['announcements_total']}**",
        "- INFO / udalosti: "
        f"**{report.inventory['info_total']} / {report.inventory['event_total']}**",
        "- Aktívne / budúce / expirované: "
        f"**{report.inventory['active_as_of']} / {report.inventory['future_as_of']} / "
        f"{report.inventory['expired_as_of']}**",
        "- Neplatné / možné duplicity: "
        f"**{report.inventory['invalid']} / {report.inventory['duplicates']}**",
        "",
        "## Plán",
        "",
        "| Legacy ID | Typ | Akcia | Stav | Cieľový UUID | Upozornenia |",
        "|---:|---|---|---|---|---|",
    ]
    for item in report.items:
        lines.append(
            f"| {item.legacy_id} | {item.kind} | {item.action} | "
            f"{'aktívny' if item.active else 'neaktívny'} | `{item.target_id}` | "
            f"{', '.join(item.warnings) or '—'} |"
        )
    lines.extend(["", "## Problémy na kontrolu", ""])
    if report.issues:
        lines.extend(f"- `{issue.get('code')}`: {issue}" for issue in report.issues)
    else:
        lines.append("Neboli nájdené poškodené dátumy, neplatné URL ani duplicity.")
    if report.result is not None:
        lines.extend(["", "## Výsledok importu", ""])
        lines.extend(f"- {key}: **{value}**" for key, value in sorted(report.result.items()))
    return "\n".join(lines) + "\n"


def _optional(value: Any) -> str | None:
    text = "" if value is None else str(value).strip()
    return text or None


def _normalized_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return " ".join("".join(char for char in normalized if not unicodedata.combining(char)).split())


def _public_http_url(value: str | None) -> bool:
    return value is not None and valid_public_url(value)


def _database_name(url: str) -> str:
    parsed = urlparse(url)
    name = parsed.path.removeprefix("/")
    if parsed.scheme not in {"postgresql+asyncpg", "postgresql"} or not name:
        raise LegacyMigrationError("Cieľ musí byť explicitná PostgreSQL databáza.")
    return name


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--guild-id", type=int, required=True)
    parser.add_argument("--actor-user-id", type=int, required=True)
    parser.add_argument("--target-database-url")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-target")
    parser.add_argument("--approve-unmatched", action="store_true")
    parser.add_argument("--approved-matches", type=Path)
    parser.add_argument("--apply-settings", action="store_true")
    parser.add_argument("--json-report", type=Path)
    parser.add_argument("--markdown-report", type=Path)
    return parser


async def _run(arguments: argparse.Namespace) -> MigrationReport:
    report = build_report(arguments.source, as_of=arguments.as_of)
    announcements, _, digest = read_legacy(arguments.source)
    if digest != report.source_sha256:
        raise LegacyMigrationError("Zdroj sa počas inventarizácie zmenil; import bol zastavený.")
    if arguments.target_database_url:
        report = await enrich_google_matches(
            report, target_url=arguments.target_database_url, guild_id=arguments.guild_id
        )
    if not arguments.apply:
        return report
    if not arguments.target_database_url:
        raise LegacyMigrationError("Pre import chýba --target-database-url.")
    target_name = _database_name(arguments.target_database_url)
    if arguments.confirm_target != target_name:
        raise LegacyMigrationError(f"Import vyžaduje presné --confirm-target {target_name!r}.")
    approved: dict[int, str] = {}
    if arguments.approved_matches:
        raw = json.loads(arguments.approved_matches.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise LegacyMigrationError("Súbor schválených párovaní musí byť JSON objekt.")
        approved = {int(key): str(value) for key, value in raw.items()}
    return await import_report(
        report,
        announcements,
        target_url=arguments.target_database_url,
        guild_id=arguments.guild_id,
        actor_user_id=arguments.actor_user_id,
        approve_unmatched=arguments.approve_unmatched,
        approved_matches=approved,
        apply_settings=arguments.apply_settings,
    )


def main() -> None:
    parser = _parser()
    arguments = parser.parse_args()
    try:
        report = asyncio.run(_run(arguments))
    except (LegacyMigrationError, OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(2, f"Migrácia bola bezpečne zastavená: {exc}\n")
    if arguments.json_report:
        arguments.json_report.write_text(report.json(), encoding="utf-8")
    if arguments.markdown_report:
        arguments.markdown_report.write_text(markdown(report), encoding="utf-8")
    sys.stdout.write(report.json())


if __name__ == "__main__":
    main()
