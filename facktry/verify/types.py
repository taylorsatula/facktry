"""Core types for the verify module.

Finding      -- single oracle observation.
OracleContext -- everything an oracle needs to judge deterministically.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any

from ..errors import SerdeError
from ..hashing import hash_obj
from ..types import HashableBase

class FindingKind(StrEnum):
    "Category of a Finding (ADR s7.4)."""
    violation = "violation"
    configuration = "configuration"

class Severity(StrEnum):
    hard = "hard"
    soft = "soft"
    human = "human"
    diagnostic = "diagnostic"

class Channel(StrEnum):
    raw = "raw"
    guarded = "guarded"
    na = "n/a"

class OracleContext(HashableBase):
    visible_input: dict[str, Any]
    verified_state: dict[str, Any] | None
    authorized_tools: list[dict[str, Any]]
    tool_records: list[dict[str, Any]]
    evidence_docs: list[str]
    config: dict[str, Any]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> OracleContext:
        try:
            return cls(**d)
        except Exception as exc:
            raise SerdeError(f"Bad OracleContext: {exc}") from exc

    def content_hash(self) -> str:
        return hash_obj({k: v for k, v in self.to_dict().items() if k != "config"})

class Finding(HashableBase):
    oracle: str
    kind: FindingKind
    message: str
    structural_tags: list[str] = []

    model_config = HashableBase.model_config.copy()
    model_config.update(frozen=True)

    _HASH_FIELD_NAMES: frozenset[str] = frozenset()

    @property
    def severity(self) -> Severity:
        return Severity.hard if self.kind == FindingKind.violation else Severity.diagnostic

    @property
    def channel(self) -> Channel:
        return Channel.raw

    def to_dict(self) -> dict[str, Any]:
        return {
            "oracle": self.oracle,
            "kind": self.kind.value,
            "message": self.message,
            "structural_tags": self.structural_tags,
            "severity": self.severity.value,
            "channel": self.channel.value,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Finding:
        try:
            return cls(**d)
        except Exception as exc:
            raise SerdeError(f"Bad Finding: {exc}") from exc
