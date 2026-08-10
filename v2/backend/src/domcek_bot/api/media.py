"""Authenticated INFO image upload and public immutable media delivery."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated, cast

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from domcek_bot.api.dependencies import AuthContext, csrf_context
from domcek_bot.api.errors import ApplicationError
from domcek_bot.application.auth.authorization import AuthorizationDenied, Capability
from domcek_bot.config import Settings
from domcek_bot.infrastructure.media import InvalidMediaImage, process_info_image, store_info_image

upload_router = APIRouter(prefix="/api/v1")
public_router = APIRouter(prefix="/media/info")


@upload_router.post("/uploads/info-images", status_code=201)
async def upload_info_image(
    request: Request,
    image: Annotated[UploadFile, File()],
    context: Annotated[AuthContext, Depends(csrf_context)],
) -> dict[str, object]:
    try:
        context.principal.require(Capability.EDIT_CONTENT)
    except AuthorizationDenied as exc:
        raise ApplicationError(
            "forbidden",
            "Prístup bol odmietnutý",
            "Na nahrávanie INFO obrázkov nemáte oprávnenie.",
            403,
        ) from exc

    settings = cast(Settings, request.app.state.settings)
    try:
        content = await image.read(settings.media_max_upload_bytes + 1)
    finally:
        await image.close()
    if not content:
        raise _invalid_image("Vyberte neprázdny obrázok.")
    if len(content) > settings.media_max_upload_bytes:
        limit_mb = settings.media_max_upload_bytes // (1024 * 1024)
        raise _invalid_image(f"Obrázok môže mať najviac {limit_mb} MB.", status=413)

    try:
        processed = await run_in_threadpool(
            process_info_image, content, max_edge=settings.media_max_image_edge
        )
        image_id, _ = await run_in_threadpool(store_info_image, settings.media_root, processed)
    except InvalidMediaImage as exc:
        raise _invalid_image(
            "Súbor musí byť platný statický obrázok vo formáte JPEG, PNG alebo WebP."
        ) from exc
    except OSError as exc:
        raise ApplicationError(
            "media_storage_failed",
            "Obrázok sa nepodarilo uložiť",
            "Úložisko obrázkov momentálne nie je dostupné.",
            503,
        ) from exc

    public_url = f"{settings.public_media_base_url.rstrip('/')}/media/info/{image_id}.webp"
    return {
        "image_url": public_url,
        "width": processed.width,
        "height": processed.height,
        "bytes": len(processed.content),
    }


@public_router.get("/{image_id}.webp", include_in_schema=False)
async def serve_info_image(image_id: uuid.UUID, request: Request) -> FileResponse:
    settings = cast(Settings, request.app.state.settings)
    path = settings.media_root / "info" / f"{image_id}.webp"
    if not path.is_file():
        raise ApplicationError(
            "media_not_found",
            "Obrázok sa nenašiel",
            "Požadovaný obrázok neexistuje.",
            404,
        )
    return FileResponse(
        Path(path),
        media_type="image/webp",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


def _invalid_image(detail: str, *, status: int = 422) -> ApplicationError:
    return ApplicationError("invalid_media_image", "Obrázok nemožno spracovať", detail, status)
