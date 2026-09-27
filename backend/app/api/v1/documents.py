import hashlib
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from fastapi.responses import FileResponse
from app.core.auth import get_current_user, require_role
from app.db.session import get_db

from app.models.auth import User, UserRole

from app.models.documents import (
    Document,
    DocumentFile,
    DocumentPage,
)

from app.models.extraction import (
    ExtractedField,
    ExtractionRun,
)

from app.models.validation import (
    ValidationResult,
    ValidationRun,
)

from app.models.audit import (
    AuditAction,
    AuditLog,
)

from app.schemas.audit import (
    AuditHistoryResponse,
    AuditLogResponse,
)

from app.schemas.extraction import (
    ExtractedFieldResponse,
    ExtractionSummaryResponse,
)

from app.schemas.validation import (
    ValidationResultResponse,
    ValidationSummaryResponse,
)

from app.schemas.review import (
    ReviewFieldRequest,
    ReviewFieldResponse,
)

from app.services.documents import (
    DocumentStorageService,
)

from app.services.documents.file_validation import (
    validate_upload,
)

from app.services.extraction import (
    ExtractionService,
)

from app.services.ocr import (
    OCRService,
)

from app.services.processing.document_processor import (
    process_document,
)

from app.services.processing.pipeline_service import (
    DocumentPipelineService,
)

from app.services.validation import (
    ValidationService,
)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


# ============================================================
# HEALTH
# ============================================================


@router.get("/health")
def documents_health() -> dict[str, str]:
    """
    Health check for the document service.

    This endpoint only confirms that the document API service
    is running. It is not a document-quality or document-health
    assessment.
    """

    return {
        "status": "ok",
        "service": "documents",
    }


# ============================================================
# UPLOAD
# ============================================================


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(
            UserRole.ADMIN,
            UserRole.REVIEWER,
        )
    ),
) -> dict:
    """
    Upload and persist a land-record document.

    Requires:
        ADMIN or REVIEWER

    The file is:
    - validated
    - hashed with SHA-256
    - stored privately
    - registered in the database
    - processed into page records
    """

    # ---------------------------------------------------------
    # 1. Validate uploaded file
    # ---------------------------------------------------------

    try:
        data = await validate_upload(file)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    # ---------------------------------------------------------
    # 2. Generate SHA-256 hash
    # ---------------------------------------------------------

    file_hash = hashlib.sha256(data).hexdigest()

    # ---------------------------------------------------------
    # 3. Check for duplicate document
    # ---------------------------------------------------------

    existing_document = (
        db.query(Document)
        .filter(
            Document.file_hash_sha256 == file_hash
        )
        .first()
    )

    if existing_document:
        return {
            "document_id": str(existing_document.id),
            "status": "ALREADY_EXISTS",
            "message": "This document has already been uploaded.",
        }

    # ---------------------------------------------------------
    # 4. Create document database record
    # ---------------------------------------------------------

    document = Document(
        id=uuid4(),
        original_filename=file.filename,
        file_hash_sha256=file_hash,
    )

    db.add(document)
    db.flush()

    # ---------------------------------------------------------
    # 5. Store original document privately
    # ---------------------------------------------------------

    storage_service = DocumentStorageService()

    document_file = storage_service.store_document(
        db=db,
        document=document,
        data=data,
        original_filename=file.filename,
        content_type=(
            file.content_type
            or "application/octet-stream"
        ),
    )

    # ---------------------------------------------------------
    # 6. Resolve stored document path
    # ---------------------------------------------------------

    stored_file_path = (
        storage_service.get_document_file_path(
            document_file
        )
    )

    # ---------------------------------------------------------
    # 7. Process document into page images
    # ---------------------------------------------------------

    try:
        pages = process_document(
            db=db,
            document=document,
            file_path=str(stored_file_path),
        )

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {exc}",
        ) from exc

    # ---------------------------------------------------------
    # 8. Commit transaction
    # ---------------------------------------------------------

    db.commit()

    # ---------------------------------------------------------
    # 9. Return upload result
    # ---------------------------------------------------------

    return {
        "document_id": str(document.id),
        "document_file_id": str(document_file.id),
        "status": document.status.value,
        "filename": document.original_filename,
        "file_size_bytes": document_file.file_size_bytes,
        "sha256": document.file_hash_sha256,
        "pages_created": len(pages),
    }


# ============================================================
# OCR / PROCESS
# ============================================================


@router.post("/{document_id}/process")
def process_document_ocr(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(
            UserRole.ADMIN,
            UserRole.REVIEWER,
        )
    ),
) -> dict:
    """
    Run OCR on all processed pages of a document.

    Requires:
        ADMIN or REVIEWER

    OCR results are persisted as:
    - OCRRun
    - OCRBlock

    The document status is updated based on OCR completion.
    """

    # ---------------------------------------------------------
    # 1. Find document
    # ---------------------------------------------------------

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    # ---------------------------------------------------------
    # 2. Ensure page images exist
    # ---------------------------------------------------------

    try:
        storage_service = DocumentStorageService()
        pages = (
            db.query(DocumentPage)
            .filter(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_number)
            .all()
        )

        pages_need_rebuild = not pages

        if pages and not pages_need_rebuild:
            for page in pages:
                if not page.image_storage_key:
                    pages_need_rebuild = True
                    break
                try:
                    storage_service.storage.get_path(page.image_storage_key)
                except FileNotFoundError:
                    pages_need_rebuild = True
                    break

        if pages_need_rebuild:
            document_file = (
                db.query(DocumentFile)
                .filter(DocumentFile.document_id == document_id)
                .order_by(DocumentFile.created_at.desc())
                .first()
            )
            if document_file is None:
                raise ValueError(
                    "No stored source file is available for this document."
                )

            # Remove stale/incomplete page rows before rebuilding them.
            db.query(DocumentPage).filter(
                DocumentPage.document_id == document_id
            ).delete(synchronize_session=False)
            db.flush()

            process_document(
                db=db,
                document=document,
                file_path=str(
                    storage_service.get_document_file_path(document_file)
                ),
            )
            db.flush()

        # -----------------------------------------------------
        # 3. Run OCR
        # -----------------------------------------------------

        ocr_service = OCRService()
        ocr_runs = ocr_service.process_document(
            db=db,
            document=document,
            language="mar+eng",
        )

        # -----------------------------------------------------
        # 3. Commit OCR results
        # -----------------------------------------------------

        db.commit()

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"OCR processing failed: {exc}",
        ) from exc

    # ---------------------------------------------------------
    # 4. Return OCR processing result
    # ---------------------------------------------------------

    return {
        "document_id": str(document.id),
        "status": document.status.value,
        "ocr_runs": [
            {
                "ocr_run_id": str(run.id),
                "status": run.status.value,
                "engine": run.engine,
                "engine_version": run.engine_version,
                "language": run.language,
                "confidence": run.confidence,
            }
            for run in ocr_runs
        ],
    }


# ============================================================
# END-TO-END PIPELINE
# ============================================================


@router.post("/{document_id}/run")
def run_document_pipeline(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(
            UserRole.ADMIN,
            UserRole.REVIEWER,
        )
    ),
) -> dict:
    """Run ingestion recovery, OCR, classification, extraction, evidence and validation."""

    try:
        result = DocumentPipelineService().run(
            db=db,
            document_id=document_id,
            language="mar+eng",
        )
        return result
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"End-to-end document pipeline failed: {exc}",
        ) from exc


# ============================================================
# EXTRACTION
# ============================================================


@router.post(
    "/{document_id}/extract",
    response_model=ExtractionSummaryResponse,
)
def extract_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(
            UserRole.ADMIN,
            UserRole.REVIEWER,
        )
    ),
):
    """
    Extract structured land-record fields from the latest
    completed OCR results of a document.

    Requires:
        ADMIN or REVIEWER

    Extraction results are linked to:
    - extraction run
    - source OCR run
    - OCR evidence block
    - evidence bounding box
    """

    # ---------------------------------------------------------
    # 1. Confirm document exists
    # ---------------------------------------------------------

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    # ---------------------------------------------------------
    # 2. Run extraction
    # ---------------------------------------------------------

    try:
        extraction_service = ExtractionService()

        fields = extraction_service.extract_document_fields(
            db=db,
            document_id=document_id,
        )

        # -----------------------------------------------------
        # 3. Find extraction run created by this operation
        # -----------------------------------------------------

        extraction_run = (
            db.query(ExtractionRun)
            .filter(
                ExtractionRun.document_id == document_id
            )
            .order_by(
                ExtractionRun.created_at.desc()
            )
            .first()
        )

        if extraction_run is None:
            db.rollback()

            raise HTTPException(
                status_code=500,
                detail=(
                    "Extraction completed without "
                    "creating an extraction run."
                ),
            )

        # -----------------------------------------------------
        # 4. Commit extraction results
        # -----------------------------------------------------

        db.commit()

        # -----------------------------------------------------
        # 5. Refresh extraction run
        # -----------------------------------------------------

        db.refresh(extraction_run)

        # -----------------------------------------------------
        # 6. Return extraction result
        # -----------------------------------------------------

        return ExtractionSummaryResponse(
            document_id=document_id,
            extraction_run_id=extraction_run.id,
            status=(
                extraction_run.status.value
                if hasattr(
                    extraction_run.status,
                    "value",
                )
                else str(extraction_run.status)
            ),
            engine=extraction_run.engine,
            engine_version=extraction_run.engine_version,
            confidence=extraction_run.confidence,
            fields_extracted=len(fields),
            fields=[
                field
                for field in fields
            ],
        )

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {exc}",
        ) from exc


# ============================================================
# EXTRACTED FIELDS
# ============================================================


@router.get(
    "/{document_id}/fields",
    response_model=list[ExtractedFieldResponse],
)
def get_document_fields(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return extracted fields for the latest extraction run."""

    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    latest_run = (
        db.query(ExtractionRun)
        .filter(ExtractionRun.document_id == document_id)
        .order_by(ExtractionRun.created_at.desc())
        .first()
    )
    if latest_run is None:
        return []

    fields = (
        db.query(ExtractedField)
        .join(DocumentPage, ExtractedField.document_page_id == DocumentPage.id)
        .filter(
            DocumentPage.document_id == document_id,
            ExtractedField.extraction_run_id == latest_run.id,
        )
        .order_by(DocumentPage.page_number, ExtractedField.created_at)
        .all()
    )
    return [ExtractedFieldResponse.model_validate(field) for field in fields]


# ============================================================
# VALIDATION
# ============================================================


@router.post("/{document_id}/validate")
def validate_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(
            UserRole.ADMIN,
            UserRole.REVIEWER,
        )
    ),
) -> dict:
    """
    Run validation rules against fields from the latest
    completed extraction run for a document.

    Requires:
        ADMIN or REVIEWER

    Every execution creates a separate ValidationRun.
    """

    # ---------------------------------------------------------
    # 1. Find document
    # ---------------------------------------------------------

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    # ---------------------------------------------------------
    # 2. Run validation
    # ---------------------------------------------------------

    try:
        validation_service = ValidationService()

        validation_run, results = (
            validation_service.validate_document(
                db=db,
                document_id=document_id,
            )
        )

        db.commit()

        db.refresh(validation_run)

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {exc}",
        ) from exc

    # ---------------------------------------------------------
    # 3. Return validation result
    # ---------------------------------------------------------

    return {
        "document_id": str(document.id),
        "validation_run_id": str(
            validation_run.id
        ),
        "status": (
            validation_run.status.value
            if hasattr(
                validation_run.status,
                "value",
            )
            else str(
                validation_run.status
            )
        ),
        "engine": validation_run.engine,
        "engine_version": (
            validation_run.engine_version
        ),
        "confidence": (
            validation_run.confidence
        ),
        "total_results": len(results),
        "results": [
            {
                "field_name": result.field_name,
                "rule_name": result.rule_name,
                "status": result.status.value,
                "message": result.message,
                "confidence": result.confidence,
            }
            for result in results
        ],
    }


# ============================================================
# GET VALIDATION RESULTS
# ============================================================


@router.get(
    "/{document_id}/validation",
    response_model=ValidationSummaryResponse,
)
def get_document_validation(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve validation results from the latest
    validation run for a document.

    Requires:
        Any authenticated user.
    """

    # ---------------------------------------------------------
    # 1. Confirm document exists
    # ---------------------------------------------------------

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    # ---------------------------------------------------------
    # 2. Find latest validation run
    # ---------------------------------------------------------

    validation_run = (
        db.query(ValidationRun)
        .filter(
            ValidationRun.document_id
            == document_id
        )
        .order_by(
            ValidationRun.created_at.desc()
        )
        .first()
    )

    if validation_run is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No validation run found "
                "for this document."
            ),
        )

    # ---------------------------------------------------------
    # 3. Retrieve results belonging to this run
    # ---------------------------------------------------------

    rows = (
        db.query(
            ValidationResult,
            ExtractedField,
        )
        .join(
            ExtractedField,
            ValidationResult.extracted_field_id
            == ExtractedField.id,
        )
        .filter(
            ValidationResult.validation_run_id
            == validation_run.id
        )
        .order_by(
            ValidationResult.created_at
        )
        .all()
    )

    # ---------------------------------------------------------
    # 4. Build response objects
    # ---------------------------------------------------------

    results = [
        ValidationResultResponse(
            id=validation_result.id,
            validation_run_id=(
                validation_result.validation_run_id
            ),
            extracted_field_id=(
                validation_result.extracted_field_id
            ),
            field_name=field.field_name,
            rule_name=validation_result.rule_name,
            status=(
                validation_result.status.value
                if hasattr(
                    validation_result.status,
                    "value",
                )
                else str(
                    validation_result.status
                )
            ),
            message=validation_result.message,
            confidence=validation_result.confidence,
        )
        for validation_result, field in rows
    ]

    # ---------------------------------------------------------
    # 5. Calculate summary counts
    # ---------------------------------------------------------

    pass_count = sum(
        1
        for result in results
        if result.status == "PASS"
    )

    warning_count = sum(
        1
        for result in results
        if result.status == "WARNING"
    )

    review_count = sum(
        1
        for result in results
        if result.status == "REVIEW"
    )

    # ---------------------------------------------------------
    # 6. Return latest validation summary
    # ---------------------------------------------------------

    return ValidationSummaryResponse(
        document_id=document_id,
        validation_run_id=validation_run.id,
        status=(
            validation_run.status.value
            if hasattr(
                validation_run.status,
                "value",
            )
            else str(
                validation_run.status
            )
        ),
        engine=validation_run.engine,
        engine_version=(
            validation_run.engine_version
        ),
        confidence=validation_run.confidence,
        total_results=len(results),
        pass_count=pass_count,
        warning_count=warning_count,
        review_count=review_count,
        results=results,
    )


# ============================================================
# HUMAN VERIFICATION / REVIEW
# ============================================================


@router.post(
    "/fields/{field_id}/review",
    response_model=ReviewFieldResponse,
)
def review_extracted_field(
    field_id: UUID,
    payload: ReviewFieldRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(
            UserRole.ADMIN,
            UserRole.REVIEWER,
        )
    ),
):
    """
    Apply a human verification action to an extracted field.

    Requires:
        ADMIN or REVIEWER

    Supported actions:

    ACCEPT
        Accept the extracted value as-is.

    EDIT
        Replace the extracted value with a corrected value.

    REJECT
        Reject the extracted value.

    VERIFY
        Mark the extracted value as human verified.

    FLAG
        Flag the field for further investigation.

    Every action creates an immutable audit log entry.

    The reviewer identity is taken from the authenticated JWT.
    It is never accepted from the request body.
    """

    # ---------------------------------------------------------
    # 1. Find extracted field
    # ---------------------------------------------------------

    field = (
        db.query(ExtractedField)
        .filter(
            ExtractedField.id == field_id
        )
        .first()
    )

    if field is None:
        raise HTTPException(
            status_code=404,
            detail="Extracted field not found.",
        )

    # ---------------------------------------------------------
    # 2. Find document page
    # ---------------------------------------------------------

    page = (
        db.query(DocumentPage)
        .filter(
            DocumentPage.id
            == field.document_page_id
        )
        .first()
    )

    if page is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Document page not found "
                "for extracted field."
            ),
        )

    # ---------------------------------------------------------
    # 3. Validate action-specific input
    # ---------------------------------------------------------

    if payload.action == AuditAction.EDIT:

        if payload.new_value is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "new_value is required "
                    "when action is EDIT."
                ),
            )

        if not payload.new_value.strip():
            raise HTTPException(
                status_code=400,
                detail=(
                    "new_value cannot be empty "
                    "when action is EDIT."
                ),
            )

    # ---------------------------------------------------------
    # 4. Capture old value
    # ---------------------------------------------------------

    old_value = field.value

    # ---------------------------------------------------------
    # 5. Apply human decision
    # ---------------------------------------------------------

    if payload.action == AuditAction.ACCEPT:

        field.validation_status = "ACCEPTED"

        new_value = field.value

    elif payload.action == AuditAction.EDIT:

        new_value = payload.new_value.strip()

        field.value = new_value

        # Keep normalized value synchronized.
        field.normalized_value = new_value.casefold()

        field.validation_status = "EDITED"

    elif payload.action == AuditAction.REJECT:

        field.validation_status = "REJECTED"

        new_value = field.value

    elif payload.action == AuditAction.VERIFY:

        field.validation_status = "VERIFIED"

        new_value = field.value

    elif payload.action == AuditAction.FLAG:

        field.validation_status = "FLAGGED"

        new_value = field.value

    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported review action.",
        )

    # ---------------------------------------------------------
    # 6. Create audit log
    # ---------------------------------------------------------

    audit_log = AuditLog(
        id=uuid4(),
        document_id=page.document_id,
        extracted_field_id=field.id,
        action=payload.action,
        old_value=old_value,
        new_value=new_value,
        decision=field.validation_status,
        reason=payload.reason,

        # SECURITY:
        # reviewer identity comes from the JWT,
        # never from client input.
        reviewer_id=current_user.id,
    )

    db.add(audit_log)

    # ---------------------------------------------------------
    # 7. Commit atomically
    # ---------------------------------------------------------

    try:
        db.commit()

        db.refresh(field)
        db.refresh(audit_log)

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to save review decision: {exc}"
            ),
        ) from exc

    # ---------------------------------------------------------
    # 8. Return review result
    # ---------------------------------------------------------

    return ReviewFieldResponse(
        field_id=field.id,
        field_name=field.field_name,
        old_value=old_value,
        new_value=field.value,
        validation_status=field.validation_status,
        action=audit_log.action,
        reason=audit_log.reason,
        audit_log_id=audit_log.id,
    )


# ============================================================
# AUDIT HISTORY
# ============================================================


@router.get(
    "/{document_id}/audit",
    response_model=AuditHistoryResponse,
)
def get_document_audit_history(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve the complete human-review audit history
    for a document.

    Requires:
        Any authenticated user.

    Audit records are ordered from newest to oldest.
    """

    # ---------------------------------------------------------
    # 1. Confirm document exists
    # ---------------------------------------------------------

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id
        )
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    # ---------------------------------------------------------
    # 2. Retrieve audit logs
    # ---------------------------------------------------------

    logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.document_id == document_id
        )
        .order_by(
            AuditLog.created_at.desc()
        )
        .all()
    )

    # ---------------------------------------------------------
    # 3. Build response
    # ---------------------------------------------------------

    return AuditHistoryResponse(
        document_id=document_id,
        total=len(logs),
        logs=[
            AuditLogResponse(
                id=log.id,
                document_id=log.document_id,
                extracted_field_id=log.extracted_field_id,
                action=log.action,
                old_value=log.old_value,
                new_value=log.new_value,
                decision=log.decision,
                reason=log.reason,
                reviewer_id=log.reviewer_id,
                created_at=log.created_at,
            )
            for log in logs
        ],
    )

# ============================================================
# EVIDENCE / SOURCE PAGE
# ============================================================

@router.get("/{document_id}/pages")
def list_document_pages(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(
            UserRole.ADMIN,
            UserRole.REVIEWER,
        )
    ),
):
    """
    Return source-page metadata for an authenticated document.

    Storage keys are intentionally never returned to the client.
    """

    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    pages = (
        db.query(DocumentPage)
        .filter(DocumentPage.document_id == document_id)
        .order_by(DocumentPage.page_number)
        .all()
    )

    return [
        {
            "id": str(page.id),
            "document_id": str(page.document_id),
            "page_number": page.page_number,
        }
        for page in pages
    ]


@router.get("/{document_id}/pages/{page_id}/image")
def get_document_page_image(
    document_id: UUID,
    page_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(
            UserRole.ADMIN,
            UserRole.REVIEWER,
        )
    ),
):
    """
    Serve one authenticated source-page image.

    The client receives image bytes only; the private storage key/path
    is never exposed.
    """

    page = (
        db.query(DocumentPage)
        .filter(
            DocumentPage.id == page_id,
            DocumentPage.document_id == document_id,
        )
        .first()
    )

    if page is None:
        raise HTTPException(
            status_code=404,
            detail="Document page not found.",
        )

    if not page.image_storage_key:
        raise HTTPException(
            status_code=404,
            detail="Source page image is unavailable.",
        )

    storage_service = DocumentStorageService()

    try:
        image_path = storage_service.storage.get_path(
            page.image_storage_key
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="Source page image file not found.",
        ) from exc

    suffix = image_path.suffix.lower()

    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }

    media_type = media_types.get(
        suffix,
        "application/octet-stream",
    )

    return FileResponse(
        path=image_path,
        media_type=media_type,
        filename=f"document-{document_id}-page-{page.page_number}{suffix}",
    )
