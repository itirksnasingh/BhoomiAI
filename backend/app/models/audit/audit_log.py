from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AuditAction(str, Enum):
    ACCEPT = "ACCEPT"
    EDIT = "EDIT"
    REJECT = "REJECT"
    VERIFY = "VERIFY"
    FLAG = "FLAG"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    __table_args__ = (
        Index(
            "ix_audit_logs_document_id",
            "document_id",
        ),
        Index(
            "ix_audit_logs_extracted_field_id",
            "extracted_field_id",
        ),
        Index(
            "ix_audit_logs_reviewer_id",
            "reviewer_id",
        ),
        {
            "schema": "audit",
        },
    )

    # --------------------------------------------------------
    # Primary key
    # --------------------------------------------------------

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )

    # --------------------------------------------------------
    # Document being audited
    # --------------------------------------------------------

    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "documents.documents.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    # --------------------------------------------------------
    # Extracted field being reviewed
    # --------------------------------------------------------

    extracted_field_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "extraction.extracted_fields.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    # --------------------------------------------------------
    # Reviewer action
    # --------------------------------------------------------

    action: Mapped[AuditAction] = mapped_column(
        PGEnum(
            "ACCEPT",
            "EDIT",
            "REJECT",
            "VERIFY",
            "FLAG",
            name="audit_action",
            schema="audit",
            create_type=False,
        ),
        nullable=False,
    )

    # --------------------------------------------------------
    # Value before human review/edit
    # --------------------------------------------------------

    old_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # --------------------------------------------------------
    # Value after human review/edit
    # --------------------------------------------------------

    new_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # --------------------------------------------------------
    # Review decision
    # --------------------------------------------------------

    decision: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # --------------------------------------------------------
    # Explanation for the review action
    # --------------------------------------------------------

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # --------------------------------------------------------
    # Reviewer ID
    #
    # Authentication/RBAC is not wired yet, so this remains
    # nullable and intentionally has no FK for now.
    # --------------------------------------------------------

    reviewer_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )

    # --------------------------------------------------------
    # Audit timestamp
    # --------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )