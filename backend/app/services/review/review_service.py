from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditAction, AuditLog
from app.models.extraction import ExtractedField


class ReviewService:

    @staticmethod
    def review_field(
        db: Session,
        field_id: UUID,
        action: AuditAction,
        new_value: str | None = None,
        reason: str | None = None,
        reviewer_id: UUID | None = None,
    ) -> tuple[ExtractedField, AuditLog]:

        # ----------------------------------------------------
        # 1. Fetch extracted field
        # ----------------------------------------------------

        field = db.scalar(
            select(ExtractedField).where(
                ExtractedField.id == field_id
            )
        )

        if field is None:
            raise ValueError(
                f"Extracted field {field_id} not found"
            )

        # ----------------------------------------------------
        # 2. Capture old value
        # ----------------------------------------------------

        old_value = field.value

        # ----------------------------------------------------
        # 3. Determine new value and status
        # ----------------------------------------------------

        if action == AuditAction.ACCEPT:
            field.validation_status = "ACCEPTED"

        elif action == AuditAction.VERIFY:
            field.validation_status = "VERIFIED"

        elif action == AuditAction.FLAG:
            field.validation_status = "FLAGGED"

        elif action == AuditAction.REJECT:
            field.validation_status = "REJECTED"

        elif action == AuditAction.EDIT:

            if new_value is None or not new_value.strip():
                raise ValueError(
                    "new_value is required when action is EDIT"
                )

            field.value = new_value.strip()

            # Keep normalized value synchronized for the MVP.
            field.normalized_value = new_value.strip().casefold()

            field.validation_status = "EDITED"

        # ----------------------------------------------------
        # 4. Create audit record
        # ----------------------------------------------------

        audit_log = AuditLog(
            document_id=field.document_page.document_id,
            extracted_field_id=field.id,
            action=action,
            old_value=old_value,
            new_value=field.value,
            decision=field.validation_status,
            reason=reason,
            reviewer_id=reviewer_id,
            created_at=datetime.now(timezone.utc),
        )

        db.add(audit_log)

        # ----------------------------------------------------
        # 5. Persist atomically
        # ----------------------------------------------------

        db.commit()

        db.refresh(field)
        db.refresh(audit_log)

        return field, audit_log