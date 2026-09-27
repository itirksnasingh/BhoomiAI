from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.audit import AuditAction


class AuditLogResponse(BaseModel):
    id: UUID
    document_id: UUID
    extracted_field_id: UUID | None

    action: AuditAction

    old_value: str | None
    new_value: str | None

    decision: str | None
    reason: str | None

    reviewer_id: UUID | None

    created_at: datetime


class AuditHistoryResponse(BaseModel):
    document_id: UUID
    total: int
    logs: list[AuditLogResponse]