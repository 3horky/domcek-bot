"""Two-step, user-bound manual publication confirmation."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from domcek_bot.application.auth.authorization import Capability, Principal
from domcek_bot.application.publication.engine import (
    PreparedPublication,
    PublicationEngine,
    PublicationGuardResult,
    PublicationResult,
    PublicationSlotChanged,
)
from domcek_bot.application.publication.intro import IntroResult
from domcek_bot.application.publication.models import PublicationDraft
from domcek_bot.application.publication.service import PublicationDraftService
from domcek_bot.domain.enums import PublicationMode


class InvalidPublishConfirmation(ValueError):
    pass


class ManualPublicationDisabled(RuntimeError):
    """Raised before any external effect when runtime policy forbids manual publish."""


@dataclass(frozen=True, slots=True)
class ManualPublicationPreview:
    slot_key: str
    scheduled_for: datetime
    announcement_count: int
    message_count: int
    announcement_channel_id: int | None
    draft: PublicationDraft
    confirmation_token: str
    expires_at: datetime


class ManualPublicationService:
    def __init__(
        self,
        draft_service: PublicationDraftService,
        engine: PublicationEngine,
        *,
        secret: str,
        publication_enabled: bool = True,
        lifetime: timedelta = timedelta(minutes=5),
    ) -> None:
        self._draft_service = draft_service
        self._engine = engine
        self._secret = secret.encode()
        self._publication_enabled = publication_enabled
        self._lifetime = lifetime

    async def preview(
        self,
        *,
        principal: Principal,
        now: datetime | None = None,
        for_publication: bool = True,
    ) -> ManualPublicationPreview:
        principal.require(Capability.MANUAL_PUBLISH if for_publication else Capability.VIEW_ADMIN)
        if for_publication and not self._publication_enabled:
            raise ManualPublicationDisabled(
                "manual Discord publication is disabled by the runtime execution policy"
            )
        issued_at = now or datetime.now(UTC)
        publication_preview = await self._engine.preview(
            principal.guild_id,
            reference_time=issued_at,
        )
        draft = publication_preview.draft
        intro = publication_preview.intro
        expires_at = issued_at + self._lifetime
        token = self._encode(
            {
                "guild_id": principal.guild_id,
                "user_id": principal.user_id,
                "slot_key": draft.slot_key,
                "draft_sha256": hashlib.sha256(draft.canonical_json().encode()).hexdigest(),
                "intro_text": intro.text,
                "intro_prompt_version": intro.prompt_version,
                "intro_used_fallback": intro.used_fallback,
                "intro_warning_code": intro.warning_code,
                "exp": int(expires_at.timestamp()),
            }
        )
        return ManualPublicationPreview(
            draft.slot_key,
            draft.scheduled_for,
            len(draft.public_items),
            len(draft.messages),
            publication_preview.announcement_channel_id,
            draft,
            token,
            expires_at,
        )

    async def confirm(
        self,
        token: str,
        *,
        principal: Principal,
        correlation_id: str,
        now: datetime | None = None,
    ) -> tuple[PreparedPublication, PublicationGuardResult | PublicationResult]:
        principal.require(Capability.MANUAL_PUBLISH)
        if not self._publication_enabled:
            raise ManualPublicationDisabled(
                "manual Discord publication is disabled by the runtime execution policy"
            )
        confirmed_at = now or datetime.now(UTC)
        payload = self._decode(token)
        if (
            payload.get("guild_id") != principal.guild_id
            or payload.get("user_id") != principal.user_id
        ):
            raise InvalidPublishConfirmation("confirmation belongs to another user or server")
        expires = payload.get("exp")
        if not isinstance(expires, int) or confirmed_at.timestamp() > expires:
            raise InvalidPublishConfirmation("confirmation expired")
        slot_key = payload.get("slot_key")
        if not isinstance(slot_key, str):
            raise InvalidPublishConfirmation("confirmation has no publication slot")
        draft_sha256 = payload.get("draft_sha256")
        intro_text = payload.get("intro_text")
        intro_prompt_version = payload.get("intro_prompt_version")
        intro_used_fallback = payload.get("intro_used_fallback")
        intro_warning_code = payload.get("intro_warning_code")
        if (
            not isinstance(draft_sha256, str)
            or len(draft_sha256) != 64
            or not isinstance(intro_text, str)
            or not isinstance(intro_prompt_version, str)
            or not isinstance(intro_used_fallback, bool)
            or (intro_warning_code is not None and not isinstance(intro_warning_code, str))
        ):
            raise InvalidPublishConfirmation("confirmation has no canonical preview")
        intro = IntroResult(
            intro_text,
            intro_prompt_version,
            intro_used_fallback,
            intro_warning_code,
        )
        try:
            prepared = await self._engine.prepare(
                principal.guild_id,
                reference_time=confirmed_at,
                mode=PublicationMode.MANUAL,
                initiated_by_user_id=principal.user_id,
                correlation_id=correlation_id,
                expected_slot_key=slot_key,
                expected_draft_sha256=draft_sha256,
                intro_override=intro,
            )
        except PublicationSlotChanged as exc:
            raise InvalidPublishConfirmation(
                "publication slot changed; request a new preview"
            ) from exc
        if prepared.run.slot_key != slot_key:
            raise InvalidPublishConfirmation("publication slot changed; request a new preview")
        result = await self._engine.begin_guard(
            prepared.run.id,
            correlation_id=correlation_id,
            now=confirmed_at,
        )
        return prepared, result

    async def release(
        self,
        run_id: uuid.UUID,
        *,
        principal: Principal,
        correlation_id: str,
        now: datetime | None = None,
    ) -> PublicationGuardResult | PublicationResult:
        principal.require(Capability.MANUAL_PUBLISH)
        return await self._engine.release_guard(
            run_id,
            correlation_id=correlation_id,
            actor_user_id=principal.user_id,
            force=True,
            now=now,
        )

    async def cancel(
        self,
        run_id: uuid.UUID,
        *,
        principal: Principal,
        correlation_id: str,
        now: datetime | None = None,
    ) -> PublicationGuardResult:
        principal.require(Capability.MANUAL_PUBLISH)
        return await self._engine.cancel_guard(
            run_id,
            correlation_id=correlation_id,
            actor_user_id=principal.user_id,
            now=now,
        )

    def _encode(self, payload: dict[str, object]) -> str:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        encoded = base64.urlsafe_b64encode(body).rstrip(b"=")
        signature = hmac.new(self._secret, encoded, hashlib.sha256).digest()
        return f"{encoded.decode()}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"

    def _decode(self, token: str) -> dict[str, object]:
        try:
            body_part, signature_part = token.split(".", 1)
            encoded = body_part.encode()
            supplied = _decode_base64(signature_part)
            expected = hmac.new(self._secret, encoded, hashlib.sha256).digest()
            if not hmac.compare_digest(supplied, expected):
                raise InvalidPublishConfirmation("confirmation signature is invalid")
            value: object = json.loads(_decode_base64(body_part))
            if not isinstance(value, dict):
                raise InvalidPublishConfirmation("confirmation payload is invalid")
            return {str(key): item for key, item in value.items()}
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            if isinstance(exc, InvalidPublishConfirmation):
                raise
            raise InvalidPublishConfirmation("confirmation token is invalid") from exc


def _decode_base64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
