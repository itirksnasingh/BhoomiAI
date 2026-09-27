from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ReviewDecision:
    action: str
    accepted: bool
    requires_revalidation: bool
    audit_required: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "accepted": self.accepted,
            "requires_revalidation": self.requires_revalidation,
            "audit_required": self.audit_required,
            "reason": self.reason,
        }


class ReviewDecisionService:
    """
    Central workflow policy for human review.

    The existing document API remains responsible for authentication,
    persistence and audit-log creation. This service centralizes the
    meaning of reviewer actions so the frontend and backend follow
    one consistent workflow.
    """

    APPROVE = "APPROVE"
    CORRECT = "CORRECT"
    REJECT = "REJECT"

    ALLOWED_ACTIONS = {
        APPROVE,
        CORRECT,
        REJECT,
    }

    @classmethod
    def evaluate(
        cls,
        action: str,
        new_value: str | None = None,
        reason: str | None = None,
    ) -> ReviewDecision:
        normalized = str(action or "").upper().strip()

        if normalized not in cls.ALLOWED_ACTIONS:
            raise ValueError(
                f"Unsupported review action: {normalized}"
            )

        if normalized == cls.APPROVE:
            return ReviewDecision(
                action=normalized,
                accepted=True,
                requires_revalidation=True,
                audit_required=True,
                reason=reason or "Reviewer approved the extracted value.",
            )

        if normalized == cls.CORRECT:
            if not new_value or not str(new_value).strip():
                raise ValueError(
                    "A corrected value is required for CORRECT."
                )

            return ReviewDecision(
                action=normalized,
                accepted=True,
                requires_revalidation=True,
                audit_required=True,
                reason=reason or "Reviewer corrected the extracted value.",
            )

        return ReviewDecision(
            action=normalized,
            accepted=False,
            requires_revalidation=True,
            audit_required=True,
            reason=reason or "Reviewer rejected the extracted value.",
        )


__all__ = [
    "ReviewDecision",
    "ReviewDecisionService",
]
