from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

from domcek_bot.migration.legacy import build_report, markdown, read_legacy, stable_id


def _legacy_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE announcements (
            id INTEGER PRIMARY KEY, typ TEXT NOT NULL, title TEXT NOT NULL,
            description TEXT NOT NULL, datetime TEXT, day TEXT, link TEXT,
            image TEXT, visible_from TEXT, visible_to TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE bot_settings (key TEXT PRIMARY KEY, value TEXT);
        INSERT INTO announcements VALUES
          (1, 'event', 'Stretnutie', 'Text', '12.12. // 19:00', 'piatok', NULL,
           NULL, '10.12.2025', '12.12.2025', '2025-12-01T12:00:00'),
          (2, 'info', 'INFO', 'Popis', NULL, NULL, '', 'https://example.org/image.png',
           '01.08.2026', '20.08.2026', '2026-08-01T12:00:00');
        INSERT INTO bot_settings VALUES
          ('publish_schedule', '{"day":"Friday","time":"09:00"}'),
          ('schedule_active', 'true'),
          ('reaction_emoji', '"<:seen:123456>"'),
          ('auto_react_channels', '[10, 10, 20]');
        """
    )
    connection.commit()
    connection.close()


def test_inventory_is_read_only_and_deterministic(tmp_path: Path) -> None:
    source = tmp_path / "legacy.db"
    _legacy_database(source)
    before = source.read_bytes()

    first = build_report(source, as_of=date(2026, 8, 10))
    second = build_report(source, as_of=date(2026, 8, 10))

    assert source.read_bytes() == before
    assert first.json() == second.json()
    assert first.inventory == {
        "announcements_total": 2,
        "info_total": 1,
        "event_total": 1,
        "active_as_of": 1,
        "future_as_of": 0,
        "expired_as_of": 1,
        "invalid": 0,
        "duplicates": 0,
    }
    assert first.settings["publication"] == {"weekday": 4, "time": "09:00", "active": True}
    assert first.settings["reaction"] == {
        "emoji_id": 123456,
        "emoji_unicode": None,
        "channel_ids": [10, 20],
    }
    assert first.items[0].starts_at == "2025-12-12T19:00:00+01:00"
    assert first.items[0].active is False
    assert first.items[1].valid_until == "2026-08-20"
    assert "## Plán" in markdown(first)
    assert stable_id("event", 1) == stable_id("event", 1)


def test_invalid_and_duplicate_rows_are_reported(tmp_path: Path) -> None:
    source = tmp_path / "legacy.db"
    _legacy_database(source)
    connection = sqlite3.connect(source)
    connection.execute(
        "INSERT INTO announcements VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            3,
            "info",
            "INFO",
            "Popis",
            None,
            None,
            "http://user:pass@example.org/private",
            None,
            "01.08.2026",
            "20.08.2026",
            "2026-08-02T12:00:00",
        ),
    )
    connection.execute(
        "INSERT INTO announcements VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (4, "event", "Chyba", "Text", "nie je datum", None, None, None, "x", "y", "now"),
    )
    connection.commit()
    connection.close()

    report = build_report(source, as_of=date(2026, 8, 10))

    assert report.inventory["invalid"] == 1
    assert report.inventory["duplicates"] == 1
    codes = {issue["code"] for issue in report.issues}
    assert codes == {"invalid_record", "invalid_link_url", "possible_duplicate"}


def test_read_legacy_decodes_json_settings(tmp_path: Path) -> None:
    source = tmp_path / "legacy.db"
    _legacy_database(source)
    announcements, settings, digest = read_legacy(source)
    assert len(announcements) == 2
    assert settings["auto_react_channels"] == [10, 10, 20]
    assert len(digest) == 64
    json.loads(build_report(source, as_of=date(2026, 8, 10)).json())
