from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class ValidationStatus(str, Enum):
    """
    Result of a validation rule.
    """

    PASS = "PASS"
    WARNING = "WARNING"
    REVIEW = "REVIEW"


@dataclass
class ValidationResult:
    """
    Result produced by a single validation rule.
    """

    field_id: UUID
    field_name: str
    status: ValidationStatus
    rule_name: str
    message: str
    confidence: float | None = None


class ValidationRule(ABC):
    """
    Base interface for deterministic validation rules.
    """

    @abstractmethod
    def validate(
        self,
        field,
    ) -> ValidationResult | None:
        """
        Validate one extracted field.

        Returns None when the rule does not apply
        to the supplied field.
        """
        raise NotImplementedError