from __future__ import annotations

from typing import Any, cast

import pytest

from domcek_bot.application.auth.authorization import AppRole, Principal
from domcek_bot.application.publication.manual import ManualPublicationPreview
from domcek_bot.bot.main import (
    ChannelSetupView,
    DirectArchiveView,
    PublishConfirmationView,
    _safe_latency_ms,
)


class _Response:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def edit_message(self, **kwargs: object) -> None:
        del kwargs

    async def send_message(self, content: str, **kwargs: object) -> None:
        del kwargs
        self.messages.append(content)


class _Followup:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send(self, content: str, **kwargs: object) -> None:
        del kwargs
        self.messages.append(content)


class _User:
    id = 123


class _RevokedClient:
    async def principal(self, interaction: object) -> Principal:
        del interaction
        raise PermissionError("roles were revoked")


class _Interaction:
    id = 456
    user = _User()
    client = _RevokedClient()

    def __init__(self) -> None:
        self.response = _Response()
        self.followup = _Followup()


class _ForbiddenEffectService:
    def __init__(self) -> None:
        self.calls = 0

    def __getattr__(self, name: str) -> Any:
        async def forbidden(*args: object, **kwargs: object) -> None:
            del args, kwargs
            self.calls += 1

        return forbidden


def _captured_admin() -> Principal:
    return Principal(
        guild_id=1,
        user_id=123,
        username="admin",
        display_name="Admin",
        avatar_url=None,
        discord_role_ids=frozenset({10}),
        app_roles=frozenset({AppRole.ADMIN}),
    )


@pytest.mark.parametrize(
    ("latency_seconds", "expected"),
    [
        (0.0254, 25),
        (0.0, 0),
        (float("inf"), None),
        (float("-inf"), None),
        (float("nan"), None),
        (1e308, None),
        (-0.001, None),
    ],
)
def test_runtime_latency_is_safe_for_disconnected_gateway(
    latency_seconds: float, expected: int | None
) -> None:
    assert _safe_latency_ms(latency_seconds) == expected


@pytest.mark.asyncio
async def test_channel_confirmation_reloads_roles_before_external_effect() -> None:
    service = _ForbiddenEffectService()
    view = ChannelSetupView(
        service=cast(Any, service),
        principal=_captured_admin(),
        requested_name="projekt",
        emoji="🏠",
        request_interaction_id=789,
    )
    interaction = _Interaction()

    assert "Vlastník: **Admin**" in view.summary
    assert "projektová kategória nastavená v Carlovi" in view.summary
    assert "ostatní členovia servera nie" in view.summary

    await view.children[-1].callback(cast(Any, interaction))

    assert service.calls == 0
    assert interaction.followup.messages == ["Oprávnenie na vytvorenie kanála už nie je platné."]


@pytest.mark.asyncio
@pytest.mark.parametrize("button_index", [0, 1])
async def test_direct_archive_confirmation_reloads_admin_role(button_index: int) -> None:
    service = _ForbiddenEffectService()
    view = DirectArchiveView(
        service=cast(Any, service),
        request_id="00000000-0000-0000-0000-000000000001",
        principal=_captured_admin(),
    )
    interaction = _Interaction()

    await view.children[button_index].callback(cast(Any, interaction))

    assert service.calls == 0
    messages = interaction.followup.messages + interaction.response.messages
    assert messages == ["Admin oprávnenie už nie je platné."]


@pytest.mark.asyncio
async def test_publish_confirmation_reloads_publisher_role_before_external_effect() -> None:
    service = _ForbiddenEffectService()
    view = PublishConfirmationView(
        service=cast(Any, service),
        principal=_captured_admin(),
        preview=cast(ManualPublicationPreview, object()),
    )
    interaction = _Interaction()

    await view.children[0].callback(cast(Any, interaction))

    assert service.calls == 0
    assert interaction.followup.messages == ["Oprávnenie na ručné publikovanie už nie je platné."]
