from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.documents import Document, DocumentPage, DocumentStatus
from app.models.extraction import OCRBlock, OCRRun, OCRRunStatus
from app.services.ocr.document_classifier import LandDocumentClassifier
from app.services.ocr.tesseract import TesseractOCRProvider
from app.services.storage import LocalStorage


class OCRService:
    """Run OCR, persist evidence, and classify the document from its OCR text."""

    def __init__(
        self,
        provider: TesseractOCRProvider | None = None,
        storage: LocalStorage | None = None,
        classifier: LandDocumentClassifier | None = None,
    ):
        self.provider = provider or TesseractOCRProvider()
        self.storage = storage or LocalStorage()
        self.classifier = classifier or LandDocumentClassifier()

    def process_document(
        self,
        db: Session,
        document: Document,
        language: str = "mar+eng",
    ) -> list[OCRRun]:
        pages = (
            db.query(DocumentPage)
            .filter(DocumentPage.document_id == document.id)
            .order_by(DocumentPage.page_number)
            .all()
        )
        if not pages:
            raise ValueError("Document has no processed pages.")

        document.status = DocumentStatus.PROCESSING
        db.flush()

        ocr_runs: list[OCRRun] = []
        all_text: list[str] = []

        for page in pages:
            ocr_run = self._process_page(db, page, language)
            ocr_runs.append(ocr_run)

            if ocr_run.status == OCRRunStatus.COMPLETED:
                blocks = (
                    db.query(OCRBlock)
                    .filter(OCRBlock.ocr_run_id == ocr_run.id)
                    .order_by(OCRBlock.block_number)
                    .all()
                )
                all_text.extend(block.text for block in blocks if block.text)

        if all(run.status == OCRRunStatus.COMPLETED for run in ocr_runs):
            classification = self.classifier.classify("\n".join(all_text))
            document.document_type = classification.document_type
            document.language = classification.language
            document.status = DocumentStatus.PROCESSED
        else:
            document.status = DocumentStatus.FAILED

        db.flush()
        return ocr_runs

    def _process_page(self, db: Session, page: DocumentPage, language: str) -> OCRRun:
        if not page.image_storage_key:
            raise ValueError(
                f"Page {page.page_number} does not have a stored page image."
            )

        ocr_run = OCRRun(
            document_page_id=page.id,
            engine="tesseract",
            language=language,
            status=OCRRunStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        db.add(ocr_run)
        db.flush()

        try:
            image_path = self.storage.get_path(page.image_storage_key)
            result = self.provider.process(str(image_path), language=language)

            ocr_run.engine = result.engine
            ocr_run.engine_version = result.engine_version
            ocr_run.language = result.language
            ocr_run.confidence = result.confidence
            ocr_run.status = OCRRunStatus.COMPLETED
            ocr_run.completed_at = datetime.now(timezone.utc)

            for block_number, block_result in enumerate(result.blocks, start=1):
                db.add(
                    OCRBlock(
                        ocr_run_id=ocr_run.id,
                        block_number=block_number,
                        text=block_result.text,
                        confidence=block_result.confidence,
                        bbox=block_result.bbox,
                        language=block_result.language,
                    )
                )

            db.flush()
            return ocr_run

        except Exception as exc:
            ocr_run.status = OCRRunStatus.FAILED
            ocr_run.error_message = str(exc)
            ocr_run.completed_at = datetime.now(timezone.utc)
            db.flush()
            return ocr_run
