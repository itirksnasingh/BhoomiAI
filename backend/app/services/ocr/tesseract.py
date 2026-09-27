from __future__ import annotations

import csv
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.services.ocr.base import OCRBlockResult, OCRProvider, OCRResult
from app.services.ocr.image_preprocessor import DocumentImagePreprocessor


class TesseractOCRProvider(OCRProvider):
    """Tesseract OCR with document preprocessing and layout-aware pass selection."""

    def __init__(
        self,
        executable: str | None = None,
        preprocessor: DocumentImagePreprocessor | None = None,
    ):
        self.executable = executable or shutil.which("tesseract")
        if not self.executable:
            raise RuntimeError(
                "Tesseract executable was not found. Make sure Tesseract is installed and available on PATH."
            )
        self.preprocessor = preprocessor or DocumentImagePreprocessor()

    def get_version(self) -> str | None:
        result = subprocess.run(
            [self.executable, "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        lines = result.stdout.strip().splitlines()
        return lines[0].strip() if lines else None

    def process(self, image_path: str, language: str = "mar+eng") -> OCRResult:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"OCR image not found: {path}")

        best: tuple[float, OCRResult] | None = None

        with tempfile.TemporaryDirectory(prefix="bhoomiai_ocr_") as temp_dir:
            for variant_name, image_bytes in self.preprocessor.variants(str(path)):
                variant_path = Path(temp_dir) / f"{variant_name}.png"
                variant_path.write_bytes(image_bytes)

                for psm in (4, 11):
                    result = self._run_tesseract(
                        image_path=variant_path,
                        language=language,
                        psm=psm,
                    )
                    score = self._quality_score(result, variant_name, psm)
                    if best is None or score > best[0]:
                        best = (score, result)

        if best is None:
            raise RuntimeError("Tesseract produced no OCR result.")

        return best[1]

    def _run_tesseract(self, image_path: Path, language: str, psm: int) -> OCRResult:
        result = subprocess.run(
            [
                self.executable,
                str(image_path),
                "stdout",
                "-l",
                language,
                "--psm",
                str(psm),
                "tsv",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )

        blocks = self._parse_tsv(result.stdout, language)
        text = "\n".join(block.text for block in blocks if block.text.strip())
        confidences = [
            float(block.confidence)
            for block in blocks
            if block.confidence is not None and block.confidence >= 0
        ]
        confidence = sum(confidences) / len(confidences) if confidences else None

        return OCRResult(
            engine="tesseract",
            engine_version=self.get_version(),
            language=language,
            text=text,
            confidence=confidence,
            blocks=blocks,
        )

    @staticmethod
    def _quality_score(result: OCRResult, variant_name: str, psm: int) -> float:
        text = result.text or ""
        confidence = result.confidence or 0.0

        useful_signals = [
            "गाव नमुना", "७/१२", "7/12", "सर्वे", "गट", "खातेदार",
            "फेरफार", "जिल्हा", "तालुका", "village", "survey", "owner",
            "property card", "mutation",
        ]
        signal_bonus = sum(3.0 for signal in useful_signals if signal.casefold() in text.casefold())
        alnum_or_dev = len(re.findall(r"[A-Za-z0-9\u0900-\u097F]", text))
        junk = len(re.findall(r"[\[\]{}]{2,}|(?:[oO0]){4,}", text))
        density_bonus = min(6.0, alnum_or_dev / 500.0)
        psm_bonus = 1.0 if psm == 4 else 0.0
        variant_bonus = 0.5 if variant_name == "gray" else 0.0

        return confidence + signal_bonus + density_bonus + psm_bonus + variant_bonus - junk * 0.08

    @staticmethod
    def _parse_tsv(tsv_output: str, language: str) -> list[OCRBlockResult]:
        rows = list(csv.DictReader(tsv_output.splitlines(), delimiter="\t"))
        grouped: dict[tuple[str, str, str], list[dict]] = {}

        for row in rows:
            text = (row.get("text") or "").strip()
            if not text:
                continue
            try:
                confidence = float(row.get("conf", "-1"))
            except ValueError:
                confidence = -1.0
            if confidence < 0:
                continue

            key = (
                row.get("block_num", "0"),
                row.get("par_num", "0"),
                row.get("line_num", "0"),
            )
            grouped.setdefault(key, []).append(
                {
                    "text": text,
                    "confidence": confidence,
                    "left": int(row.get("left", 0)),
                    "top": int(row.get("top", 0)),
                    "width": int(row.get("width", 0)),
                    "height": int(row.get("height", 0)),
                }
            )

        results: list[OCRBlockResult] = []
        for words in grouped.values():
            if not words:
                continue
            text = " ".join(word["text"] for word in words)
            confidence = sum(word["confidence"] for word in words) / len(words)
            left = min(word["left"] for word in words)
            top = min(word["top"] for word in words)
            right = max(word["left"] + word["width"] for word in words)
            bottom = max(word["top"] + word["height"] for word in words)
            results.append(
                OCRBlockResult(
                    text=text,
                    confidence=confidence,
                    bbox={"x": left, "y": top, "width": right - left, "height": bottom - top},
                    language=language,
                )
            )

        return results
