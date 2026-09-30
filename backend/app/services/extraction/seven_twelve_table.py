from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from app.models.extraction import OCRBlock
from app.services.extraction.types import ExtractedFieldResult


@dataclass(frozen=True)
class _HeaderMatch:
    field_name: str
    block: OCRBlock
    score: float


class SevenTwelveTableExtractor:
    """Conservative structure-aware extractor for Maharashtra 7/12 tables.

    Production OCR currently persists line-level OCR blocks with bounding boxes,
    not cell-level table JSON. This adapter reconstructs a lightweight row/column
    view from those blocks and only emits a field when a recognizable 7/12 header
    has a geometrically plausible value underneath or to its right.

    It deliberately avoids inventing values. The output remains linked to the
    value OCR block so the existing FieldEvidence/audit pipeline remains intact.
    """

    DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

    LABELS: dict[str, tuple[str, ...]] = {
        "survey_number": (
            "भूमापन क्रमांक",
            "भूपा क्रमांक",
            "भूमापन क्र",
            "भूमापन नंबर",
            "सर्वे क्रमांक",
            "सर्वे नंबर",
            "गट क्रमांक",
            "गट नंबर",
        ),
        "subdivision": (
            "भूमापन क्रमांकाचा उपविभाग",
            "भूमापन क्रमांक चा उपविभाग",
            "भूभाष क्रमांक चा उपविभाग",
            "उपविभाग",
            "उप विभाग",
        ),
        "land_tenure": (
            "भू-धारणा पद्धती",
            "भू धारणा पद्धती",
            "भुधारणा पद्धती",
            "भूधारणा पद्धती",
        ),
        "holder_name": (
            "भोगवटादाराचे नाव",
            "खातेदाराचे नाव",
            "धारकाचे नाव",
            "मालकाचे नाव",
            "owner name",
            "holder name",
        ),
        "account_number": (
            "खाते क्रमांक",
            "खाते नंबर",
            "खाता क्रमांक",
            "खाता नंबर",
        ),
        "local_field_name": (
            "शेताचे स्थानिक नाव",
            "शेताचा स्थानिक नाव",
            "स्थानिक नाव",
        ),
        "cultivable_area": (
            "लागवडीयोग्य क्षेत्र",
            "लागवडी योग्य क्षेत्र",
            "लागवडीयोग्य क्षेत्रफळ",
            "लागवडी योग्य क्षेत्रफळ",
        ),
    }

    def extract(self, blocks: list[OCRBlock]) -> list[ExtractedFieldResult]:
        usable = [b for b in blocks if self._box(b) and (b.text or '').strip()]
        if len(usable) < 2:
            return []

        rows = self._cluster_rows(usable)
        headers = self._find_headers(usable)
        results: list[ExtractedFieldResult] = []

        for header in headers:
            candidate = self._find_value(header, rows)
            if candidate is None:
                continue
            value_block, relation_score = candidate
            value = self._clean(value_block.text)
            if not value or not self._valid(header.field_name, value):
                continue

            normalized = self._normalize(header.field_name, value)
            if not normalized:
                continue

            ocr_conf = float(value_block.confidence or header.block.confidence or 0.0)
            confidence = min(100.0, max(0.0, ocr_conf * 0.65 + header.score * 25.0 + relation_score * 10.0))
            results.append(
                ExtractedFieldResult(
                    field_name=self._backend_field_name(header.field_name),
                    value=value,
                    normalized_value=normalized,
                    confidence=confidence,
                    extraction_method="seven_twelve_table_header_value",
                    evidence_block_id=value_block.id,
                    evidence_bbox=value_block.bbox or {},
                )
            )

        return self._deduplicate(results)

    @classmethod
    def _backend_field_name(cls, field_name: str) -> str:
        return {
            "survey_number": "survey_number",
            "subdivision": "subdivision",
            "land_tenure": "land_tenure",
            "holder_name": "owner",
            "account_number": "khata_number",
            "local_field_name": "local_field_name",
            "cultivable_area": "area",
        }[field_name]

    def _find_headers(self, blocks: list[OCRBlock]) -> list[_HeaderMatch]:
        found: list[_HeaderMatch] = []
        for block in blocks:
            text = self._norm_label(block.text)
            if not text:
                continue
            best_field = None
            best_score = 0.0
            for field, labels in self.LABELS.items():
                for label in labels:
                    score = self._label_score(text, self._norm_label(label))
                    if score > best_score:
                        best_field, best_score = field, score
            if best_field is not None and best_score >= self._threshold(best_field):
                found.append(_HeaderMatch(best_field, block, best_score))
        # Keep one strongest header per field/physical area.
        found.sort(key=lambda h: h.score, reverse=True)
        selected: list[_HeaderMatch] = []
        seen: set[str] = set()
        for header in found:
            if header.field_name in seen:
                continue
            selected.append(header)
            seen.add(header.field_name)
        return selected

    def _find_value(self, header: _HeaderMatch, rows: list[list[OCRBlock]]) -> tuple[OCRBlock, float] | None:
        hb = self._box(header.block)
        if hb is None:
            return None
        hx, hy, hw, hh = hb
        hcx = hx + hw / 2
        hright = hx + hw

        row_index = next((i for i, row in enumerate(rows) if header.block in row), None)
        if row_index is None:
            return None

        candidates: list[tuple[float, OCRBlock]] = []
        for distance in range(1, min(5, len(rows) - row_index)):
            row = rows[row_index + distance]
            for block in row:
                bb = self._box(block)
                if bb is None or block.id == header.block.id:
                    continue
                x, y, w, h = bb
                center_x = x + w / 2
                horizontal_distance = abs(center_x - hcx)
                # Prefer same-column values. A modest wider band handles OCR
                # line boxes whose x-span covers several adjacent cells.
                column_limit = max(90.0, hw * 2.2, 0.18 * max(hw, w))
                if horizontal_distance > column_limit:
                    continue
                vertical_distance = max(0.0, y - (hy + hh))
                if vertical_distance > 520:
                    continue
                if not self._valid(header.field_name, self._clean(block.text)):
                    continue
                distance_score = max(0.0, 1.0 - distance / 5.0)
                x_score = max(0.0, 1.0 - horizontal_distance / max(column_limit, 1.0))
                candidates.append((distance_score * 0.55 + x_score * 0.45, block))

        # Same-row right-side extraction is appropriate for simple inline
        # "label: value" OCR, but is dangerous in a real 7/12 header row:
        # neighboring column headers are not field values. Only allow it when
        # the row contains very few blocks and the candidate is not itself a
        # recognized 7/12 header.
        current_row = rows[row_index]
        if len(current_row) <= 2:
            for block in current_row:
                if block.id == header.block.id:
                    continue
                bb = self._box(block)
                if bb is None:
                    continue
                x, y, w, h = bb
                if x < hright - 10:
                    continue
                if abs((y + h / 2) - (hy + hh / 2)) > max(24.0, min(hh, h)):
                    continue
                value = self._clean(block.text)
                if self._looks_like_any_known_header(value):
                    continue
                if self._valid(header.field_name, value):
                    gap_score = max(0.0, 1.0 - (x - hright) / 1000.0)
                    candidates.append((0.65 + 0.35 * gap_score, block))

        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], float(item[1].confidence or 0.0)), reverse=True)
        return candidates[0][1], candidates[0][0]

    @staticmethod
    def _cluster_rows(blocks: list[OCRBlock]) -> list[list[OCRBlock]]:
        """Cluster OCR blocks into rows efficiently using row center positions."""
        usable = []

        for block in blocks:
            box = SevenTwelveTableExtractor._box(block)
            if box is None:
                continue

            x, y, w, h = box
            usable.append((y + h / 2, x, block, h))

        usable.sort(key=lambda item: (item[0], item[1]))

        rows: list[list[OCRBlock]] = []
        row_centers: list[float] = []
        row_heights: list[float] = []

        for cy, x, block, h in usable:
            best_index = None
            best_distance = None

            for i, center in enumerate(row_centers):
                tolerance = max(18.0, min(h, row_heights[i]) * 0.9)
                distance = abs(cy - center)

                if distance <= tolerance:
                    if best_distance is None or distance < best_distance:
                        best_index = i
                        best_distance = distance

            if best_index is None:
                rows.append([block])
                row_centers.append(cy)
                row_heights.append(h)
            else:
                rows[best_index].append(block)

                count = len(rows[best_index])
                row_centers[best_index] = (
                    (row_centers[best_index] * (count - 1)) + cy
                ) / count
                row_heights[best_index] = max(
                    row_heights[best_index],
                    h,
                )

        for row in rows:
            row.sort(
                key=lambda item: SevenTwelveTableExtractor._box(item)[0]
            )

        return rows

    @classmethod
    def _threshold(cls, field: str) -> float:
        return 0.74 if field in {"survey_number", "subdivision", "land_tenure", "holder_name", "account_number"} else 0.70

    @classmethod
    def _label_score(cls, text: str, label: str) -> float:
        if text == label:
            return 1.0
        if label in text or text in label:
            return 0.94
        seq = SequenceMatcher(None, text, label).ratio()
        t1, t2 = set(text.split()), set(label.split())
        overlap = len(t1 & t2) / max(1, len(t1 | t2))
        return 0.65 * seq + 0.35 * overlap

    @classmethod
    def _valid(cls, field: str, value: str) -> bool:
        value = cls._clean(value)
        if not value or len(value) > 180:
            return False
        norm = cls._norm_label(value)
        if norm in {"क्रमांक", "नाव", "वर्ग", "क्षेत्र", "क्षेत्रफळ", "माहिती", "दिनांक", "name", "number", "no"}:
            return False
        if field == "survey_number":
            return bool(re.fullmatch(r"[0-9०-९]+(?:\s*/\s*[0-9०-९]+)*", value))
        if field == "subdivision":
            return bool(re.fullmatch(r"[0-9०-९]+(?:\s*/\s*[0-9०-९]+)*|-", value))
        if field == "account_number":
            return bool(re.fullmatch(r"[0-9०-९]+", value))
        if field == "cultivable_area":
            return bool(re.fullmatch(r"[0-9०-९]+(?:[.,][0-9०-९]+)?", value))
        if field == "land_tenure":
            return bool(re.search(r"[A-Za-z\u0900-\u097F]", value))
        if field in {"holder_name", "local_field_name"}:
            return bool(re.search(r"[A-Za-z\u0900-\u097F]", value)) and not cls._looks_header(value)
        return True

    @classmethod
    def _looks_header(cls, value: str) -> bool:
        n = cls._norm_label(value)
        return any(token in n for token in ("क्रमांक", "पद्धती", "नाव", "क्षेत्र", "वर्ग", "माहिती")) and len(n.split()) <= 8

    @classmethod
    def _looks_like_any_known_header(cls, value: str) -> bool:
        n = cls._norm_label(value)
        if not n:
            return True
        for labels in cls.LABELS.values():
            for label in labels:
                if cls._label_score(n, cls._norm_label(label)) >= 0.82:
                    return True
        return cls._looks_header(value)

    @classmethod
    def _normalize(cls, field: str, value: str) -> str:
        value = cls._clean(value).translate(cls.DIGITS)
        if field in {"survey_number", "account_number", "cultivable_area"}:
            return re.sub(r"\s+", "", value).strip(".-")
        if field == "subdivision":
            compact = re.sub(r"\s+", "", value).strip()
            return "" if not compact else compact.translate(cls.DIGITS)
        return re.sub(r"\s+", " ", value).strip(" .,:;|/-").casefold()

    @classmethod
    def _norm_label(cls, value: str | None) -> str:
        if not value:
            return ""
        value = value.translate(cls.DIGITS).casefold().strip()
        value = value.replace("/", " ").replace("|", " ")
        value = re.sub(r"[.:,;()\[\]{}#\\]", " ", value)
        value = re.sub(r"\s*[-–—]\s*", " ", value)
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    @staticmethod
    def _clean(value: str | None) -> str:
        if not value:
            return ""
        value = re.sub(r"\s+", " ", value.replace("\n", " ")).strip()
        return value.strip(" .,:;|/")

    @staticmethod
    def _box(block: OCRBlock) -> tuple[float, float, float, float] | None:
        bbox = block.bbox or {}
        try:
            x = float(bbox.get("x", 0))
            y = float(bbox.get("y", 0))
            w = float(bbox.get("width", 0))
            h = float(bbox.get("height", 0))
        except (TypeError, ValueError):
            return None
        if w <= 0 or h <= 0:
            return None
        return x, y, w, h

    @staticmethod
    def _deduplicate(results: Iterable[ExtractedFieldResult]) -> list[ExtractedFieldResult]:
        best: dict[tuple[str, str], ExtractedFieldResult] = {}
        for result in results:
            key = (result.field_name, result.normalized_value)
            old = best.get(key)
            if old is None or result.confidence > old.confidence:
                best[key] = result
        return list(best.values())
