from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ValidationResultResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID
    validation_run_id: UUID
    extracted_field_id: UUID
    field_name: str
    rule_name: str
    status: str
    message: str
    confidence: float | None


class ValidationSummaryResponse(BaseModel):
    document_id: UUID
    validation_run_id: UUID
    status: str
    engine: str
    engine_version: str | None
    confidence: float | None

    total_results: int
    pass_count: int
    warning_count: int
    review_count: int

    results: list[
        ValidationResultResponse
    ]