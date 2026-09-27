from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.documents import DocumentType


@dataclass(frozen=True)
class DocumentClassification:
    document_type: DocumentType
    confidence: float
    language: str
    matched_signals: list[str]


class LandDocumentClassifier:
    """Lightweight explainable classifier for common Maharashtra land records."""

    _rules = {
        DocumentType.SEVEN_TWELVE: (
            7,
            [
                ("गाव नमुना ७/१२", 8),
                ("७/१२", 8),
                ("7/12", 8),
                ("सर्वे नं", 3),
                ("गट नं", 3),
                ("खातेदार", 4),
                ("जमिनीचा प्रकार", 3),
                ("क्षेत्र", 2),
            ],
        ),
        DocumentType.EIGHT_A: (
            7,
            [
                ("गाव नमुना ८अ", 10),
                ("८अ", 8),
                ("8A", 8),
                ("खाता क्र", 4),
                ("खातेदार", 3),
                ("क्षेत्र", 2),
            ],
        ),
        DocumentType.FERFAR: (
            7,
            [
                ("फेरफार", 10),
                ("ferfar", 8),
                ("mutation", 6),
                ("नोंद दिनांक", 3),
                ("फेरफार क्र", 5),
            ],
        ),
        DocumentType.PROPERTY_CARD: (
            7,
            [
                ("property card", 10),
                ("मालमत्ता पत्रक", 10),
                ("मालमत्ता", 5),
                ("cts", 4),
                ("city survey", 5),
            ],
        ),
    }

    def classify(self, text: str) -> DocumentClassification:
        normalized = self._normalize(text)
        best_type = DocumentType.UNKNOWN
        best_score = 0
        best_signals: list[str] = []

        for document_type, (_, signals) in self._rules.items():
            score = 0
            matched: list[str] = []
            for signal, weight in signals:
                if self._normalize(signal) in normalized:
                    score += weight
                    matched.append(signal)

            if score > best_score:
                best_type = document_type
                best_score = score
                best_signals = matched

        if best_score < 7:
            return DocumentClassification(
                document_type=DocumentType.UNKNOWN,
                confidence=min(100.0, best_score * 8.0),
                language=self.detect_language(text),
                matched_signals=best_signals,
            )

        # Confidence is intentionally capped below 100 because this is a
        # heuristic classifier, not a legal/document authenticity decision.
        confidence = min(98.0, 55.0 + best_score * 4.0)

        return DocumentClassification(
            document_type=best_type,
            confidence=confidence,
            language=self.detect_language(text),
            matched_signals=best_signals,
        )

    @staticmethod
    def detect_language(text: str) -> str:
        if not text.strip():
            return "unknown"

        devanagari = len(re.findall(r"[\u0900-\u097F]", text))
        latin = len(re.findall(r"[A-Za-z]", text))
        total = devanagari + latin

        if total == 0:
            return "unknown"
        if devanagari / total >= 0.35 and latin / total >= 0.08:
            return "mar+eng"
        if devanagari / total >= 0.55:
            return "mar"
        if latin / total >= 0.55:
            return "eng"
        return "mar+eng"

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.casefold()
        text = text.replace("०", "0").replace("१", "1").replace("२", "2")
        text = text.replace("३", "3").replace("४", "4").replace("५", "5")
        text = text.replace("६", "6").replace("७", "7").replace("८", "8").replace("९", "9")
        return re.sub(r"\s+", " ", text).strip()
