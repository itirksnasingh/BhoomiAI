from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Float,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ValidationStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    REVIEW = "REVIEW"


class ValidationResult(Base):
    __tablename__ = "validation_results"

    __table_args__ = {"schema": "validation"}

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    validation_run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "validation.validation_runs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    extracted_field_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "extraction.extracted_fields.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    rule_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    status: Mapped[ValidationStatus] = mapped_column(
        SAEnum(
            ValidationStatus,
            name="validation_status",
            schema="validation",
            create_type=False,
        ),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )