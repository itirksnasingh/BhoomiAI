from __future__ import annotations

from pydantic import BaseModel, Field


class ReviewQueueItem(BaseModel):
    field_id: str
    document_id: str
    field_name: str
    extracted_value: str | None = None
    normalized_value: str | None = None
    confidence: float | None = None
    validation_status: str | None = None
    review_required: bool = True
    review_reason: str | None = None


class ReviewQueueResponse(BaseModel):
    total: int
    review_required: int
    items: list[ReviewQueueItem]


class ReviewDecisionSummary(BaseModel):
    action: str
    accepted: bool
    requires_revalidation: bool
    audit_required: bool
    reason: str
