from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class OCRBlock(Base):
    __tablename__ = "ocr_blocks"

    __table_args__ = {"schema": "extraction"}

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    ocr_run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "extraction.ocr_runs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    block_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    confidence: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    # Bounding box in image coordinates:
    # {"x": 100, "y": 200, "width": 300, "height": 50}
    bbox: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    language: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )