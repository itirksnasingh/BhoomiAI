from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConfidenceBand(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    CONFLICT = "CONFLICT"


@dataclass
class ConfidenceInput:
    extraction_confidence: float | None = None
    ocr_confidence: float | None = None
    validation_status: str | None = None
    entity_match_score: float | None = None
    has_conflict: bool = False
    requires_review: bool = False


@dataclass
class ConfidenceResult:
    score: float
    band: ConfidenceBand
    automation_allowed: bool
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "band": self.band.value,
            "automation_allowed": self.automation_allowed,
            "reasons": self.reasons,
        }


class ConfidenceCalibrationEngine:
    """
    Conservative confidence calibration for BhoomiAI.

    This does not claim statistical probability of correctness.
    It produces an operational confidence score used to decide
    whether a result can safely proceed automatically or should
    receive human review.
    """

    HIGH_THRESHOLD = 0.85
    MEDIUM_THRESHOLD = 0.65

    @staticmethod
    def _clamp(value: float | None) -> float | None:
        if value is None:
            return None

        value = float(value)

        # Accept both [0,1] and percentage [0,100] inputs.
        if value > 1.0:
            value /= 100.0

        return max(0.0, min(1.0, value))

    @classmethod
    def calibrate(cls, data: ConfidenceInput) -> ConfidenceResult:
        extraction = cls._clamp(data.extraction_confidence)
        ocr = cls._clamp(data.ocr_confidence)
        entity = cls._clamp(data.entity_match_score)

        components: list[float] = []
        weights: list[float] = []
        reasons: list[str] = []

        if extraction is not None:
            components.append(extraction)
            weights.append(0.45)

            if extraction < 0.65:
                reasons.append("Extraction confidence is low.")

        if ocr is not None:
            components.append(ocr)
            weights.append(0.25)

            if ocr < 0.65:
                reasons.append("OCR confidence is low.")

        if entity is not None:
            components.append(entity)
            weights.append(0.20)

            if entity >= 0.85:
                reasons.append("Cross-record similarity is high.")
            elif entity >= 0.62:
                reasons.append("Cross-record similarity warrants review.")

        # Base confidence from available quantitative signals.
        if components:
            score = sum(
                value * weight
                for value, weight in zip(components, weights)
            ) / sum(weights)
        else:
            score = 0.0
            reasons.append("No quantitative confidence signal was available.")

        status = (data.validation_status or "").upper()

        if status in {"PASS", "VALID", "APPROVED"}:
            score += 0.10
            reasons.append("Validation status is positive.")

        elif status in {"WARNING", "WARN"}:
            score -= 0.10
            reasons.append("Validation produced a warning.")

        elif status in {"REVIEW", "FAILED", "FAIL", "INVALID"}:
            score -= 0.25
            reasons.append("Validation requires human review.")

        if data.has_conflict:
            score -= 0.35
            reasons.append("A cross-record or field conflict was detected.")

        if data.requires_review:
            score -= 0.20
            reasons.append("The record is already marked for human review.")

        score = max(0.0, min(1.0, score))

        # Conservative operational policy:
        # conflicts/review flags can never become auto-approved.
        if data.has_conflict or data.requires_review:
            band = ConfidenceBand.CONFLICT
            automation_allowed = False

        elif score >= cls.HIGH_THRESHOLD:
            band = ConfidenceBand.HIGH
            automation_allowed = True

        elif score >= cls.MEDIUM_THRESHOLD:
            band = ConfidenceBand.MEDIUM
            automation_allowed = False
            reasons.append("Manual review is recommended before automation.")

        else:
            band = ConfidenceBand.LOW
            automation_allowed = False
            reasons.append("Human review is required.")

        return ConfidenceResult(
            score=score,
            band=band,
            automation_allowed=automation_allowed,
            reasons=reasons,
        )


__all__ = [
    "ConfidenceBand",
    "ConfidenceInput",
    "ConfidenceResult",
    "ConfidenceCalibrationEngine",
]
