from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from domcek_bot.infrastructure.media import InvalidMediaImage, process_info_image, store_info_image


def test_info_image_is_resized_and_reencoded_without_source_metadata(tmp_path: Path) -> None:
    source = io.BytesIO()
    image = Image.new("RGBA", (2200, 1100), (30, 120, 70, 180))
    image.save(source, format="PNG", pnginfo=None)

    processed = process_info_image(source.getvalue(), max_edge=800)

    assert (processed.width, processed.height) == (800, 400)
    with Image.open(io.BytesIO(processed.content)) as result:
        assert result.format == "WEBP"
        assert result.size == (800, 400)
        assert not result.getexif()

    image_id, path = store_info_image(tmp_path, processed)
    assert path == tmp_path / "info" / f"{image_id}.webp"
    assert path.read_bytes() == processed.content


@pytest.mark.parametrize("content", [b"", b"<svg><script>alert(1)</script></svg>", b"not-image"])
def test_info_image_rejects_non_raster_content(content: bytes) -> None:
    with pytest.raises(InvalidMediaImage):
        process_info_image(content, max_edge=800)
