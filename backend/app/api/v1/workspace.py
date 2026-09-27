from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import String, cast, func
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db

from app.models.audit import AuditLog
from app.models.documents import Document, DocumentPage
from app.models.extraction import ExtractedField, ExtractionRun
from app.models.validation import ValidationResult, ValidationRun


router = APIRouter(
    prefix="/workspace",
    tags=["Workspace"],
)


# ============================================================
# HELPERS
# ============================================================


def enum_value(value: Any) -> str:
    """
    Safely convert SQLAlchemy enum values to strings.
    """
    if hasattr(value, "value"):
        return str(value.value)

    return str(value)


def document_status_expression():
    """
    SQL expression used to group document statuses regardless of
    whether Document.status is represented as an enum or string.
    """
    return cast(Document.status, String)


def latest_completed_extraction_id_subquery(db: Session):
    """
    Return a correlated subquery that identifies the latest completed
    extraction run for each document.

    Historical extraction runs remain stored, but active workspace
    metrics/review items should only use the newest completed run.
    """

    return (
        db.query(ExtractionRun.id)
        .filter(
            ExtractionRun.document_id == Document.id,
            cast(ExtractionRun.status, String) == "COMPLETED",
        )
        .order_by(
            ExtractionRun.completed_at.desc().nullslast(),
            ExtractionRun.created_at.desc(),
        )
        .limit(1)
        .correlate(Document)
        .scalar_subquery()
    )


def latest_completed_validation_id_subquery(db: Session):
    """
    Return a correlated subquery that identifies the latest completed
    validation run for each document.

    This prevents the dashboard from counting validation results from
    every historical validation execution.
    """

    return (
        db.query(ValidationRun.id)
        .filter(
            ValidationRun.document_id == Document.id,
            cast(ValidationRun.status, String) == "COMPLETED",
        )
        .order_by(
            ValidationRun.completed_at.desc().nullslast(),
            ValidationRun.created_at.desc(),
        )
        .limit(1)
        .correlate(Document)
        .scalar_subquery()
    )


# ============================================================
# WORKSPACE SUMMARY
# ============================================================


@router.get("/summary")
def get_workspace_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:

    # --------------------------------------------------------
    # Document counts
    # --------------------------------------------------------

    total_documents = (
        db.query(
            func.count(Document.id)
        ).scalar()
        or 0
    )

    status_expression = document_status_expression()

    status_rows = (
        db.query(
            status_expression.label("status"),
            func.count(Document.id).label("count"),
        )
        .group_by(status_expression)
        .all()
    )

    status_counts = {
        enum_value(row.status).upper(): int(row.count)
        for row in status_rows
    }

    processed_documents = sum(
        status_counts.get(status, 0)
        for status in {
            "PROCESSED",
            "VALIDATED",
            "COMPLETED",
            "VERIFIED",
            "VALIDATION_REQUIRED",
        }
    )

    pending_documents = sum(
        status_counts.get(status, 0)
        for status in {
            "UPLOADED",
            "PENDING",
            "PROCESSING",
            "OCR_PROCESSING",
            "EXTRACTING",
            "VALIDATING",
        }
    )

    failed_documents = sum(
        status_counts.get(status, 0)
        for status in {
            "FAILED",
            "ERROR",
        }
    )

    # --------------------------------------------------------
    # Latest extraction run for each document
    # --------------------------------------------------------

    latest_extraction_id = (
        latest_completed_extraction_id_subquery(db)
    )

    review_statuses = {
        "REVIEW",
        "WARNING",
        "FLAGGED",
    }

    # --------------------------------------------------------
    # Active fields needing human review
    #
    # IMPORTANT:
    # Only fields belonging to the latest completed extraction
    # are counted.
    # --------------------------------------------------------

    fields_needing_review = (
        db.query(
            func.count(ExtractedField.id)
        )
        .join(
            DocumentPage,
            ExtractedField.document_page_id
            == DocumentPage.id,
        )
        .join(
            Document,
            DocumentPage.document_id
            == Document.id,
        )
        .filter(
            ExtractedField.extraction_run_id
            == latest_extraction_id,
            ExtractedField.validation_status.in_(
                review_statuses
            ),
        )
        .scalar()
        or 0
    )

    # --------------------------------------------------------
    # Latest extracted field count
    #
    # Historical fields remain in the database but aren't counted
    # as current workspace fields.
    # --------------------------------------------------------

    total_extracted_fields = (
        db.query(
            func.count(ExtractedField.id)
        )
        .join(
            DocumentPage,
            ExtractedField.document_page_id
            == DocumentPage.id,
        )
        .join(
            Document,
            DocumentPage.document_id
            == Document.id,
        )
        .filter(
            ExtractedField.extraction_run_id
            == latest_extraction_id,
        )
        .scalar()
        or 0
    )

    # --------------------------------------------------------
    # Latest extraction confidence
    #
    # This is calculated from the active/latest fields rather than
    # every historical extraction ever performed.
    # --------------------------------------------------------

    average_confidence = (
        db.query(
            func.avg(
                ExtractedField.confidence
            )
        )
        .join(
            DocumentPage,
            ExtractedField.document_page_id
            == DocumentPage.id,
        )
        .join(
            Document,
            DocumentPage.document_id
            == Document.id,
        )
        .filter(
            ExtractedField.extraction_run_id
            == latest_extraction_id,
            ExtractedField.confidence.isnot(None),
        )
        .scalar()
    )

    # --------------------------------------------------------
    # Latest validation run for each document
    # --------------------------------------------------------

    latest_validation_id = (
        latest_completed_validation_id_subquery(db)
    )

    validation_rows = (
        db.query(
            cast(
                ValidationResult.status,
                String,
            ).label("status"),
            func.count(
                ValidationResult.id
            ).label("count"),
        )
        .join(
            ValidationRun,
            ValidationResult.validation_run_id
            == ValidationRun.id,
        )
        .join(
            Document,
            ValidationRun.document_id
            == Document.id,
        )
        .filter(
            ValidationResult.validation_run_id
            == latest_validation_id,
        )
        .group_by(
            cast(
                ValidationResult.status,
                String,
            )
        )
        .all()
    )

    validation_counts = {
        enum_value(row.status).upper(): int(row.count)
        for row in validation_rows
    }

    # --------------------------------------------------------
    # Recent documents
    # --------------------------------------------------------

    recent_documents = (
        db.query(Document)
        .order_by(
            Document.created_at.desc()
        )
        .limit(5)
        .all()
    )

    return {
        "total_documents": int(
            total_documents
        ),

        "processed_documents": int(
            processed_documents
        ),

        "pending_documents": int(
            pending_documents
        ),

        "failed_documents": int(
            failed_documents
        ),

        "fields_needing_review": int(
            fields_needing_review
        ),

        "validation_passed": int(
            validation_counts.get(
                "PASS",
                0,
            )
        ),

        "validation_review": int(
            validation_counts.get(
                "REVIEW",
                0,
            )
            + validation_counts.get(
                "WARNING",
                0,
            )
        ),

        "validation_failed": int(
            validation_counts.get(
                "FAIL",
                0,
            )
            + validation_counts.get(
                "FAILED",
                0,
            )
        ),

        "total_extracted_fields": int(
            total_extracted_fields
        ),

        "average_confidence": (
            float(average_confidence)
            if average_confidence is not None
            else None
        ),

        "recent_documents": [
            {
                "id": str(document.id),

                "original_filename": (
                    document.original_filename
                ),

                "status": enum_value(
                    document.status
                ),

                "created_at": (
                    document.created_at.isoformat()
                ),
            }
            for document in recent_documents
        ],
    }


# ============================================================
# WORKSPACE NOTIFICATIONS
# ============================================================


@router.get("/notifications")
def get_workspace_notifications(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:

    review_statuses = {
        "REVIEW",
        "WARNING",
        "FLAGGED",
    }

    latest_extraction_id = (
        latest_completed_extraction_id_subquery(db)
    )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Notifications only come from fields belonging to the latest
    # completed extraction run of each document.
    #
    # This prevents old extraction attempts from producing
    # permanent/stale notification counts.
    # --------------------------------------------------------

    rows = (
        db.query(
            ExtractedField,
            DocumentPage,
            Document,
        )
        .join(
            DocumentPage,
            ExtractedField.document_page_id
            == DocumentPage.id,
        )
        .join(
            Document,
            DocumentPage.document_id
            == Document.id,
        )
        .filter(
            ExtractedField.extraction_run_id
            == latest_extraction_id,
            ExtractedField.validation_status.in_(
                review_statuses
            ),
        )
        .order_by(
            ExtractedField.created_at.desc()
        )
        .limit(50)
        .all()
    )

    items = []

    for field, page, document in rows:

        status = enum_value(
            field.validation_status
        ).upper()

        if status == "FLAGGED":
            severity = "FLAGGED"
            title = "Field has been flagged"

        elif status == "REVIEW":
            severity = "REVIEW"
            title = "Field requires review"

        else:
            severity = "WARNING"
            title = "Field has a validation warning"

        items.append(
            {
                "id": str(field.id),

                "type": "FIELD_REVIEW",

                "severity": severity,

                "title": title,

                "message": (
                    f"{field.field_name} "
                    f"in {document.original_filename}"
                ),

                "document_id": str(
                    document.id
                ),

                "field_id": str(
                    field.id
                ),

                "document_filename": (
                    document.original_filename
                ),

                "field_name": (
                    field.field_name
                ),

                "validation_status": status,

                "page_number": (
                    page.page_number
                ),

                "created_at": (
                    field.created_at.isoformat()
                ),
            }
        )

    return {
        "total": len(items),

        # Phase 1/3 does not yet have a persisted per-user
        # notification-read table. Therefore "unread" represents
        # the current actionable review workload.
        "unread": len(items),

        "items": items,
    }


# ============================================================
# WORKSPACE AUDIT
# ============================================================


@router.get("/audit")
def get_workspace_audit(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:

    # --------------------------------------------------------
    # Audit history intentionally includes ALL historical actions.
    #
    # Unlike Review Queue, audit history must never be restricted
    # to the latest extraction run because it is our lineage trail.
    # --------------------------------------------------------

    rows = (
        db.query(
            AuditLog,
            Document,
        )
        .join(
            Document,
            AuditLog.document_id
            == Document.id,
        )
        .order_by(
            AuditLog.created_at.desc()
        )
        .limit(200)
        .all()
    )

    return {
        "total": len(rows),

        "items": [
            {
                "id": str(log.id),

                "document_id": str(
                    log.document_id
                ),

                "document_filename": (
                    document.original_filename
                ),

                "extracted_field_id": (
                    str(log.extracted_field_id)
                    if log.extracted_field_id
                    else None
                ),

                "action": enum_value(
                    log.action
                ),

                "old_value": log.old_value,

                "new_value": log.new_value,

                "decision": log.decision,

                "reason": log.reason,

                "reviewer_id": (
                    str(log.reviewer_id)
                    if log.reviewer_id
                    else None
                ),

                "created_at": (
                    log.created_at.isoformat()
                ),
            }

            for log, document in rows
        ],
    }