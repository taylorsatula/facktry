"""Deterministic hard-gate oracles — Phase 06.

Oracles turn model outputs into structured :class:`Finding`s.
LLM judges must never solely own these checks (ADR doctrine 4).

Public API
----------
.. py:data:: Finding
.. py:data:: OracleContext
.. py:function:: run_oracles(output, ctx, oracle_names=None) -> list[Finding]
.. py:function:: findings_to_gate_results(findings, gate_configs) -> list[facktry.types.GateResult]

See ADR s7.4 for the normative oracle table.
"""

from __future__ import annotations

from .types import Finding, OracleContext
from .core import run_oracles, findings_to_gate_results

__all__ = [
    "OracleContext",
    "Finding",
    "run_oracles",
    "findings_to_gate_results",
]
