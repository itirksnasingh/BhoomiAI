from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Float,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    __table_args__ = {
        "schema": "extraction",
    }

    # --------------------------------------------------------
    # Primary key
    # --------------------------------------------------------

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # --------------------------------------------------------
    # Document page
    # --------------------------------------------------------

    document_page_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "documents.document_pages.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # --------------------------------------------------------
    # Extraction lineage
    # --------------------------------------------------------

    extraction_run_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "extraction.extraction_runs.id",
            ondelete="CASCADE",
        ),
        nullable=True,
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

    # --------------------------------------------------------
    # Extracted field
    # --------------------------------------------------------

    field_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    normalized_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    extraction_method: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    evidence_bbox: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    validation_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING",
    )

    # --------------------------------------------------------
    # Timestamp
    # --------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # --------------------------------------------------------
    # Relationships
    # --------------------------------------------------------

    document_page = relationship(
        "DocumentPage",
        back_populates="extracted_fields",
    )

    extraction_run = relationship(
        "ExtractionRun",
        foreign_keys=[extraction_run_id],
    )

    source_ocr_run = relationship(
        "OCRRun",
        foreign_keys=[source_ocr_run_id],
    )