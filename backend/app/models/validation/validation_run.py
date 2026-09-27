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


class ValidationRunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ValidationRun(Base):
    __tablename__ = "validation_runs"

    __table_args__ = {"schema": "validation"}

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "documents.documents.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    extraction_run_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "extraction.extraction_runs.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    engine: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="deterministic",
    )

    engine_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    status: Mapped[ValidationRunStatus] = mapped_column(
        SAEnum(
            ValidationRunStatus,
            name="validation_run_status",
            schema="validation",
            create_type=True,
        ),
        nullable=False,
        default=ValidationRunStatus.PENDING,
    )

    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )