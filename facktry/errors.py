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
    """Base class for typed govern refusals.

    Subclasses carry ``reason`` (str) and ``details`` (dict[str, Any])
    so control flow keys off type alone while diagnostics are structured.
    """

    def __init__(self, message: str, *, reason: str = "", details: dict | None = None) -> None:
        super().__init__(message)
        self.reason = reason
        self.details = details or {}


class MissionBriefRequired(GovernDenial):
    """No matching saved MissionBrief version/hash for the experiment."""


class BudgetExhausted(GovernDenial):
    """Requested budget charge exceeds remaining dimensions."""


class PolicyDenied(GovernDenial):
    """Policy default-deny rejected the capability."""


class PreflightFailed(GovernDenial):
    """Machine-state or safety precondition not met."""


class CompatMismatch(GovernDenial):
    """Interface hashes drift between tuples beyond allowed diffs."""


class SmokeGateUnsatisfied(GovernDenial):
    """Smoke prerequisites for scale train not met."""


class SuiteNotPinned(GovernDenial):
    """Sealed suite hash not frozen before generate/admit-for-train."""


class AdmitRejection(GovernDenial):
    """Admission gate rejected one or more rows."""

    def __init__(self, message: str, *, reason: str = "admit_rejected", details: dict | None = None) -> None:
        super().__init__(message, reason=reason, details=details)


class ObjectiveLintError(Exception):
    """Objective freeze refused by lint — carries all named violations."""

    def __init__(self, violations: list[str]) -> None:
        super().__init__(" | ".join(violations))
        self.violations = violations


class SuiteError(Exception):
    "Raised when a suite operation violates an invariant."""
    pass


class ObjectiveFrozenError(ObjectiveLintError):
    """Attempt to mutate an already-frozen objective."""

    def __init__(self, objective_id: str) -> None:
        super().__init__([f"Objective {objective_id} is already frozen"])
        self.objective_id = objective_id
