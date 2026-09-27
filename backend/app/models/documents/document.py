from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SAEnum, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DocumentStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    VALIDATION_REQUIRED = "VALIDATION_REQUIRED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


class DocumentType(str, Enum):
    UNKNOWN = "UNKNOWN"
    SEVEN_TWELVE = "7_12"
    EIGHT_A = "8A"
    FERFAR = "FERFAR"
    PROPERTY_CARD = "PROPERTY_CARD"
    OTHER = "OTHER"


class Document(Base):
    __tablename__ = "documents"

    __table_args__ = {"schema": "documents"}

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    document_type: Mapped[DocumentType] = mapped_column(
        SAEnum(
            DocumentType,
            name="document_type",
            schema="documents",
        ),
        default=DocumentType.UNKNOWN,
        nullable=False,
    )

    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(
            DocumentStatus,
            name="document_status",
            schema="documents",
        ),
        default=DocumentStatus.UPLOADED,
        nullable=False,
    )

    language: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    file_hash_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )