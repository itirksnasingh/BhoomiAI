from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExtractedFieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_page_id: UUID
    extraction_run_id: UUID | None
    source_ocr_run_id: UUID | None
    field_name: str
    value: str | None
    normalized_value: str | None
    confidence: float | None
    extraction_method: str
    evidence_bbox: dict | None
    validation_status: str


class ExtractionSummaryResponse(BaseModel):
    document_id: UUID
    extraction_run_id: UUID
    status: str
    engine: str
    engine_version: str | None
    confidence: float | None
    fields_extracted: int
    fields: list[ExtractedFieldResponse]