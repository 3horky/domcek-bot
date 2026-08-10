"""Validated processing and durable local storage for INFO thumbnails."""

from __future__ import annotations

import io
import uuid
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

SUPPORTED_INPUT_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})
Image.MAX_IMAGE_PIXELS = 25_000_000


class InvalidMediaImage(ValueError):
    """Raised when uploaded bytes are not an accepted, safe still image."""


@dataclass(frozen=True, slots=True)
class ProcessedMediaImage:
    content: bytes
    width: int
    height: int


def process_info_image(content: bytes, *, max_edge: int) -> ProcessedMediaImage:
    """Decode, orient, resize and re-encode an INFO thumbnail without source metadata."""

    try:
        with Image.open(io.BytesIO(content)) as source:
            source.verify()
        with Image.open(io.BytesIO(content)) as source:
            if source.format not in SUPPORTED_INPUT_FORMATS:
                raise InvalidMediaImage("supported formats are JPEG, PNG and WebP")
            if getattr(source, "is_animated", False):
                raise InvalidMediaImage("animated images are not supported")
            oriented = ImageOps.exif_transpose(source)
            mode = "RGBA" if "A" in oriented.getbands() else "RGB"
            normalized = oriented.convert(mode)
            normalized.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            normalized.save(output, format="WEBP", quality=86, method=6)
            return ProcessedMediaImage(output.getvalue(), normalized.width, normalized.height)
    except InvalidMediaImage:
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidMediaImage("file is not a valid supported image") from exc


def store_info_image(root: Path, image: ProcessedMediaImage) -> tuple[uuid.UUID, Path]:
    """Atomically store processed bytes under a generated non-user-controlled name."""

    image_id = uuid.uuid4()
    directory = root / "info"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{image_id}.webp"
    temporary = directory / f".{image_id}.tmp"
    temporary.write_bytes(image.content)
    temporary.replace(target)
    return image_id, target
