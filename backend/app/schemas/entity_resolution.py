from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EntityRecordInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    record_id: str
    document_id: str | None = None

    owner: str | None = None
    survey_number: str | None = None
    khata_number: str | None = None
    village: str | None = None
    taluka: str | None = None
    district: str | None = None
    area: str | None = None


class EntityMatchResponse(BaseModel):
    record_a: str
    record_b: str
    score: float = Field(ge=0.0, le=1.0)
    decision: str
    reasons: list[str]
    compared_fields: dict[str, float]
    source_document_a: str | None = None
    source_document_b: str | None = None


class EntityResolutionRequest(BaseModel):
    records: list[EntityRecordInput] = Field(min_length=2, max_length=500)
    include_no_match: bool = False


class EntityResolutionResponse(BaseModel):
    total_records: int
    comparisons: int
    flagged_matches: int
    results: list[EntityMatchResponse]
