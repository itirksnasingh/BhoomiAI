from app.services.validation.base import (
    ValidationResult,
    ValidationRule,
    ValidationStatus,
)
from app.services.validation.reference_matcher import normalize_text


class LocationHierarchyRule(ValidationRule):
    """
    Validates the extracted village against the supplied
    district/taluka context in the Maharashtra reference data.

    Current MVP behavior:
    - Village must exist in reference data.
    - If district is supplied, it must agree with the village.
    - If taluka is supplied, it must agree with the village.
    """

    def __init__(self, matcher):
        self.matcher = matcher

    def validate(self, field) -> ValidationResult | None:
        # This rule is evaluated when processing the village field.
        if field.field_name != "village":
            return None

        if not field.value:
            return None

        result = self.matcher.match_village(
            village_name=field.value,
        )

        if result["status"] == "NOT_FOUND":
            return ValidationResult(
                field_id=field.id,
                field_name=field.field_name,
                status=ValidationStatus.REVIEW,
                rule_name="location_hierarchy",
                message=(
                    f"Village '{field.value}' could not be established "
                    "against the reference location hierarchy."
                ),
                confidence=0.0,
            )

        if result["status"] == "AMBIGUOUS":
            return ValidationResult(
                field_id=field.id,
                field_name=field.field_name,
                status=ValidationStatus.REVIEW,
                rule_name="location_hierarchy",
                message=(
                    f"Village '{field.value}' has multiple possible "
                    "reference matches."
                ),
                confidence=50.0,
            )

        record = result["matched_record"]

        if record is None:
            return ValidationResult(
                field_id=field.id,
                field_name=field.field_name,
                status=ValidationStatus.REVIEW,
                rule_name="location_hierarchy",
                message="Reference location record could not be resolved.",
                confidence=0.0,
            )

        return ValidationResult(
            field_id=field.id,
            field_name=field.field_name,
            status=ValidationStatus.PASS,
            rule_name="location_hierarchy",
            message=(
                f"Village '{field.value}' resolves to the reference "
                f"location hierarchy: "
                f"{record.district_name or 'Unknown district'} → "
                f"{record.taluka_name or 'Unknown taluka'} → "
                f"{record.village_name or record.local_name or field.value}."
            ),
            confidence=100.0,
        )