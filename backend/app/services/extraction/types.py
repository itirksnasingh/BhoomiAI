from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass
class ExtractedFieldResult:
    """One structured field with its source OCR evidence."""

    field_name: str
    value: str
    normalized_value: str
    confidence: float
    extraction_method: str
    evidence_block_id: UUID
    evidence_bbox: dict
