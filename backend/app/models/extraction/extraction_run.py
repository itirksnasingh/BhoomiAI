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


class ExtractionRunStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"
    __table_args__ = {"schema": "extraction"}

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

    source_ocr_run_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "extraction.ocr_runs.id",
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

    status: Mapped[ExtractionRunStatus] = mapped_column(
        SAEnum(
            ExtractionRunStatus,
            name="extraction_run_status",
            schema="extraction",
            create_type=True,
        ),
        nullable=False,
        default=ExtractionRunStatus.RUNNING,
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
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
