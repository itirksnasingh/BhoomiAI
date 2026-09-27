from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.audit.audit_log import AuditAction


class ReviewFieldRequest(BaseModel):
    """
    Request body for human review of an extracted field.

    The reviewer identity is intentionally NOT accepted from the client.
    It is derived from the authenticated JWT user in the API layer.
    """

    action: AuditAction
    new_value: str | None = Field(default=None, max_length=5000)
    reason: str | None = Field(default=None, max_length=5000)


class ReviewFieldResponse(BaseModel):
    """
    Response returned after a human review action.
    """

    model_config = ConfigDict(from_attributes=True)

    field_id: UUID
    action: AuditAction
    old_value: str | None
    new_value: str | None
    validation_status: str
    audit_log_id: UUID