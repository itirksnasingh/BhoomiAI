from app.models.documents import (
    Document,
    DocumentFile,
    DocumentPage,
    DocumentStatus,
    DocumentType,
)

from app.models.extraction import (
    ExtractedField,
    ExtractionRun,
    ExtractionRunStatus,
    FieldEvidence,
    OCRBlock,
    OCRRun,
    OCRRunStatus,
)

from app.models.validation import (
    ValidationResult,
    ValidationRun,
    ValidationRunStatus,
    ValidationStatus,
)

from app.models.audit import (
    AuditAction,
    AuditLog,
)

from app.models.system import SchemaInfo

from app.models.reference import ReferenceVillage


__all__ = [
    # --------------------------------------------------------
    # Documents
    # --------------------------------------------------------
    "Document",
    "DocumentFile",
    "DocumentPage",
    "DocumentStatus",
    "DocumentType",

    # --------------------------------------------------------
    # Extraction
    # --------------------------------------------------------
    "ExtractedField",
    "ExtractionRun",
    "ExtractionRunStatus",
    "FieldEvidence",
    "OCRBlock",
    "OCRRun",
    "OCRRunStatus",

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------
    "ValidationResult",
    "ValidationRun",
    "ValidationRunStatus",
    "ValidationStatus",

    # --------------------------------------------------------
    # Audit
    # --------------------------------------------------------
    "AuditAction",
    "AuditLog",

    # --------------------------------------------------------
    # System
    # --------------------------------------------------------
    "SchemaInfo",

    # --------------------------------------------------------
    # reference
    # --------------------------------------------------------
    "ReferenceVillage",

]
from app.models.auth import User, UserRole