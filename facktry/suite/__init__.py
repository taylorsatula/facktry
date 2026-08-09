"""Frozen, content-hashed suites with sealed custody and paired comparison.

Public API
----------
.. py:class:: Suite
.. py:class:: SuiteCase
.. py:class:: ModelBackend
.. py:class:: CompareReport
.. py:function:: run_suite(store, suite_ref, subject, backend, seeds, decode) -> Scorecard
.. py:function:: compare(store, suite_ref, tuples, backend_factory, margins) -> CompareReport
.. py:function:: pin_suites(store, objective_id, suite_refs) -> None
"""
from .types import (
    CaseKind,
    CompareReport,
    ModelBackend,
    ModelOutput,
    Suite,
    SuiteCase,
)
from .core import run_suite, compare, pin_suites

__all__ = [
    "CompareReport",
    "ModelBackend",
    "ModelOutput",
    "CaseKind",
    "Suite",
    "SuiteCase",
    "compare",
    "pin_suites",
    "run_suite",
]
