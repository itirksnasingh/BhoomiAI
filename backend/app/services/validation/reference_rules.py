from app.services.validation.base import ValidationResult, ValidationRule, ValidationStatus
from app.services.validation.reference_matcher import ReferenceMatcher


class VillageReferenceRule(ValidationRule):
    """Validate extracted village names against reference.villages."""

    def __init__(self, matcher: ReferenceMatcher):
        self.matcher = matcher

    def validate(self, field) -> ValidationResult | None:
        if field.field_name != "village":
            return None

        if not field.value:
            return None

        result = self.matcher.match_village(field.value)

        if result["status"] == "MATCHED":
            status = ValidationStatus.PASS
            confidence = 100.0

        elif result["status"] == "AMBIGUOUS":
            status = ValidationStatus.REVIEW
            confidence = 50.0

        else:
            status = ValidationStatus.REVIEW
            confidence = 0.0

        return ValidationResult(
            field_id=field.id,
            field_name=field.field_name,
            status=status,
            rule_name="village_reference_match",
            message=result["message"],
            confidence=confidence,
        )