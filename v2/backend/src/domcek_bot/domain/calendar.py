"""Pure calendar normalization, control-text and cache-freshness rules."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from domcek_bot.domain.errors import DomainValidationError

STOP_CARLO_LINE = re.compile(r"^\s*stop\s+carlo\s*$", re.IGNORECASE)
STOP_CARLO_HTML_LINE = re.compile(
    r"^\s*(?:<[A-Za-z][^>]*>\s*)*stop\s+carlo"
    r"(?:\s*</[A-Za-z][^>]*>)*\s*$",
    re.IGNORECASE,
)
STOP_CARLO_HTML_BLOCK = re.compile(
    r"<(?P<tag>[A-Za-z][A-Za-z0-9]*)\b[^>]*>\s*stop\s+carlo\s*</(?P=tag)>",
    re.IGNORECASE,
)
STOP_CARLO_SUFFIX = re.compile(
    r"(?<=[.!?])[ \t]*stop\s+carlo"
    r"(?P<closing>[ \t]*(?:</[A-Za-z][^>]*>[ \t]*)*)$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ParsedCalendarDescription:
    raw: str | None
    public_candidate: str | None
    stop_carlo: bool


def parse_calendar_description(description: str | None) -> ParsedCalendarDescription:
    if description is None:
        return ParsedCalendarDescription(raw=None, public_candidate=None, stop_carlo=False)

    raw_description = description
    description, html_replacements = STOP_CARLO_HTML_BLOCK.subn("", description)
    found_control = html_replacements > 0
    public_lines: list[str] = []
    for line in description.splitlines():
        if STOP_CARLO_LINE.fullmatch(line) or STOP_CARLO_HTML_LINE.fullmatch(line):
            found_control = True
            continue
        cleaned_line, replacements = STOP_CARLO_SUFFIX.subn(r"\g<closing>", line)
        found_control = found_control or replacements > 0
        public_lines.append(cleaned_line)
    public_candidate = "\n".join(public_lines).strip() or None
    return ParsedCalendarDescription(
        raw=raw_description,
        public_candidate=public_candidate,
        stop_carlo=found_control,
    )


class CalendarFreshnessState(StrEnum):
    FRESH = "fresh"
    STALE_WARNING = "stale_warning"
    UNSAFE = "unsafe"


@dataclass(frozen=True, slots=True)
class CalendarFreshness:
    state: CalendarFreshnessState
    age: timedelta | None

    @property
    def publication_safe(self) -> bool:
        return self.state is not CalendarFreshnessState.UNSAFE


def assess_calendar_freshness(
    last_success_at: datetime | None,
    *,
    now: datetime,
    warning_after: timedelta,
    unsafe_after: timedelta,
) -> CalendarFreshness:
    if now.utcoffset() is None:
        raise DomainValidationError("freshness reference time must be timezone-aware")
    if warning_after <= timedelta(0) or unsafe_after <= warning_after:
        raise DomainValidationError("freshness thresholds must be positive and ordered")
    if last_success_at is None:
        return CalendarFreshness(CalendarFreshnessState.UNSAFE, None)
    if last_success_at.utcoffset() is None:
        raise DomainValidationError("last success time must be timezone-aware")

    age = max(now - last_success_at, timedelta(0))
    if age > unsafe_after:
        state = CalendarFreshnessState.UNSAFE
    elif age > warning_after:
        state = CalendarFreshnessState.STALE_WARNING
    else:
        state = CalendarFreshnessState.FRESH
    return CalendarFreshness(state, age)
