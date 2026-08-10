"""Central Slovak display formatting and safe Discord text helpers."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from ipaddress import ip_address
from urllib.parse import urlsplit

from domcek_bot.domain.time import timezone

SLOVAK_WEEKDAYS = (
    "pondelok",
    "utorok",
    "streda",
    "štvrtok",
    "piatok",
    "sobota",
    "nedeľa",
)
DAY_EMOJI_URLS = (
    "https://cdn3.emoji.gg/emojis/5712_monday.png",
    "https://cdn3.emoji.gg/emojis/6201_tuesday.png",
    "https://cdn3.emoji.gg/emojis/4270_wednesday.png",
    "https://cdn3.emoji.gg/emojis/6285_thursday.png",
    "https://cdn3.emoji.gg/emojis/2064_friday.png",
    "https://cdn3.emoji.gg/emojis/4832_saturday.png",
    "https://cdn3.emoji.gg/emojis/8878_sunday.png",
)
DISCORD_MENTION = re.compile(r"@(?=everyone\b|here\b|[!&]?\d+>)", re.IGNORECASE)
EN_DASH = "\N{EN DASH}"


class _GoogleDescriptionParser(HTMLParser):
    _BREAK_TAGS = frozenset({"br", "div", "li", "p"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag.lower() in self._BREAK_TAGS and self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._BREAK_TAGS and self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def google_html_to_text(value: str | None) -> str | None:
    if value is None:
        return None
    parser = _GoogleDescriptionParser()
    parser.feed(value)
    parser.close()
    lines = [line.strip() for line in "".join(parser.parts).splitlines()]
    return "\n".join(line for line in lines if line).strip() or None


def neutralize_discord_mentions(value: str | None) -> str | None:
    if value is None:
        return None
    return DISCORD_MENTION.sub("@\u200b", value)


def valid_public_url(value: str | None) -> bool:
    if value is None:
        return True
    parsed = urlsplit(value)
    hostname = parsed.hostname
    if (
        parsed.scheme not in {"http", "https"}
        or hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or hostname.casefold() == "localhost"
        or hostname.casefold().endswith(".localhost")
    ):
        return False
    try:
        return ip_address(hostname).is_global
    except ValueError:
        # Domain names are not resolved by Carlo: external URLs are handed to
        # Discord, while uploaded INFO images use the local byte-processing path.
        return True


def event_day(starts_at: datetime, timezone_name: str) -> tuple[date, str, str]:
    local = starts_at.astimezone(timezone(timezone_name))
    return local.date(), SLOVAK_WEEKDAYS[local.weekday()], DAY_EMOJI_URLS[local.weekday()]


def all_day_day(starts_on: date) -> tuple[date, str, str]:
    return starts_on, SLOVAK_WEEKDAYS[starts_on.weekday()], DAY_EMOJI_URLS[starts_on.weekday()]


def format_timed_range(starts_at: datetime, ends_at: datetime | None, timezone_name: str) -> str:
    zone = timezone(timezone_name)
    start = starts_at.astimezone(zone)
    if ends_at is None:
        return f"{start:%d.%m.} // {start:%H:%M}"
    end = ends_at.astimezone(zone)
    if end.date() == start.date():
        return f"{start:%d.%m.} // {start:%H:%M}{EN_DASH}{end:%H:%M}"
    return f"{start:%d.%m. %H:%M} {EN_DASH} {end:%d.%m. %H:%M}"


def format_all_day_range(starts_on: date, ends_on: date | None) -> str:
    exclusive_end = ends_on or starts_on + timedelta(days=1)
    last_day = exclusive_end - timedelta(days=1)
    if last_day == starts_on:
        return f"{starts_on:%d.%m.} // celodenná"
    return f"{starts_on:%d.%m.} {EN_DASH} {last_day:%d.%m.} // celodenná"
