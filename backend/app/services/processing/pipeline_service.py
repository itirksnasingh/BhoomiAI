from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.documents import Document, DocumentPage, DocumentStatus
from app.models.extraction import ExtractedField, ExtractionRun, OCRRun, OCRRunStatus
from app.models.validation import ValidationResult, ValidationRun
from app.services.documents import DocumentStorageService
from app.services.extraction import ExtractionService
from app.services.ocr import OCRService
from app.services.processing.document_processor import process_document
from app.services.validation import ValidationService


class DocumentPipelineService:
    """Run the complete READ -> VERIFY pipeline for one document.

    The service deliberately reuses the existing OCR, extraction and
    validation services so Phase 6 is orchestration, not a second AI stack.
    Every stage persists its own lineage and evidence.
    """

    VERSION = "6.0"

    def run(self, db: Session, document_id: UUID, language: str = "mar+eng") -> dict:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document is None:
            raise ValueError("Document not found.")

        started = datetime.now(timezone.utc)
        document.status = DocumentStatus.PROCESSING
        db.flush()

        try:
            # Stage 1: ensure page images exist.
            storage = DocumentStorageService()
            pages = (
                db.query(DocumentPage)
                .filter(DocumentPage.document_id == document_id)
                .order_by(DocumentPage.page_number)
                .all()
            )

            rebuild = not pages
            if pages:
                for page in pages:
                    if not page.image_storage_key:
                        rebuild = True
                        break
                    try:
                        storage.storage.get_path(page.image_storage_key)
                    except FileNotFoundError:
                        rebuild = True
                        break

            if rebuild:
                source = (
                    db.query(storage.document_file_model)
                    .filter(storage.document_file_model.document_id == document_id)
                    .order_by(storage.document_file_model.created_at.desc())
                    .first()
                ) if hasattr(storage, "document_file_model") else None

                if source is None:
                    # Fall back to the model used by the existing API.
                    from app.models.documents import DocumentFile
                    source = (
                        db.query(DocumentFile)
                        .filter(DocumentFile.document_id == document_id)
                        .order_by(DocumentFile.created_at.desc())
                        .first()
                    )

                if source is None:
                    raise ValueError("No stored source file is available for this document.")

                db.query(DocumentPage).filter(
                    DocumentPage.document_id == document_id
                ).delete(synchronize_session=False)
                db.flush()
                process_document(
                    db=db,
                    document=document,
                    file_path=str(storage.get_document_file_path(source)),
                )

            # Stage 2: OCR + classification.
            ocr_runs = OCRService().process_document(
                db=db, document=document, language=language
            )
            db.flush()
            if not ocr_runs or not all(r.status == OCRRunStatus.COMPLETED for r in ocr_runs):
                raise ValueError("One or more document pages failed OCR.")
            db.commit()

            # Stage 3: document-type-aware extraction through the existing
            # production FieldExtractor/Phase-5 integration.
            fields = ExtractionService().extract_document_fields(
                db=db, document_id=document_id
            )
            db.commit()

            extraction_run = (
                db.query(ExtractionRun)
                .filter(ExtractionRun.document_id == document_id)
                .order_by(ExtractionRun.created_at.desc())
                .first()
            )
            if extraction_run is None:
                raise ValueError("Extraction completed without an extraction run.")

            # Stage 4: validation + cross-field consistency.
            validation_run, results = ValidationService().validate_document(
                db=db, document_id=document_id
            )

            statuses = {str(getattr(r.status, "value", r.status)).upper() for r in results}
            needs_review = bool(statuses & {"REVIEW", "WARNING", "FAIL", "FAILED"})
            document.status = (
                DocumentStatus.VALIDATION_REQUIRED if needs_review
                else DocumentStatus.PROCESSED
            )
            db.commit()

            elapsed = (datetime.now(timezone.utc) - started).total_seconds()

            return {
                "pipeline_version": self.VERSION,
                "document_id": str(document.id),
                "status": document.status.value,
                "document_type": getattr(document.document_type, "value", str(document.document_type)),
                "language": document.language,
                "pages": len(ocr_runs),
                "ocr_runs": len(ocr_runs),
                "fields_extracted": len(fields),
                "extraction_run_id": str(extraction_run.id),
                "validation_run_id": str(validation_run.id),
                "validation_results": len(results),
                "review_required": needs_review,
                "processing_seconds": round(elapsed, 3),
                "stages": {
                    "ingestion": "COMPLETED",
                    "preprocessing": "COMPLETED",
                    "ocr": "COMPLETED",
                    "classification": "COMPLETED",
                    "extraction": "COMPLETED",
                    "evidence": "COMPLETED",
                    "validation": "COMPLETED",
                },
            }

        except Exception:
            db.rollback()
            try:
                document = db.query(Document).filter(Document.id == document_id).first()
                if document is not None:
                    document.status = DocumentStatus.FAILED
                    db.commit()
            except Exception:
                db.rollback()
            raise
