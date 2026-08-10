"""Versioned, fail-safe introduction generation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from domcek_bot.application.publication.formatting import neutralize_discord_mentions

INTRO_PROMPT_VERSION = "carlo-intro-sk-v1"
FALLBACK_PROMPT_VERSION = "carlo-intro-fallback-sk-v1"
FALLBACK_TEXT = "Ahojte, prinášame prehľad udalostí na najbližšie dva týždne. 👇"
MAX_INTRO_LENGTH = 1200
CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class IntroGenerator(Protocol):
    async def generate(self, *, prompt: str) -> str: ...


@dataclass(frozen=True, slots=True)
class IntroResult:
    text: str
    prompt_version: str
    used_fallback: bool
    warning_code: str | None = None


class IntroService:
    def __init__(self, generator: IntroGenerator | None) -> None:
        self._generator = generator

    async def create(
        self,
        *,
        enabled: bool,
        scheduled_local: datetime,
        event_titles: tuple[str, ...],
    ) -> IntroResult:
        if not enabled or self._generator is None:
            return _fallback("intro_generator_unavailable" if enabled else None)
        prompt = _prompt(scheduled_local, event_titles)
        try:
            candidate = sanitize_intro(await self._generator.generate(prompt=prompt))
        except Exception:  # provider failures are intentionally replaced by a safe fallback
            return _fallback("intro_generator_failed")
        if not candidate:
            return _fallback("intro_generator_empty")
        return IntroResult(candidate, INTRO_PROMPT_VERSION, False)


def sanitize_intro(value: str) -> str:
    cleaned = CONTROL_CHARACTERS.sub("", value).replace("\r\n", "\n").replace("\r", "\n")
    cleaned = "\n".join(line.strip() for line in cleaned.splitlines()).strip()
    cleaned = neutralize_discord_mentions(cleaned) or ""
    return cleaned[:MAX_INTRO_LENGTH].rstrip()


def _fallback(warning_code: str | None) -> IntroResult:
    return IntroResult(FALLBACK_TEXT, FALLBACK_PROMPT_VERSION, True, warning_code)


def _prompt(scheduled_local: datetime, event_titles: tuple[str, ...]) -> str:
    titles = "\n".join(f"- {title}" for title in event_titles[:20]) or "- bez udalostí"
    return (
        "Napíš po slovensky krátky, prirodzený pozdrav a úvod k týždennému prehľadu "
        "udalostí komunity. Použi najviac 3 vety. Nevkladaj žiadne Discord zmienky, "
        "mená rolí ani @everyone; aplikácia oslovenie doplní sama. Nevymýšľaj fakty. "
        f"Dátum zverejnenia: {scheduled_local:%d.%m.%Y}.\n"
        f"Názvy pripravovaných udalostí:\n{titles}"
    )
