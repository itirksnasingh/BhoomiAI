from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Iterator

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


class DocumentImagePreprocessor:
    """Create OCR-friendly image variants without changing the source file."""

    def variants(self, image_path: str) -> Iterator[tuple[str, bytes]]:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"OCR image not found: {path}")

        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")

            # Keep a clean grayscale version as the primary OCR input.
            gray = ImageOps.grayscale(image)
            gray = ImageOps.autocontrast(gray, cutoff=1)

            yield "gray", self._png_bytes(gray)

            # A mild sharpening pass helps old scans without aggressively
            # destroying thin Devanagari strokes.
            sharp = ImageEnhance.Sharpness(gray).enhance(1.35)
            sharp = sharp.filter(ImageFilter.UnsharpMask(radius=1.2, percent=110, threshold=3))
            yield "sharp", self._png_bytes(sharp)

            # Upscale only smaller scans. Large documents are already large
            # enough and unnecessary upscaling would increase OCR latency.
            max_dimension = max(gray.size)
            if max_dimension < 2200:
                scale = 1.5
                enlarged = gray.resize(
                    (int(gray.width * scale), int(gray.height * scale)),
                    Image.Resampling.LANCZOS,
                )
                enlarged = ImageOps.autocontrast(enlarged, cutoff=1)
                yield "upscaled", self._png_bytes(enlarged)

    @staticmethod
    def _png_bytes(image: Image.Image) -> bytes:
        buffer = BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()
