"""Types for the suite module (ADR s7.5).

SuiteCase     -- individual evaluation case.
Suite         -- frozen collection of cases with content hash.
ModelBackend   -- protocol for model generation.
CompareReport -- paired comparison across release tuples.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol, TypedDict

from pydantic import ConfigDict

from ..errors import SerdeError
from ..hashing import hash_obj
from ..types import HashableBase, Split

class CaseKind(StrEnum):
    single_turn = "single_turn"
    multi_turn = "multi_turn"
    tool_episode = "tool_episode"
    preference_pair = "preference_pair"
    retention_probe = "retention_probe"
    robustness_cell = "robustness_cell"
    differential_pair = "differential_pair"


class ModelOutput(TypedDict, total=False):
    text: str
    tokens: int | None
    stop_reason: str | None


class ModelBackend(Protocol):
    def generate(
        self,
        messages: list[dict[str, Any]],
        decode_config: dict[str, Any],
        tools: list[dict[str, Any]] | None,
    ) -> ModelOutput: ...


class SuiteCase(HashableBase):
    id: str
    family: str
    split: Split
    dependence_keys: dict[str, Any]
    visible_input: dict[str, Any]
    private_state: dict[str, Any] | None = None
    authorized_tools: list[dict[str, Any]]
    verifiers: list[str]
    tags: list[str] = []
    kind: str = "single_turn"

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SuiteCase:
        try:
            return cls(**d)
        except Exception as exc:
            raise SerdeError(f"Bad SuiteCase: {exc}") from exc


class Suite(HashableBase):
    model_config = ConfigDict(frozen=True)

    id: str
    version: str
    cases: list[SuiteCase]
    metadata: dict[str, Any]
    suite_hash: str

    _HASH_FIELD_NAMES: frozenset[str] = frozenset({"suite_hash"})

    @property
    def seal_cases(self) -> list[SuiteCase]:
        return [c for c in self.cases if c.split == Split.seal]

    @property
    def dev_cases(self) -> list[SuiteCase]:
        return [c for c in self.cases if c.split == Split.dev]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Suite:
        try:
            cases_d = d.get("cases", [])
            parsed_cases = [SuiteCase.from_dict(c) for c in cases_d]
            result = {
                "id": d["id"],
                "version": d["version"],
                "cases": parsed_cases,
                "metadata": d.get("metadata", {}),
                "suite_hash": d.get("suite_hash", "a" * 64),
            }
            return cls.model_validate(result)
        except Exception as exc:
            raise SerdeError(f"Bad Suite: {exc}") from exc

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["cases"] = [c.to_dict() for c in self.cases]
        return data


class CompareReport(HashableBase):
    model_config = ConfigDict(frozen=True)

    suite_ref: list[str] | None = None
    paired_deltas: dict[str, Any]
    slices: dict[str, Any]
    margin_verdicts: dict[str, Any]
