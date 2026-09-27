from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any


@dataclass
class EntityRecord:
    """
    Lightweight normalized representation of an extracted land record.

    This layer deliberately does not make legal ownership/authenticity
    determinations. It only identifies records that may warrant review.
    """

    record_id: str
    document_id: str | None = None

    owner: str | None = None
    survey_number: str | None = None
    khata_number: str | None = None
    village: str | None = None
    taluka: str | None = None
    district: str | None = None
    area: str | None = None

    source_fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityMatch:
    record_a: str
    record_b: str
    score: float
    decision: str
    reasons: list[str]
    compared_fields: dict[str, float]
    source_document_a: str | None = None
    source_document_b: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_a": self.record_a,
            "record_b": self.record_b,
            "score": round(self.score, 4),
            "decision": self.decision,
            "reasons": self.reasons,
            "compared_fields": {
                k: round(v, 4) for k, v in self.compared_fields.items()
            },
            "source_document_a": self.source_document_a,
            "source_document_b": self.source_document_b,
        }


class EntityResolutionEngine:
    """
    Cross-document duplicate/entity resolution.

    This is intentionally separate from ConsistencyEngine:

    - ConsistencyEngine checks whether fields within a record/document
      agree with one another.
    - EntityResolutionEngine compares two or more records/documents.

    It produces review candidates rather than legal conclusions.
    """

    FIELD_WEIGHTS = {
        "owner": 0.30,
        "survey_number": 0.25,
        "khata_number": 0.15,
        "village": 0.12,
        "taluka": 0.06,
        "district": 0.04,
        "area": 0.08,
    }

    HIGH_THRESHOLD = 0.82
    REVIEW_THRESHOLD = 0.62

    @classmethod
    def normalize_text(cls, value: Any) -> str:
        if value is None:
            return ""

        text = unicodedata.normalize("NFKC", str(value))
        text = text.casefold()
        text = text.replace("।", ".")
        text = re.sub(r"[\u200b-\u200f\u202a-\u202e]", "", text)
        text = re.sub(r"[^\w\s./-]", " ", text, flags=re.UNICODE)
        text = re.sub(r"\s+", " ", text).strip()

        # Common record notation normalization.
        text = text.replace("gat", "survey")
        text = text.replace("गट", "survey")

        return text

    @classmethod
    def normalize_number(cls, value: Any) -> str:
        text = cls.normalize_text(value)
        if not text:
            return ""

        digits = re.sub(r"[^\d.]", "", text)
        return digits.rstrip(".")

    @classmethod
    def similarity(cls, left: Any, right: Any, numeric: bool = False) -> float:
        if numeric:
            a = cls.normalize_number(left)
            b = cls.normalize_number(right)
        else:
            a = cls.normalize_text(left)
            b = cls.normalize_text(right)

        if not a or not b:
            return 0.0

        if a == b:
            return 1.0

        return SequenceMatcher(None, a, b).ratio()

    @classmethod
    def compare(cls, left: EntityRecord, right: EntityRecord) -> EntityMatch:
        comparisons = {
            "owner": cls.similarity(left.owner, right.owner),
            "survey_number": cls.similarity(
                left.survey_number, right.survey_number, numeric=True
            ),
            "khata_number": cls.similarity(
                left.khata_number, right.khata_number, numeric=True
            ),
            "village": cls.similarity(left.village, right.village),
            "taluka": cls.similarity(left.taluka, right.taluka),
            "district": cls.similarity(left.district, right.district),
            "area": cls.similarity(left.area, right.area, numeric=True),
        }

        available = {
            key: value
            for key, value in comparisons.items()
            if cls._field_present(left, key) and cls._field_present(right, key)
        }

        if not available:
            return EntityMatch(
                record_a=left.record_id,
                record_b=right.record_id,
                score=0.0,
                decision="INSUFFICIENT_DATA",
                reasons=["No comparable normalized fields were available."],
                compared_fields={},
                source_document_a=left.document_id,
                source_document_b=right.document_id,
            )

        total_weight = sum(cls.FIELD_WEIGHTS[k] for k in available)
        score = (
            sum(cls.FIELD_WEIGHTS[k] * available[k] for k in available)
            / total_weight
        )

        reasons: list[str] = []

        if comparisons["owner"] >= 0.92:
            reasons.append("Owner names are highly similar.")

        if comparisons["survey_number"] == 1.0:
            reasons.append("Survey/Gat number matches exactly.")

        if comparisons["khata_number"] == 1.0:
            reasons.append("Khata number matches exactly.")

        if comparisons["village"] >= 0.92:
            reasons.append("Village names are highly similar.")

        if comparisons["area"] >= 0.95:
            reasons.append("Recorded area is highly similar.")

        if (
            comparisons["survey_number"] == 1.0
            and comparisons["village"] >= 0.90
        ):
            reasons.append(
                "The same survey/Gat number occurs in the same or highly "
                "similar village context."
            )

        if score >= cls.HIGH_THRESHOLD:
            decision = "POSSIBLE_DUPLICATE"
        elif score >= cls.REVIEW_THRESHOLD:
            decision = "POSSIBLE_MATCH"
        else:
            decision = "NO_MATCH"

        if not reasons and decision != "NO_MATCH":
            reasons.append("Multiple normalized record fields are similar.")

        return EntityMatch(
            record_a=left.record_id,
            record_b=right.record_id,
            score=score,
            decision=decision,
            reasons=reasons,
            compared_fields=comparisons,
            source_document_a=left.document_id,
            source_document_b=right.document_id,
        )

    @classmethod
    def compare_many(
        cls,
        records: list[EntityRecord],
        include_no_match: bool = False,
    ) -> list[EntityMatch]:
        results: list[EntityMatch] = []

        for index, left in enumerate(records):
            for right in records[index + 1 :]:
                match = cls.compare(left, right)

                if include_no_match or match.decision != "NO_MATCH":
                    results.append(match)

        results.sort(key=lambda item: item.score, reverse=True)
        return results

    @staticmethod
    def _field_present(record: EntityRecord, field_name: str) -> bool:
        return bool(getattr(record, field_name, None))


__all__ = [
    "EntityRecord",
    "EntityMatch",
    "EntityResolutionEngine",
]
