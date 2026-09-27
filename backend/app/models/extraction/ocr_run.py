from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class OCRRunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class OCRRun(Base):
    __tablename__ = "ocr_runs"

    __table_args__ = {"schema": "extraction"}

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    document_page_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "documents.document_pages.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    engine: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    engine_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    language: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    status: Mapped[OCRRunStatus] = mapped_column(
        SAEnum(
            OCRRunStatus,
            name="ocr_run_status",
            schema="extraction",
        ),
        default=OCRRunStatus.PENDING,
        nullable=False,
    )

    confidence: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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