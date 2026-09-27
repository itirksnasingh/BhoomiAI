from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.documents import DocumentPage
from app.models.extraction import (
    ExtractedField,
    ExtractionRun,
    ExtractionRunStatus,
    FieldEvidence,
    OCRBlock,
    OCRRun,
    OCRRunStatus,
)

from app.services.extraction.field_extractor import (
    FieldExtractor,
)


class ExtractionService:
    """
    Converts persisted OCR blocks into structured land-record fields.

    Every extraction execution creates an ExtractionRun so that the
    resulting fields can always be traced back to the OCR run that
    produced them.
    """

    def __init__(
        self,
        field_extractor: FieldExtractor | None = None,
    ):
        self.field_extractor = field_extractor or FieldExtractor()

    # ------------------------------------------------------------------
    # Extract fields from one page
    # ------------------------------------------------------------------

    def extract_page_fields(
        self,
        db: Session,
        page: DocumentPage,
        extraction_run: ExtractionRun,
    ) -> list[ExtractedField]:
        """
        Extract fields from the latest completed OCR run belonging
        to a document page.

        The fields are linked to both:
        - the current ExtractionRun
        - the source OCRRun
        """

        ocr_run = (
            db.query(OCRRun)
            .filter(
                OCRRun.document_page_id == page.id,
                OCRRun.status == OCRRunStatus.COMPLETED,
            )
            .order_by(
                OCRRun.created_at.desc()
            )
            .first()
        )

        if not ocr_run:
            raise ValueError(
                f"No completed OCR run found for page "
                f"{page.page_number}."
            )

        blocks = (
            db.query(OCRBlock)
            .filter(
                OCRBlock.ocr_run_id == ocr_run.id
            )
            .order_by(
                OCRBlock.block_number
            )
            .all()
        )

        if not blocks:
            return []

        results = self.field_extractor.extract(blocks)

        extracted_fields: list[ExtractedField] = []

        for result in results:

            field = ExtractedField(
                document_page_id=page.id,

                # Extraction lineage
                extraction_run_id=extraction_run.id,
                source_ocr_run_id=ocr_run.id,

                # Extracted information
                field_name=result.field_name,
                value=result.value,
                normalized_value=result.normalized_value,
                confidence=result.confidence,
                extraction_method=result.extraction_method,
                evidence_bbox=result.evidence_bbox,

                # Validation starts separately
                validation_status="PENDING",
            )

            db.add(field)
            db.flush()

            evidence = FieldEvidence(
                extracted_field_id=field.id,
                ocr_block_id=result.evidence_block_id,
                evidence_order=0,
            )

            db.add(evidence)

            extracted_fields.append(field)

        db.flush()

        return extracted_fields

    # ------------------------------------------------------------------
    # Extract fields from complete document
    # ------------------------------------------------------------------

    def extract_document_fields(
        self,
        db: Session,
        document_id: UUID,
    ) -> list[ExtractedField]:
        """
        Create a new ExtractionRun and extract fields from every
        processed page belonging to the document.

        The ExtractionRun remains RUNNING while pages are processed
        and is marked COMPLETED when the complete document succeeds.
        """

        pages = (
            db.query(DocumentPage)
            .filter(
                DocumentPage.document_id == document_id
            )
            .order_by(
                DocumentPage.page_number
            )
            .all()
        )

        if not pages:
            raise ValueError(
                "Document has no processed pages."
            )

        # --------------------------------------------------------------
        # Find a completed OCR run to use as the source lineage.
        #
        # Individual pages may have different OCR runs, so this field
        # is only populated when a source can be represented at the
        # document level. Individual ExtractedFields always store
        # their exact source_ocr_run_id.
        # --------------------------------------------------------------

        latest_ocr_run = (
            db.query(OCRRun)
            .join(
                DocumentPage,
                OCRRun.document_page_id == DocumentPage.id,
            )
            .filter(
                DocumentPage.document_id == document_id,
                OCRRun.status == OCRRunStatus.COMPLETED,
            )
            .order_by(
                OCRRun.created_at.desc()
            )
            .first()
        )

        if not latest_ocr_run:
            raise ValueError(
                "No completed OCR run found for document."
            )

        # --------------------------------------------------------------
        # Create extraction run
        # --------------------------------------------------------------

        extraction_run = ExtractionRun(
            document_id=document_id,
            source_ocr_run_id=latest_ocr_run.id,
            engine="deterministic+7/12-table-aware",
            engine_version="2.0",
            status=ExtractionRunStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )

        db.add(extraction_run)
        db.flush()

        extracted_fields: list[ExtractedField] = []

        try:

            for page in pages:

                fields = self.extract_page_fields(
                    db=db,
                    page=page,
                    extraction_run=extraction_run,
                )

                extracted_fields.extend(fields)

            # ----------------------------------------------------------
            # Calculate extraction confidence
            # ----------------------------------------------------------

            confidences = [
                field.confidence
                for field in extracted_fields
                if field.confidence is not None
            ]

            if confidences:
                extraction_run.confidence = (
                    sum(confidences) / len(confidences)
                )
            else:
                extraction_run.confidence = None

            extraction_run.status = (
                ExtractionRunStatus.COMPLETED
            )

            extraction_run.completed_at = (
                datetime.now(timezone.utc)
            )

            db.flush()

            return extracted_fields

        except Exception as exc:

            extraction_run.status = (
                ExtractionRunStatus.FAILED
            )

            extraction_run.error_message = str(exc)

            extraction_run.completed_at = (
                datetime.now(timezone.utc)
            )

            db.flush()

            raise