import re

from app.models.extraction import ExtractedField

from app.services.validation.base import (
    ValidationResult,
    ValidationRule,
    ValidationStatus,
)

from app.services.validation.hierarchy_rules import (
    LocationHierarchyRule,
)


class RequiredValueRule(ValidationRule):
    """
    Checks whether a required field contains a value.
    """

    REQUIRED_FIELDS = {
        "survey_number",
        "village",
    }

    def validate(
        self,
        field: ExtractedField,
    ) -> ValidationResult | None:

        if field.field_name not in self.REQUIRED_FIELDS:
            return None

        if field.value and field.value.strip():
            return ValidationResult(
                field_id=field.id,
                field_name=field.field_name,
                status=ValidationStatus.PASS,
                rule_name="required_value",
                message="Required field contains a value.",
                confidence=field.confidence,
            )

        return ValidationResult(
            field_id=field.id,
            field_name=field.field_name,
            status=ValidationStatus.REVIEW,
            rule_name="required_value",
            message="Required field is empty and requires review.",
            confidence=field.confidence,
        )


class SurveyNumberFormatRule(ValidationRule):
    """
    Checks whether a survey number follows a plausible
    Maharashtra-style numeric/subdivision pattern.

    Examples:

        124
        124/3
        124/3/1
    """

    PATTERN = re.compile(
        r"^\d+(?:/\d+)*$"
    )

    def validate(
        self,
        field: ExtractedField,
    ) -> ValidationResult | None:

        if field.field_name != "survey_number":
            return None

        value = (
            field.normalized_value
            or field.value
            or ""
        ).strip()

        if not value:
            return ValidationResult(
                field_id=field.id,
                field_name=field.field_name,
                status=ValidationStatus.REVIEW,
                rule_name="survey_number_format",
                message="Survey number is empty.",
                confidence=field.confidence,
            )

        if self.PATTERN.fullmatch(value):
            return ValidationResult(
                field_id=field.id,
                field_name=field.field_name,
                status=ValidationStatus.PASS,
                rule_name="survey_number_format",
                message=(
                    "Survey number matches the expected "
                    "numeric format."
                ),
                confidence=field.confidence,
            )

        return ValidationResult(
            field_id=field.id,
            field_name=field.field_name,
            status=ValidationStatus.REVIEW,
            rule_name="survey_number_format",
            message=(
                "Survey number does not match the expected "
                "numeric/subdivision format."
            ),
            confidence=field.confidence,
        )


class SevenTwelveFieldSanityRule(ValidationRule):
    """Sanity checks for fields produced by the 7/12 table extractor."""

    NUMERIC_FIELDS = {"subdivision", "khata_number"}
    TEXT_FIELDS = {"land_tenure", "local_field_name", "owner"}

    def validate(self, field: ExtractedField) -> ValidationResult | None:
        if field.field_name in self.NUMERIC_FIELDS:
            value = (field.normalized_value or field.value or "").strip()
            if value == "-" or re.fullmatch(r"\d+(?:/\d+)*", value):
                return ValidationResult(
                    field_id=field.id,
                    field_name=field.field_name,
                    status=ValidationStatus.PASS,
                    rule_name="seven_twelve_numeric_format",
                    message="7/12 numeric field matches the expected format.",
                    confidence=field.confidence,
                )
            return ValidationResult(
                field_id=field.id,
                field_name=field.field_name,
                status=ValidationStatus.REVIEW,
                rule_name="seven_twelve_numeric_format",
                message="7/12 numeric field has an unexpected format and requires review.",
                confidence=field.confidence,
            )

        if field.field_name == "area":
            value = (field.normalized_value or field.value or "").strip()
            try:
                if float(value.replace(",", ".")) > 0:
                    return ValidationResult(
                        field_id=field.id,
                        field_name=field.field_name,
                        status=ValidationStatus.PASS,
                        rule_name="seven_twelve_area_format",
                        message="Area value is a positive numeric value.",
                        confidence=field.confidence,
                    )
            except ValueError:
                pass
            return ValidationResult(
                field_id=field.id,
                field_name=field.field_name,
                status=ValidationStatus.REVIEW,
                rule_name="seven_twelve_area_format",
                message="Area value is not a positive numeric value.",
                confidence=field.confidence,
            )

        if field.field_name in self.TEXT_FIELDS:
            value = (field.normalized_value or field.value or "").strip()
            generic = {
                "क्रमांक", "नाव", "वर्ग", "क्षेत्र", "क्षेत्रफळ", "माहिती",
                "name", "number", "no", "type", "details", "information",
            }
            if value.casefold() in generic or len(value) < 2:
                return ValidationResult(
                    field_id=field.id,
                    field_name=field.field_name,
                    status=ValidationStatus.REVIEW,
                    rule_name="seven_twelve_text_value",
                    message="7/12 text field resembles a header/label rather than a value.",
                    confidence=min(float(field.confidence or 0.0), 35.0),
                )
            return ValidationResult(
                field_id=field.id,
                field_name=field.field_name,
                status=ValidationStatus.PASS,
                rule_name="seven_twelve_text_value",
                message="7/12 text field contains a non-empty candidate value.",
                confidence=field.confidence,
            )

        return None


class ConfidenceThresholdRule(ValidationRule):
    """
    Flags fields with low OCR/extraction confidence.

    This is deliberately separate from correctness.

    A high-confidence OCR result can still be wrong.
    """

    REVIEW_THRESHOLD = 50.0
    WARNING_THRESHOLD = 75.0

    def validate(
        self,
        field: ExtractedField,
    ) -> ValidationResult | None:

        if field.confidence is None:
            return ValidationResult(
                field_id=field.id,
                field_name=field.field_name,
                status=ValidationStatus.REVIEW,
                rule_name="confidence_threshold",
                message="No extraction confidence is available.",
                confidence=None,
            )

        if field.confidence < self.REVIEW_THRESHOLD:
            return ValidationResult(
                field_id=field.id,
                field_name=field.field_name,
                status=ValidationStatus.REVIEW,
                rule_name="confidence_threshold",
                message=(
                    f"Extraction confidence is low "
                    f"({field.confidence:.2f}%). "
                    "Human review is recommended."
                ),
                confidence=field.confidence,
            )

        if field.confidence < self.WARNING_THRESHOLD:
            return ValidationResult(
                field_id=field.id,
                field_name=field.field_name,
                status=ValidationStatus.WARNING,
                rule_name="confidence_threshold",
                message=(
                    f"Extraction confidence is moderate "
                    f"({field.confidence:.2f}%)."
                ),
                confidence=field.confidence,
            )

        return ValidationResult(
            field_id=field.id,
            field_name=field.field_name,
            status=ValidationStatus.PASS,
            rule_name="confidence_threshold",
            message=(
                f"Extraction confidence is high "
                f"({field.confidence:.2f}%)."
            ),
            confidence=field.confidence,
        )


class FieldRuleSet:
    """
    Collection of deterministic validation rules.

    Base rules:
        1. Required field validation
        2. Survey number format validation
        3. OCR/extraction confidence validation

    Reference rules are added when a ReferenceMatcher
    is supplied.
    """

    def __init__(
        self,
        reference_matcher=None,
    ):
        self.rules: list[ValidationRule] = [
            RequiredValueRule(),
            SurveyNumberFormatRule(),
            SevenTwelveFieldSanityRule(),
            ConfidenceThresholdRule(),
        ]

        # ----------------------------------------------------
        # Reference-data validation
        # ----------------------------------------------------

        if reference_matcher is not None:

            from app.services.validation.reference_rules import (
                VillageReferenceRule,
            )

            # Check whether village exists in the reference data.
            self.rules.append(
                VillageReferenceRule(
                    reference_matcher
                )
            )

            # Check the resolved village's location hierarchy.
            self.rules.append(
                LocationHierarchyRule(
                    reference_matcher
                )
            )

    def validate(
        self,
        field: ExtractedField,
    ) -> list[ValidationResult]:

        results: list[ValidationResult] = []

        for rule in self.rules:

            result = rule.validate(
                field
            )

            if result is not None:
                results.append(
                    result
                )

        return results