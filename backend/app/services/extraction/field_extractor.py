from __future__ import annotations

import re
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from app.models.extraction import OCRBlock
from app.services.extraction.seven_twelve_table import SevenTwelveTableExtractor
from app.services.extraction.types import ExtractedFieldResult




class FieldExtractor:
    """Deterministic, evidence-linked land-record field extractor.

    The extractor deliberately prefers precision over speculative extraction.
    It supports:
      - inline label/value OCR blocks
      - spatially adjacent label/value blocks on the same row
      - owner-name rows beneath the explicit owner-name table header

    It never changes the source OCR text and never treats an OCR heading as a
    field value merely because it contains a label substring.
    """

    DIGIT_TRANSLATION = str.maketrans("०१२३४५६७८९", "0123456789")

    # Exact normalized labels only. Substring matching is intentionally avoided.
    ADJACENT_LABELS: dict[str, tuple[str, ...]] = {
        "village": (
            "village",
            "village name",
            "vill",
            "गाव",
            "गाव नाव",
            "मौजा",
            "मौजा नाव",
        ),
        "taluka": (
            "taluka",
            "taluka name",
            "tehsil",
            "tehsil name",
            "taluka tehsil",
            "तालुका",
            "तालुका नाव",
            "तहसील",
            "तहसील नाव",
        ),
        "district": (
            "district",
            "district name",
            "dist",
            "जिल्हा",
            "जिल्हा नाव",
        ),
        "survey_number": (
            "survey number",
            "survey no",
            "survey #",
            "survey",
            "gat number",
            "gat no",
            "gat #",
            "gat",
            "सर्वे नं",
            "सर्वे क्रमांक",
            "सर्वे नंबर",
            "सर्वे क्र",
            "सर्वे",
            "गट नं",
            "गट क्रमांक",
            "गट नंबर",
            "गट क्र",
            "गट",
        ),
        "khata_number": (
            "khata number",
            "khata no",
            "khata",
            "account number",
            "account no",
            "खाता क्रमांक",
            "खाता नंबर",
            "खाता नं",
            "खाते क्र",
            "खाते क्रमांक",
            "खाते नं",
            "खाते",
        ),
        "area": (
            "area",
            "extent",
            "land area",
            "क्षेत्र",
            "क्षेत्रफळ",
            "क्षेत्रफळ हे",
        ),
        "classification": (
            "classification",
            "land classification",
            "land use",
            "land type",
            "जमिनीचा प्रकार",
            "जमिनीचा वर्ग",
            "भूमीचा प्रकार",
            "भूमीचा वर्ग",
        ),
        "mutation": (
            "mutation",
            "mutation number",
            "mutation no",
            "ferfar",
            "ferfar number",
            "ferfar no",
            "फेरफार",
            "फेरफार क्रमांक",
            "फेरफार नंबर",
            "फेरफार नं",
            "फेरफार क्र",
        ),
        "registration": (
            "registration",
            "registration number",
            "registration no",
            "document number",
            "document no",
            "नोंदणी",
            "नोंदणी क्रमांक",
            "नोंदणी नंबर",
            "नोंदणी नं",
            "दस्त क्रमांक",
            "दस्त नंबर",
            "दस्त नं",
        ),
    }

    OWNER_HEADER_LABELS = {
        "owner name",
        "landowner name",
        "account holder name",
        "holder name",
        "खातेदाराचे नाव",
        "खातेदाराचे नाव",
        "धारकाचे नाव",
        "मालकाचे नाव",
    }

    # OCR often returns these as headings/table labels. They must never become
    # location/owner/classification values through adjacent-label extraction.
    GENERIC_HEADER_TOKENS = {
        "क्रमांक",
        "क्रमांक नं",
        "नंबर",
        "नं",
        "क्र",
        "क्र.",
        "नाव",
        "माहिती",
        "प्रकार",
        "वर्ग",
        "हक्क",
        "हक्काचा प्रकार",
        "नोंदणी माहिती",
        "फेरफार माहिती",
        "दिनांक",
        "क्षेत्रफळ",
        "क्षेत्र",
        "एकक",
        "भोगवटा",
        "नोंद",
        "विवरण",
        "details",
        "name",
        "number",
        "no",
        "type",
        "classification",
        "information",
        "area",
        "extent",
    }

    FIELD_LABEL_TOKENS = {
        "village",
        "taluka",
        "tehsil",
        "district",
        "survey",
        "gat",
        "khata",
        "account",
        "area",
        "extent",
        "classification",
        "mutation",
        "ferfar",
        "registration",
        "document",
        "गाव",
        "मौजा",
        "तालुका",
        "तहसील",
        "जिल्हा",
        "सर्वे",
        "गट",
        "खाता",
        "खाते",
        "क्षेत्र",
        "क्षेत्रफळ",
        "जमिनीचा प्रकार",
        "फेरफार",
        "नोंदणी",
        "दस्त",
    }

    def extract(self, blocks: list[OCRBlock]) -> list[ExtractedFieldResult]:
        ordered = sorted(blocks, key=self._block_sort_key)
        results: list[ExtractedFieldResult] = []

        # Phase 5: structure-aware 7/12 extraction runs before the legacy
        # line/adjacency rules. It is evidence-linked and conservative; when
        # it cannot establish a reliable header/value relationship it returns
        # no candidate and the legacy rules continue to operate.
        results.extend(SevenTwelveTableExtractor().extract(ordered))

        for index, block in enumerate(ordered):
            results.extend(self._extract_from_block(block))
            next_block = ordered[index + 1] if index + 1 < len(ordered) else None
            results.extend(self._extract_from_adjacent_block(block, next_block))

        results.extend(self._extract_owner_rows(ordered))
        results.extend(self._extract_area_rows(ordered))

        # Keep the strongest evidence for the same field/value. Multiple owner
        # or area values are retained when their values are genuinely different.
        best: dict[tuple[str, str], ExtractedFieldResult] = {}
        for result in results:
            key = (result.field_name, result.normalized_value)
            previous = best.get(key)
            if previous is None or result.confidence > previous.confidence:
                best[key] = result

        return sorted(
            best.values(),
            key=lambda result: self._result_sort_key(result, ordered),
        )

    # ------------------------------------------------------------------
    # Inline label/value extraction
    # ------------------------------------------------------------------

    def _extract_from_block(self, block: OCRBlock) -> list[ExtractedFieldResult]:
        extractors: tuple[Callable[[OCRBlock], ExtractedFieldResult | None], ...] = (
            self._extract_survey_number,
            self._extract_village,
            self._extract_taluka,
            self._extract_district,
            self._extract_owner_inline,
            self._extract_khata_number,
            self._extract_area,
            self._extract_classification,
            self._extract_mutation,
            self._extract_registration,
        )
        results: list[ExtractedFieldResult] = []
        for extractor in extractors:
            result = extractor(block)
            if result:
                results.append(result)
        return results

    def _extract_survey_number(self, block: OCRBlock):
        return self._match(
            block,
            "survey_number",
            (
                r"^survey\s*(?:number|no\.?|#)\s*[:|/\-]\s*([0-9०-९]+(?:\s*/\s*[0-9०-९]+)*)$",
                r"^gat\s*(?:number|no\.?|#)\s*[:|/\-]\s*([0-9०-९]+(?:\s*/\s*[0-9०-९]+)*)$",
                r"^सर्वे\s*(?:क्रमांक|नंबर|नं\.?|क्र\.?)\s*[:|/\-]\s*([0-9०-९]+(?:\s*/\s*[0-9०-९]+)*)$",
                r"^गट\s*(?:क्रमांक|नंबर|नं\.?|क्र\.?)\s*[:|/\-]\s*([0-9०-९]+(?:\s*/\s*[0-9०-९]+)*)$",
            ),
            self._normalize_number,
            value_validator=self._valid_survey_number,
        )

    def _extract_village(self, block: OCRBlock):
        return self._match(
            block,
            "village",
            (
                r"^village\s*(?:name)?\s*[:|/\-]\s*(.+)$",
                r"^vilage\s*(?:name)?\s*[:|/\-]\s*(.+)$",
                r"^vill\.?\s*[:|/\-]\s*(.+)$",
                r"^(?:गाव|मौजा)\s*(?:नाव)?\s*[:|/\-]\s*(.+)$",
            ),
            value_validator=lambda value: self._valid_text_value(value, "village"),
        )

    def _extract_taluka(self, block: OCRBlock):
        return self._match(
            block,
            "taluka",
            (
                r"^taluka\s*(?:/\s*tehsil|name)?\s*[:|/\-]\s*(.+)$",
                r"^tehsil\s*(?:name)?\s*[:|/\-]\s*(.+)$",
                r"^तालुका\s*(?:नाव)?\s*[:|/\-]\s*(.+)$",
                r"^तहसील\s*(?:नाव)?\s*[:|/\-]\s*(.+)$",
            ),
            value_validator=lambda value: self._valid_text_value(value, "taluka"),
        )

    def _extract_district(self, block: OCRBlock):
        return self._match(
            block,
            "district",
            (
                r"^district\s*(?:name)?\s*[:|/\-]\s*(.+)$",
                r"^dist\.?\s*[:|/\-]\s*(.+)$",
                r"^जिल्हा\s*(?:नाव)?\s*[:|/\-]\s*(.+)$",
            ),
            value_validator=lambda value: self._valid_text_value(value, "district"),
        )

    def _extract_owner_inline(self, block: OCRBlock):
        return self._match(
            block,
            "owner",
            (
                r"^owner\s*(?:name)?\s*[:|/\-]\s*(.+)$",
                r"^landowner\s*(?:name)?\s*[:|/\-]\s*(.+)$",
                r"^holder\s*(?:name)?\s*[:|/\-]\s*(.+)$",
                r"^account\s*holder\s*(?:name)?\s*[:|/\-]\s*(.+)$",
                r"^(?:खातेदाराचे\s*नाव|धारकाचे\s*नाव|मालकाचे\s*नाव)\s*[:|/\-]\s*(.+)$",
            ),
            value_validator=lambda value: self._valid_text_value(value, "owner"),
        )

    def _extract_khata_number(self, block: OCRBlock):
        return self._match(
            block,
            "khata_number",
            (
                r"^khata\s*(?:number|no\.?)?\s*[:|/\-]\s*([0-9०-९]+)$",
                r"^account\s*(?:number|no\.?)\s*[:|/\-]\s*([0-9०-९]+)$",
                r"^खाता\s*(?:क्रमांक|नंबर|नं\.?)?\s*[:|/\-]\s*([0-9०-९]+)$",
                r"^खाते\s*(?:क्र\.?|क्रमांक|नं\.?)?\s*[:|/\-]\s*([0-9०-९]+)$",
            ),
            self._normalize_number,
            value_validator=lambda value: bool(re.fullmatch(r"[0-9०-९]+", value)),
        )

    def _extract_area(self, block: OCRBlock):
        return self._match(
            block,
            "area",
            (
                r"^area\s*[:|/\-]\s*([0-9०-९]+(?:[.,][0-9०-९]+)?)\s*(?:hectare|hectares|ha|acre|acres|sq\.?\s*m\.?|sqft)?$",
                r"^extent\s*[:|/\-]\s*([0-9०-९]+(?:[.,][0-9०-९]+)?)\s*(?:hectare|hectares|ha|acre|acres)?$",
                r"^(?:क्षेत्र|क्षेत्रफळ)\s*[:|/\-]\s*([0-9०-९]+(?:[.,][0-9०-९]+)?)\s*(?:हेक्टर|हे|एकर)?$",
            ),
            self._normalize_number,
            value_validator=lambda value: self._valid_positive_number(value),
        )

    def _extract_classification(self, block: OCRBlock):
        return self._match(
            block,
            "classification",
            (
                r"^classification\s*[:|/\-]\s*(.+)$",
                r"^land\s*(?:classification|use|type)\s*[:|/\-]\s*(.+)$",
                r"^(?:जमिनीचा|भूमीचा)\s*(?:वर्ग|प्रकार)\s*[:|/\-]\s*(.+)$",
                r"^जमिनीचा\s*प्रकार\s*[:|/\-]\s*(.+)$",
            ),
            value_validator=lambda value: self._valid_text_value(value, "classification"),
        )

    def _extract_mutation(self, block: OCRBlock):
        return self._match(
            block,
            "mutation",
            (
                r"^mutation\s*(?:number|no\.?)?\s*[:|/\-]\s*(.+)$",
                r"^ferfar\s*(?:number|no\.?)?\s*[:|/\-]\s*(.+)$",
                r"^फेरफार\s*(?:क्रमांक|नंबर|नं\.?|क्र\.?)?\s*[:|/\-]\s*(.+)$",
            ),
            value_validator=lambda value: self._valid_text_value(value, "mutation"),
        )

    def _extract_registration(self, block: OCRBlock):
        return self._match(
            block,
            "registration",
            (
                r"^registration\s*(?:number|no\.?)?\s*[:|/\-]\s*(.+)$",
                r"^registered\s*(?:number|no\.?)\s*[:|/\-]\s*(.+)$",
                r"^document\s*(?:number|no\.?)\s*[:|/\-]\s*(.+)$",
                r"^(?:नोंदणी|दस्त)\s*(?:क्रमांक|नंबर|नं\.?|क्र\.?)?\s*[:|/\-]\s*(.+)$",
            ),
            value_validator=lambda value: self._valid_text_value(value, "registration"),
        )

    # ------------------------------------------------------------------
    # Spatial label/value extraction
    # ------------------------------------------------------------------

    def _extract_from_adjacent_block(
        self,
        label_block: OCRBlock,
        value_block: OCRBlock | None,
    ) -> list[ExtractedFieldResult]:
        if value_block is None:
            return []

        normalized_label = self._normalize_label(label_block.text)
        field_name = self._field_for_adjacent_label(normalized_label)
        if field_name is None:
            return []

        if not self._same_row_right_of(label_block, value_block):
            return []

        candidate = self._clean_candidate(value_block.text)
        if not candidate:
            return []

        if not self._valid_adjacent_candidate(field_name, candidate):
            # Preserve suspicious table/header candidates for human review instead
            # of silently dropping them. These are deliberately low-confidence so
            # the validation layer routes them to the review queue.
            if field_name in {"mutation", "registration"} and self._looks_like_table_label(candidate):
                return [
                    self._result(
                        field_name=field_name,
                        value=candidate,
                        block=value_block,
                        method="spatial_label_value_suspect",
                        normalized=self._normalize_text(candidate),
                        confidence_override=25.0,
                    )
                ]
            return []

        normalized = (
            self._normalize_number(candidate)
            if field_name in {"survey_number", "khata_number", "area"}
            else self._normalize_text(candidate)
        )

        return [
            self._result(
                field_name=field_name,
                value=candidate,
                block=value_block,
                method="spatial_label_value",
                normalized=normalized,
            )
        ]

    def _field_for_adjacent_label(self, normalized_label: str) -> str | None:
        if not normalized_label:
            return None
        for field_name, labels in self.ADJACENT_LABELS.items():
            if normalized_label in labels:
                return field_name
        return None

    # ------------------------------------------------------------------
    # Owner table rows
    # ------------------------------------------------------------------

    def _extract_owner_rows(self, ordered: list[OCRBlock]) -> list[ExtractedFieldResult]:
        results: list[ExtractedFieldResult] = []
        headers = [
            block
            for block in ordered
            if self._normalize_label(block.text) in self.OWNER_HEADER_LABELS
        ]

        for header in headers:
            hb = self._box(header)
            if hb is None:
                continue

            header_x, header_y, header_w, header_h = hb
            header_bottom = header_y + header_h
            column_right = header_x + max(header_w, 240)

            candidates = []
            for block in ordered:
                if block.id == header.id:
                    continue
                box = self._box(block)
                if box is None:
                    continue
                x, y, w, h = box
                if y <= header_bottom:
                    continue
                if y - header_bottom > 260:
                    continue
                # Owner values should remain in the first table column.
                if x < header_x - 20 or x > column_right + 40:
                    continue
                candidate = self._clean_candidate(block.text)
                if not candidate or not self._valid_text_value(candidate, "owner"):
                    continue
                if self._looks_like_table_label(candidate):
                    continue
                # Names normally contain letters/Devanagari and are not just
                # numeric identifiers.
                if not re.search(r"[A-Za-z\u0900-\u097F]", candidate):
                    continue
                candidates.append((y, x, block))

            # Take only the first two nearby owner rows; this covers the common
            # 7/12 owner table while avoiding unrelated lower sections.
            for _, _, block in sorted(candidates)[:2]:
                results.append(
                    self._result(
                        field_name="owner",
                        value=self._clean_candidate(block.text),
                        block=block,
                        method="owner_table_row",
                    )
                )

        return results

    def _extract_area_rows(self, ordered: list[OCRBlock]) -> list[ExtractedFieldResult]:
        """Extract numeric area values beneath an explicit area/extent header."""
        results: list[ExtractedFieldResult] = []
        headers = [
            block
            for block in ordered
            if self._normalize_label(block.text) in {
                "area",
                "extent",
                "land area",
                "क्षेत्र",
                "क्षेत्रफळ",
            }
        ]

        for header in headers:
            hb = self._box(header)
            if hb is None:
                continue
            hx, hy, hw, hh = hb
            bottom = hy + hh
            right = hx + max(hw, 180)

            candidates: list[tuple[float, OCRBlock]] = []
            for block in ordered:
                if block.id == header.id:
                    continue
                box = self._box(block)
                if box is None:
                    continue
                x, y, w, h = box
                if y <= bottom or y - bottom > 280:
                    continue
                if x < hx - 20 or x > right + 40:
                    continue
                value = self._clean_candidate(block.text)
                if self._valid_positive_number(value):
                    candidates.append((y, block))

            for _, block in sorted(candidates)[:10]:
                value = self._clean_candidate(block.text)
                results.append(
                    self._result(
                        field_name="area",
                        value=value,
                        block=block,
                        method="area_table_row",
                        normalized=self._normalize_number(value),
                    )
                )

        return results

    # ------------------------------------------------------------------
    # Generic matching / validation helpers
    # ------------------------------------------------------------------

    def _match(
        self,
        block: OCRBlock,
        field_name: str,
        patterns: tuple[str, ...],
        normalize: Callable[[str], str] | None = None,
        value_validator: Callable[[str], bool] | None = None,
    ) -> ExtractedFieldResult | None:
        text = self._clean_candidate(block.text)
        if not text:
            return None

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue

            value = self._clean_candidate(match.group(1))
            if not value:
                continue
            if value_validator and not value_validator(value):
                continue

            normalized = normalize(value) if normalize else self._normalize_text(value)
            if not normalized:
                continue

            return self._result(
                field_name=field_name,
                value=value,
                block=block,
                method="regex_label",
                normalized=normalized,
            )

        return None

    def _result(
        self,
        field_name: str,
        value: str,
        block: OCRBlock,
        method: str,
        normalized: str | None = None,
        confidence_override: float | None = None,
    ) -> ExtractedFieldResult:
        return ExtractedFieldResult(
            field_name=field_name,
            value=value,
            normalized_value=normalized if normalized is not None else self._normalize_text(value),
            confidence=(
                confidence_override
                if confidence_override is not None
                else self._field_confidence(block.confidence, method)
            ),
            extraction_method=method,
            evidence_block_id=block.id,
            evidence_bbox=block.bbox or {},
        )

    def _valid_adjacent_candidate(self, field_name: str, value: str) -> bool:
        if field_name == "survey_number":
            return self._valid_survey_number(value)
        if field_name == "khata_number":
            return bool(re.fullmatch(r"[0-9०-९]+", value))
        if field_name == "area":
            return self._valid_positive_number(value)
        return self._valid_text_value(value, field_name)

    def _valid_text_value(self, value: str, field_name: str) -> bool:
        value = self._clean_candidate(value)
        if not value or len(value) > 120:
            return False

        normalized = self._normalize_label(value)
        if not normalized:
            return False
        if normalized in self.GENERIC_HEADER_TOKENS:
            return False
        if self._looks_like_table_label(value):
            return False

        # Location/owner/classification values must not contain another field's
        # label followed by a separator. This catches OCR column headers.
        if re.search(
            r"(?:village|taluka|tehsil|district|owner|holder|survey|gat|khata|area|classification|mutation|ferfar|registration|document)\s*[:|/\-]",
            value,
            flags=re.IGNORECASE,
        ):
            return False
        if re.search(
            r"(?:गाव|मौजा|तालुका|तहसील|जिल्हा|खातेदार|धारक|सर्वे|गट|खाता|खाते|क्षेत्र|क्षेत्रफळ|फेरफार|नोंदणी|दस्त)\s*[:|/\-]",
            value,
        ):
            return False

        # Header-like values with mostly punctuation/numbers are not names or
        # locations. Mutation/registration may legitimately be numeric.
        if field_name in {"village", "taluka", "district", "owner", "classification"}:
            if not re.search(r"[A-Za-z\u0900-\u097F]", value):
                return False

        return True

    def _valid_survey_number(self, value: str) -> bool:
        value = self._clean_candidate(value)
        return bool(re.fullmatch(r"[0-9०-९]+(?:\s*/\s*[0-9०-९]+)*", value))

    def _valid_positive_number(self, value: str) -> bool:
        normalized = self._normalize_number(value)
        if not re.fullmatch(r"[0-9]+(?:[.,][0-9]+)?", normalized):
            return False
        try:
            return float(normalized.replace(",", ".")) > 0
        except ValueError:
            return False

    def _looks_like_table_label(self, value: str) -> bool:
        normalized = self._normalize_label(value)
        if normalized in self.GENERIC_HEADER_TOKENS:
            return True

        tokens = set(normalized.split())
        if tokens and tokens.issubset({
            "name", "number", "no", "type", "classification", "area", "extent",
            "information", "details", "क्रमांक", "नंबर", "नं", "क्र", "नाव",
            "माहिती", "प्रकार", "वर्ग", "हक्क", "क्षेत्र", "क्षेत्रफळ", "एकक",
            "भोगवटा", "नोंद", "विवरण", "नोंदणी", "फेरफार", "दिनांक",
        }):
            return True

        # Typical OCR header such as "गटक्रमांक | क्रमांक".
        if "क्रमांक" in normalized and not re.search(r"\d", normalized):
            return True
        if "क्षेत्रफळ" in normalized and not re.search(r"\d", normalized):
            return True
        if "हक्काचा प्रकार" in normalized:
            return True
        if "नोंदणी माहिती" in normalized or "फेरफार माहिती" in normalized:
            return True
        if normalized == "दिनांक":
            return True

        return False

    def _clean_candidate(self, value: str | None) -> str:
        if not value:
            return ""
        value = value.replace("\n", " ")
        value = re.sub(r"\s+", " ", value).strip()
        return value.strip(" .,:;|/-")

    def _normalize_label(self, value: str | None) -> str:
        if not value:
            return ""
        value = value.translate(self.DIGIT_TRANSLATION)
        value = value.casefold().strip()
        value = value.replace("/", " ").replace("|", " ")
        value = re.sub(r"[.:,;()\[\]{}#\\]", " ", value)
        value = re.sub(r"\s*-\s*", " ", value)
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    def _normalize_text(self, value: str) -> str:
        value = value.translate(self.DIGIT_TRANSLATION)
        value = re.sub(r"\s+", " ", value.strip())
        return value.strip(".,;:()[]{}").casefold()

    def _normalize_number(self, value: str) -> str:
        value = value.translate(self.DIGIT_TRANSLATION)
        return re.sub(r"\s+", "", value.strip())

    # ------------------------------------------------------------------
    # Geometry / confidence
    # ------------------------------------------------------------------

    @staticmethod
    def _box(block: OCRBlock) -> tuple[float, float, float, float] | None:
        bbox = block.bbox or {}
        try:
            x = float(bbox.get("x", 0))
            y = float(bbox.get("y", 0))
            width = float(bbox.get("width", 0))
            height = float(bbox.get("height", 0))
        except (TypeError, ValueError):
            return None
        if width <= 0 or height <= 0:
            return None
        return x, y, width, height

    def _same_row_right_of(self, label_block: OCRBlock, value_block: OCRBlock) -> bool:
        left = self._box(label_block)
        right = self._box(value_block)
        if left is None or right is None:
            return False

        lx, ly, lw, lh = left
        rx, ry, rw, rh = right
        label_right = lx + lw
        label_center_y = ly + lh / 2
        value_center_y = ry + rh / 2

        if rx < label_right - 10:
            return False

        vertical_delta = abs(value_center_y - label_center_y)
        row_tolerance = max(18.0, min(lh, rh) * 0.9)
        if vertical_delta > row_tolerance:
            return False

        horizontal_gap = rx - label_right
        return 0 <= horizontal_gap <= 1400

    @staticmethod
    def _block_sort_key(block: OCRBlock):
        bbox = block.bbox or {}
        return (
            float(bbox.get("y", 0)),
            float(bbox.get("x", 0)),
            block.block_number,
        )

    @staticmethod
    def _result_sort_key(result: ExtractedFieldResult, ordered: list[OCRBlock]):
        try:
            index = next(i for i, block in enumerate(ordered) if block.id == result.evidence_block_id)
        except StopIteration:
            index = 0
        return (index, result.field_name, result.normalized_value)

    @staticmethod
    def _field_confidence(ocr_confidence: float | None, method: str) -> float:
        base = 0.0 if ocr_confidence is None else max(0.0, min(100.0, float(ocr_confidence)))
        bonus = {
            "regex_label": 4.0,
            "spatial_label_value": 2.5,
            "owner_table_row": 1.5,
            "area_table_row": 1.5,
        }.get(method, 0.0)
        return min(100.0, base + bonus)
