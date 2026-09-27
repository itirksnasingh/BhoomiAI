from __future__ import annotations

from pydantic import BaseModel, Field


class ConfidenceCalibrationRequest(BaseModel):
    extraction_confidence: float | None = Field(default=None, ge=0, le=100)
    ocr_confidence: float | None = Field(default=None, ge=0, le=100)
    validation_status: str | None = None
    entity_match_score: float | None = Field(default=None, ge=0, le=100)
    has_conflict: bool = False
    requires_review: bool = False


class ConfidenceCalibrationResponse(BaseModel):
    score: float = Field(ge=0, le=1)
    band: str
    automation_allowed: bool
    reasons: list[str]
