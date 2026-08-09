"""Facktry domain exceptions."""

from __future__ import annotations


class SerdeError(Exception):
    """Raised when serialization / deserialization violates an invariant.

    Wraps Pydantic ``ValidationError`` in ``HashableBase.from_dict()`` so
    downstream code catches a single typed exception instead of bare
    KeyError/ValueError or framework-specific errors.
    """


class StoreError(Exception):
    """Durable storage operation failed."""


class GovernDenial(Exception):
    """Govern policy refused a requested action."""


class AdmitRejection(Exception):
    """Admission gate rejected an artifact."""


class ObjectiveLintError(Exception):
    """Objective freeze refused by lint — carries all named violations."""

    def __init__(self, violations: list[str]) -> None:
        super().__init__(" | ".join(violations))
        self.violations = violations


class ObjectiveFrozenError(ObjectiveLintError):
    """Attempt to mutate an already-frozen objective."""

    def __init__(self, objective_id: str) -> None:
        super().__init__([f"Objective {objective_id} is already frozen"])
        self.objective_id = objective_id
