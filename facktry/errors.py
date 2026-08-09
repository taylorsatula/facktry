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
