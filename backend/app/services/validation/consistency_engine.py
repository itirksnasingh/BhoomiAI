from __future__ import annotations

import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Iterable

from app.models.extraction import ExtractedField
from app.services.validation.base import ValidationResult, ValidationStatus


class ConsistencyEngine:
    """Document-level land-record consistency engine.

    The engine compares independently extracted values within one extraction
    run. It is intentionally explainable and deterministic. It does not make
    legal ownership/authenticity determinations.
    """

    # Only fields that are expected to be single-valued within a document
    # participate in duplicate-value conflict detection. Owner, area,
    # classification, mutation and registration are intentionally multi-valued
    # in real land records and must not be flagged merely because more than one
    # legitimate row exists. Survey/Gat identifiers may also legitimately occur
    # in more than one form on a 7/12, so they are not treated as duplicates here.
    CONFLICT_FIELDS = {
        "village",
        "taluka",
        "district",
        "khata_number",
    }

    def __init__(self, reference_matcher=None):
        self.reference_matcher = reference_matcher

    def analyze(self, fields: list[ExtractedField]) -> list[ValidationResult]:
        grouped: dict[str, list[ExtractedField]] = {}
        for field in fields:
            grouped.setdefault(field.field_name, []).append(field)

        results: list[ValidationResult] = []
        results.extend(self._duplicate_consistency(grouped))
        results.extend(self._area_checks(grouped))
        results.extend(self._date_relationship(grouped))
        results.extend(self._location_consistency(grouped))
        return self._deduplicate_results(results)

    def _duplicate_consistency(self, grouped: dict[str, list[ExtractedField]]) -> list[ValidationResult]:
        results: list[ValidationResult] = []

        for field_name, candidates in grouped.items():
            if field_name not in self.CONFLICT_FIELDS or len(candidates) < 2:
                continue

            usable = [field for field in candidates if self._value(field)]
            if len(usable) < 2:
                continue

            clusters: list[list[ExtractedField]] = []
            for candidate in usable:
                placed = False
                candidate_value = self._normalized(self._value(candidate))
                for cluster in clusters:
                    representative = self._normalized(self._value(cluster[0]))
                    if self._equivalent(field_name, candidate_value, representative):
                        cluster.append(candidate)
                        placed = True
                        break
                if not placed:
                    clusters.append([candidate])

            if len(clusters) == 1:
                representative = clusters[0][0]
                results.append(
                    ValidationResult(
                        field_id=representative.id,
                        field_name=field_name,
                        status=ValidationStatus.PASS,
                        rule_name=f"consistency_{field_name}_duplicates",
                        message=(
                            f"All {len(usable)} extracted {field_name.replace('_', ' ')} "
                            "values are consistent."
                        ),
                        confidence=self._cluster_confidence(clusters[0]),
                    )
                )
                continue

            rendered = []
            for cluster in clusters:
                value = self._value(cluster[0])
                count = len(cluster)
                rendered.append(f"{value} ({count} occurrence{'s' if count != 1 else ''})")
            message = (
                f"Conflicting {field_name.replace('_', ' ')} values were extracted: "
                + "; ".join(rendered)
                + ". Human review is required to determine the correct value."
            )

            for cluster in clusters:
                representative = cluster[0]
                results.append(
                    ValidationResult(
                        field_id=representative.id,
                        field_name=field_name,
                        status=ValidationStatus.REVIEW,
                        rule_name=f"consistency_{field_name}_conflict",
                        message=message,
                        confidence=self._cluster_confidence(cluster),
                    )
                )

        return results

    def _area_checks(self, grouped: dict[str, list[ExtractedField]]) -> list[ValidationResult]:
        results: list[ValidationResult] = []
        for field in grouped.get("area", []):
            value = self._number(self._value(field))
            if value is None:
                results.append(
                    ValidationResult(
                        field_id=field.id,
                        field_name="area",
                        status=ValidationStatus.REVIEW,
                        rule_name="consistency_area_numeric",
                        message="Area could not be interpreted as a numeric value.",
                        confidence=field.confidence,
                    )
                )
            elif value <= 0:
                results.append(
                    ValidationResult(
                        field_id=field.id,
                        field_name="area",
                        status=ValidationStatus.REVIEW,
                        rule_name="consistency_area_positive",
                        message=f"Area value {value:g} is not positive.",
                        confidence=field.confidence,
                    )
                )
            else:
                results.append(
                    ValidationResult(
                        field_id=field.id,
                        field_name="area",
                        status=ValidationStatus.PASS,
                        rule_name="consistency_area_positive",
                        message=f"Area value {value:g} is positive and numerically valid.",
                        confidence=field.confidence,
                    )
                )
        return results

    def _date_relationship(self, grouped: dict[str, list[ExtractedField]]) -> list[ValidationResult]:
        registrations = [f for f in grouped.get("registration", []) if self._value(f)]
        mutations = [f for f in grouped.get("mutation", []) if self._value(f)]
        if not registrations or not mutations:
            return []

        registration_date = self._extract_date(self._value(registrations[0]))
        mutation_date = self._extract_date(self._value(mutations[0]))
        if not registration_date or not mutation_date:
            return []

        field = mutations[0]
        if mutation_date < registration_date:
            return [
                ValidationResult(
                    field_id=field.id,
                    field_name="mutation",
                    status=ValidationStatus.REVIEW,
                    rule_name="consistency_mutation_registration_date",
                    message=(
                        f"Mutation date {mutation_date:%d/%m/%Y} occurs before registration date "
                        f"{registration_date:%d/%m/%Y}. Review the source record."
                    ),
                    confidence=field.confidence,
                )
            ]

        return [
            ValidationResult(
                field_id=field.id,
                field_name="mutation",
                status=ValidationStatus.PASS,
                rule_name="consistency_mutation_registration_date",
                message="Mutation date is on or after the registration date.",
                confidence=field.confidence,
            )
        ]

    def _location_consistency(self, grouped: dict[str, list[ExtractedField]]) -> list[ValidationResult]:
        """Compare village/taluka/district with the reference hierarchy when configured."""
        if self.reference_matcher is None:
            return []

        village = self._first_value(grouped.get("village", []))
        if not village:
            return []

        taluka = self._first_value(grouped.get("taluka", []))
        district = self._first_value(grouped.get("district", []))
        village_field = self._first_field(grouped.get("village", []))
        if village_field is None:
            return []

        try:
            match = self.reference_matcher.match_village(
                village_name=village,
                taluka_name=taluka,
                district_name=district,
            )
        except Exception as exc:
            return [
                ValidationResult(
                    field_id=village_field.id,
                    field_name="village",
                    status=ValidationStatus.WARNING,
                    rule_name="consistency_reference_lookup",
                    message=f"Reference hierarchy lookup was unavailable: {exc}",
                    confidence=0.0,
                )
            ]

        if match.get("status") != "MATCHED":
            return [
                ValidationResult(
                    field_id=village_field.id,
                    field_name="village",
                    status=ValidationStatus.REVIEW,
                    rule_name="consistency_reference_location",
                    message=match.get("message") or "Village could not be resolved against reference data.",
                    confidence=50.0 if match.get("status") == "AMBIGUOUS" else 0.0,
                )
            ]

        record = match.get("matched_record")
        if record is None:
            return []

        results: list[ValidationResult] = []
        expected_taluka = self._normalize_text(getattr(record, "taluka_name", None))
        expected_district = self._normalize_text(getattr(record, "district_name", None))

        for field_name, actual, expected in (
            ("taluka", taluka, expected_taluka),
            ("district", district, expected_district),
        ):
            if not actual or not expected:
                continue
            field = self._first_field(grouped.get(field_name, [])) or village_field
            if self._normalize_text(actual) == expected:
                results.append(
                    ValidationResult(
                        field_id=field.id,
                        field_name=field_name,
                        status=ValidationStatus.PASS,
                        rule_name=f"consistency_{field_name}_reference",
                        message=f"{field_name.title()} is consistent with the reference village hierarchy.",
                        confidence=100.0,
                    )
                )
            else:
                results.append(
                    ValidationResult(
                        field_id=field.id,
                        field_name=field_name,
                        status=ValidationStatus.REVIEW,
                        rule_name=f"consistency_{field_name}_reference_conflict",
                        message=(
                            f"Extracted {field_name} '{actual}' does not match the reference hierarchy "
                            f"value '{getattr(record, field_name + '_name', expected)}' for village '{village}'."
                        ),
                        confidence=0.0,
                    )
                )

        return results

    @staticmethod
    def _first_field(fields: Iterable[ExtractedField] | None) -> ExtractedField | None:
        if not fields:
            return None
        return next(iter(fields), None)

    @classmethod
    def _first_value(cls, fields: Iterable[ExtractedField] | None) -> str | None:
        if not fields:
            return None
        for field in fields:
            value = cls._value(field)
            if value:
                return value
        return None

    @staticmethod
    def _value(field: ExtractedField) -> str:
        return (field.value or field.normalized_value or "").strip()

    @staticmethod
    def _normalized(value: str) -> str:
        text = value.casefold().strip()
        text = text.translate(str.maketrans("०१२३४५६७८९", "0123456789"))
        text = re.sub(r"[\s,;:]+", " ", text)
        return text.strip()

    @staticmethod
    def _normalize_text(value: str | None) -> str | None:
        if not value:
            return None
        value = value.casefold().strip()
        value = value.translate(str.maketrans("०१२३४५६७८९", "0123456789"))
        value = re.sub(r"[.,;:()\[\]{}]", "", value)
        value = re.sub(r"\s+", " ", value)
        return value

    @classmethod
    def _equivalent(cls, field_name: str, a: str, b: str) -> bool:
        if a == b:
            return True
        if field_name in {"survey_number", "khata_number", "area"}:
            return re.sub(r"\s+", "", a) == re.sub(r"\s+", "", b)
        if field_name in {"village", "taluka", "district", "owner", "classification"}:
            return cls._similarity(a, b) >= 0.92
        return False

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()

    @classmethod
    def _number(cls, value: str) -> float | None:
        if not value:
            return None
        value = value.translate(str.maketrans("०१२३४५६७८९", "0123456789"))
        match = re.search(r"\d+(?:[.,]\d+)?", value)
        if not match:
            return None
        try:
            return float(match.group(0).replace(",", "."))
        except ValueError:
            return None

    @staticmethod
    def _extract_date(value: str) -> datetime | None:
        if not value:
            return None
        for pattern in (
            r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})",
            r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})",
        ):
            match = re.search(pattern, value)
            if not match:
                continue
            try:
                if len(match.group(1)) == 4:
                    return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                return datetime(int(match.group(3)), int(match.group(2)), int(match.group(1)))
            except ValueError:
                return None
        return None

    @staticmethod
    def _cluster_confidence(cluster: list[ExtractedField]) -> float | None:
        values = [f.confidence for f in cluster if f.confidence is not None]
        return sum(values) / len(values) if values else None

    @staticmethod
    def _deduplicate_results(results: list[ValidationResult]) -> list[ValidationResult]:
        seen: set[tuple] = set()
        unique: list[ValidationResult] = []
        for result in results:
            key = (result.field_id, result.rule_name, result.status.value, result.message)
            if key not in seen:
                seen.add(key)
                unique.append(result)
        return unique
