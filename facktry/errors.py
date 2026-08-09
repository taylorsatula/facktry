"""Facktry domain exceptions."""

from __future__ import annotations


class SerdeError(Exception):
    """Raised when serialization / deserialization violates an invariant.

    Used by every ``from_dict`` implementation to reject bad input
    (missing required field, invalid enum value, etc.) instead of silently
    accepting or raising bare ``KeyError``/``ValueError``.
    """


class StoreError(Exception):
    """Durable storage operation failed."""


class GovernDenial(Exception):
    """Govern policy refused a requested action."""


class AdmitRejection(Exception):
    """Admission gate rejected an artifact."""
