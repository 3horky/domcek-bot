from __future__ import annotations

from datetime import UTC, datetime

from domcek_bot.application.publication.intro import (
    FALLBACK_TEXT,
    INTRO_PROMPT_VERSION,
    IntroService,
    sanitize_intro,
)


class Generator:
    def __init__(self, result: str | Exception) -> None:
        self.result = result
        self.prompt = ""

    async def generate(self, *, prompt: str) -> str:
        self.prompt = prompt
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


async def test_generated_intro_is_versioned_sanitized_and_cannot_mention() -> None:
    generator = Generator(" Ahojte @everyone a <@123>!\r\n\x00Tešíme sa. ")
    result = await IntroService(generator).create(
        enabled=True,
        scheduled_local=datetime(2026, 8, 10, 20, tzinfo=UTC),
        event_titles=("Prvá udalosť",),
    )

    assert result.prompt_version == INTRO_PROMPT_VERSION
    assert result.used_fallback is False
    assert "@everyone" not in result.text
    assert "<@123>" not in result.text
    assert "Prvá udalosť" in generator.prompt
    assert result.text == "Ahojte @\u200beveryone a <@\u200b123>!\nTešíme sa."


async def test_generator_failure_uses_deterministic_slovak_fallback() -> None:
    result = await IntroService(Generator(RuntimeError("provider unavailable"))).create(
        enabled=True,
        scheduled_local=datetime(2026, 8, 10, 20, tzinfo=UTC),
        event_titles=(),
    )

    assert result.text == FALLBACK_TEXT
    assert result.used_fallback is True
    assert result.warning_code == "intro_generator_failed"
    assert sanitize_intro("@here") == "@\u200bhere"
