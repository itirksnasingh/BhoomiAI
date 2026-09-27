from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.documents import DocumentPage
from app.models.extraction import ExtractedField, ExtractionRun, ExtractionRunStatus
from app.models.validation import (
    ValidationResult as ValidationResultModel,
    ValidationRun,
    ValidationRunStatus,
)
from app.services.validation.base import ValidationResult, ValidationStatus
from app.services.validation.consistency_engine import ConsistencyEngine
from app.services.validation.reference_matcher import ReferenceMatcher
from app.services.validation.rules import FieldRuleSet


class ValidationService:
    """Run field rules and document-level consistency checks together."""

    ENGINE = "deterministic+consistency"
    ENGINE_VERSION = "2.3"

    def __init__(self, rule_set: FieldRuleSet | None = None):
        self.rule_set = rule_set

    def validate_field(
        self,
        field: ExtractedField,
        rule_set: FieldRuleSet | None = None,
    ) -> list[ValidationResult]:
        active_rule_set = rule_set or self.rule_set or FieldRuleSet()
        return active_rule_set.validate(field)

    def validate_document(
        self,
        db: Session,
        document_id,
    ) -> tuple[ValidationRun, list[ValidationResult]]:
        source_extraction_run = (
            db.query(ExtractionRun)
            .filter(
                ExtractionRun.document_id == document_id,
                ExtractionRun.status == ExtractionRunStatus.COMPLETED,
            )
            .order_by(ExtractionRun.created_at.desc())
            .first()
        )
        if source_extraction_run is None:
            raise ValueError(
                "No completed extraction run found for this document. "
                "Run extraction before validation."
            )

        fields = (
            db.query(ExtractedField)
            .join(DocumentPage, ExtractedField.document_page_id == DocumentPage.id)
            .filter(
                DocumentPage.document_id == document_id,
                ExtractedField.extraction_run_id == source_extraction_run.id,
            )
            .order_by(ExtractedField.created_at)
            .all()
        )
        if not fields:
            raise ValueError(
                "No extracted fields found for the latest completed extraction run."
            )

        reference_matcher = ReferenceMatcher(db)
        rule_set = self.rule_set or FieldRuleSet(reference_matcher=reference_matcher)
        consistency_engine = ConsistencyEngine(reference_matcher=reference_matcher)

        validation_run = ValidationRun(
            document_id=document_id,
            extraction_run_id=source_extraction_run.id,
            engine=self.ENGINE,
            engine_version=self.ENGINE_VERSION,
            status=ValidationRunStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        db.add(validation_run)
        db.flush()

        results: list[ValidationResult] = []

        try:
            field_statuses: dict = {field.id: "PASS" for field in fields}

            # 1. Existing deterministic field rules plus explicit OCR/header
            # suspicion checks. Suspicious extracted labels must never silently
            # pass merely because the OCR engine itself reported high confidence.
            for field in fields:
                field_results = self.validate_field(field, rule_set=rule_set)
                suspicious_result = self._suspicious_field_result(field)
                if suspicious_result is not None:
                    field_results.append(suspicious_result)
                results.extend(field_results)
                self._persist_results(db, validation_run, field_results)
                self._apply_status(field_statuses, field.id, field_results)

            # 2. Cross-field/document consistency.
            consistency_results = consistency_engine.analyze(fields)
            results.extend(consistency_results)
            self._persist_results(db, validation_run, consistency_results)
            for result in consistency_results:
                self._apply_status(field_statuses, result.field_id, [result])

            # 3. Apply the strongest status to every affected field.
            for field in fields:
                field.validation_status = field_statuses.get(field.id, "PASS")

            confidences = [
                result.confidence
                for result in results
                if result.confidence is not None
            ]
            validation_run.confidence = (
                sum(confidences) / len(confidences) if confidences else None
            )
            validation_run.status = ValidationRunStatus.COMPLETED
            validation_run.completed_at = datetime.now(timezone.utc)
            db.flush()

            return validation_run, results

        except Exception as exc:
            validation_run.status = ValidationRunStatus.FAILED
            validation_run.error_message = str(exc)
            validation_run.completed_at = datetime.now(timezone.utc)
            db.flush()
            raise


    @classmethod
    def _suspicious_field_result(cls, field: ExtractedField) -> ValidationResult | None:
        """Route obvious OCR/table-header captures to human review."""
        value = (field.value or field.normalized_value or "").strip().casefold()
        compact = " ".join(value.split())
        method = (field.extraction_method or "").casefold()

        generic_headers = {
            "नोंदणी माहिती",
            "फेरफार माहिती",
            "दिनांक",
            "हक्काचा प्रकार",
            "क्षेत्रफळ",
            "क्षेत्र",
            "क्रमांक",
            "गटक्रमांक",
            "गटक्रमांक क्रमांक",
            "name",
            "number",
            "no",
            "type",
            "information",
            "details",
        }

        is_header = compact in generic_headers
        is_label_like = method.endswith("_suspect")

        # Mutation/registration often have a table header followed by a date
        # column. A bare header is not a trustworthy extracted value.
        if field.field_name in {"mutation", "registration"} and (
            is_header
            or compact in {"mutation", "ferfar", "registration", "नोंदणी", "फेरफार"}
        ):
            is_header = True

        if not is_header and not is_label_like:
            return None

        return ValidationResult(
            field_id=field.id,
            field_name=field.field_name,
            status=ValidationStatus.REVIEW,
            rule_name="field_value_suspicious",
            message=(
                f"Extracted value '{field.value}' appears to be a document/table header or label rather than a field value. "
                "Human review is required before it can be trusted."
            ),
            confidence=min(float(field.confidence or 0.0), 25.0),
        )

    @staticmethod
    def _apply_status(statuses: dict, field_id, results: list[ValidationResult]) -> None:
        rank = {
            "PASS": 0,
            "WARNING": 1,
            "REVIEW": 2,
        }
        current = statuses.get(field_id, "PASS")
        for result in results:
            value = result.status.value
            if rank.get(value, 0) > rank.get(current, 0):
                statuses[field_id] = value

    @staticmethod
    def _persist_results(
        db: Session,
        validation_run: ValidationRun,
        results: list[ValidationResult],
    ) -> None:
        for result in results:
            db.add(
                ValidationResultModel(
                    validation_run_id=validation_run.id,
                    extracted_field_id=result.field_id,
                    rule_name=result.rule_name,
                    status=result.status,
                    message=result.message,
                    confidence=result.confidence,
                )
            )
