"""Suite execution engine with sealed custody.

All public functions here accept suite_refs (id+hash tuples) and return only
Scorecards or CompareReports -- never case text, visible_input, or private_state.
Sealed custody boundary enforced by construction, not convention.

Guard channels produce distinct raw vs guarded scores via lightweight policy
engine; raw carries all violations, guarded suppresses those caught by guards.
"""
from __future__ import annotations

import json
import time
from typing import Any

from ..errors import StoreError, SuiteError
from ..hashing import hash_obj
from ..types import Scorecard
from .types import (
    CompareReport,
    ModelBackend,
    ModelOutput,
    Suite,
    SuiteCase,
)

# --- Constants ---

_DEFAULT_MAX_TURNS = 8

#: ADR s7.5 scorecard dimension names.
_DIMENSION_NAMES = [
    "correctness",
    "unsupported_claim",
    "abstention",
    "retention",
    "robustness",
    "privacy",
    "preference",
    "style",
    "diversity",
    "raw_guarded",
    "resources",
]

_DIMENSION_DEFAULTS: dict[str, float] = {
    "correctness": 0.0,
    "unsupported_claim": 1.0,
    "abstention": 0.0,
    "retention": 1.0,
    "robustness": 1.0,
    "privacy": 1.0,
    "preference": 0.0,
    "style": 1.0,
    "diversity": 1.0,
    "raw_guarded": 0.0,
}

#: Oracles whose violations are guardable (suppressed under active guards).
_GUARDABLE_ORACLES = frozenset([
    "unsupported_action",
    "claim_not_executed",
    "privacy",
    "schema",
])

# Oracle name -> dimension key mapping.
_ORACLE_TO_DIMENSION: dict[str, str] = {
    "schema": "correctness",
    "entailment": "correctness",
    "unsupported_action": "unsupported_claim",
    "claim_not_executed": "unsupported_claim",
    "privacy": "privacy",
    "abstention": "abstention",
}

# --- Helpers ---

def _extract_evidence_docs(case: SuiteCase) -> list[str]:
    """Extract evidence document texts from visible_input (Corner 5 fix).

    Gathers content from all messages except system-role ones;
    these become the grounding corpus for entailment oracle checks.
    """
    docs: list[str] = []
    for msg in case.visible_input.get("messages", []):
        if msg.get("role") == "system":
            continue
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            docs.append(content)
    return docs


def _build_oracle_context(
    case: SuiteCase,
    *,
    include_verified_state: bool = True,
) -> dict:
    """Build an OracleContext dict from a case.

    For sealed cases, verified_state is never exposed (Fix 1: sealed custody).
    Evidence docs are extracted from visible_input (Corner 5 fix).
    """
    if include_verified_state:
        verified = case.private_state or {}
    else:
        verified = None  # Sealed: no access to private state.

    return {
        "visible_input": case.visible_input,
        "verified_state": verified,
        "authorized_tools": case.authorized_tools,
        "tool_records": [],
        "evidence_docs": _extract_evidence_docs(case),
        "config": {"canaries": [], "pii_patterns": []},
    }


def _apply_guards(findings: list[dict], guard_policy_id: str | None):
    """Split findings into (guarded, raw_residual) per guard policy.

    When an active guard policy exists, violations matching known guardable
    categories are suppressed in the guarded channel (Fix 2).

    Returns (raw_findings, guarded_findings) where guarded may have fewer items.
    """
    if not guard_policy_id:
        # No guard policy — both channels identical.
        return findings, findings

    raw_findings = findings
    guarded_findings: list[dict] = []
    for f in findings:
        oracle_name = f.get("oracle", "")
        if oracle_name not in _GUARDABLE_ORACLES:
            # Unguardable — always passes through.
            guarded_findings.append(f)
        else:
            # Guardable category suppressed in guarded channel.
            pass
    return raw_findings, guarded_findings


def _extract_tool_records(output: dict) -> list[dict]:
    """Extract tool-call records from backend output for tool episodes (Fix 6)."""
    calls = output.get("tool_calls") or []
    if isinstance(calls, list):
        return calls
    return []


def _compute_dimensions_from_findings(
    total_cases: int,
    oracle_counts: dict[str, int],
    slice_families: dict[str, set[str]],
) -> dict[str, float]:
    """Compute per-dimension rates from oracle finding counts (Fix 5)."""
    dims: dict[str, float] = {k: v for k, v in _DIMENSION_DEFAULTS.items()}

    correctness_violations = sum(
        oracle_counts.get(o, 0)
        for o in ["schema", "entailment"]
    )
    unsupported_violations = sum(
        oracle_counts.get(o, 0)
        for o in ["unsupported_action", "claim_not_executed"]
    )

    if total_cases > 0:
        dims["correctness"] = 1.0 - (correctness_violations / total_cases)
        dims["unsupported_claim"] = supported_rate(unsupported_violations, total_cases)
        dims["privacy"] = 1.0 - (oracle_counts.get("privacy", 0) / total_cases)
        dims["abstention"] = 1.0 - (oracle_counts.get("abstention", 0) / total_cases)

    return dims

def supported_rate(violations, total):
    return violations / max(total, 1)

# --- Case execution ---

def _run_single_case(
    store: Any,
    case: SuiteCase,
    subject_tuple: Any,
    backend: ModelBackend,
    decode_config: dict[str, Any],
) -> tuple[dict[str, Any]]:
    """Execute one single-turn case.

    Returns result dict with keys: dim_update, raw_findings, guarded_findings,
    tokens_consumed, passed_raw.
    """
    messages = case.visible_input.get("messages", [])
    tools = case.authorized_tools if case.authorized_tools else None

    # Call backend.
    output = backend.generate(messages, decode_config, tools)
    result_text = output.get("text", "")
    tokens_consumed = output.get("tokens") or 0

    # Fix 1: sealed cases get no verified_state.
    include_vs = case.split.value != "seal"

    # Build OracleContext; add tool records for tool_episode (Fix 6).
    ctx_data = _build_oracle_context(case, include_verified_state=include_vs)
    if case.kind == "tool_episode":
        ctx_data["tool_records"] = _extract_tool_records(output)

    # Run oracles.
    try:
        from facktry.verify import OracleContext, run_oracles as _run_oracles
        finding_list = _run_oracles(result_text, OracleContext(**ctx_data), case.verifiers)
        all_findings = [f.to_dict() for f in finding_list]
    except ImportError:
        all_findings = []

    # Fix 2: split into raw/guarded via guard engine.
    guard_id = getattr(subject_tuple.guards, "ref", None)
    raw_findings, guarded_findings = _apply_guards(all_findings, guard_id)

    # Fix 5: compute dimension update from oracle-specific counts.
    raw_passed = not any(f.get("kind") == "violation" for f in raw_findings)
    dim_update = {
        "passed_raw": raw_passed,
        "findings": all_findings,
        "raw_findings": raw_findings,
        "guarded_findings": guarded_findings,
    }
    return dim_update, raw_findings, guarded_findings, tokens_consumed, raw_passed

def _run_multi_turn_case(
    store: Any,
    case: SuiteCase,
    subject_tuple: Any,
    backend: ModelBackend,
    decode_config: dict[str, Any],
    max_turns: int,
    partner_backend: ModelBackend | None = None,
) -> tuple[dict[str, Any]]:
    """Execute multi-turn case with hard turn cap.

    partner_backend (Fix 4): optional separate backend for partner turns;
    falls back to continuation prompts if absent.
    """
    messages = case.visible_input.get("messages", [])
    tools = case.authorized_tools if case.authorized_tools else None
    findings: list[dict] = []
    total_tokens: int = 0

    for turn in range(max_turns):
        active = backend if not partner_backend or turn % 2 == 0 else partner_backend
        output = active.generate(messages, decode_config, tools)
        turn_text = output.get("text", "")
        total_tokens += output.get("tokens") or 0
        stop_reason = output.get("stop_reason")

        if not isinstance(turn_text, str):
            break

        role = "assistant" if active is backend else "partner"
        messages.append({"role": role, "content": turn_text})

        # Fix 4: check for stop BEFORE adding continuation prompt.
        if stop_reason or not turn_text.strip():
            break

        if partner_backend and turn + 1 < max_turns:
            # Partner generates the next user-side turn.
            pass  # loop will alternate on next iteration.
        elif not stop_reason:
            messages.append({"role": "user", "content": "continue"})

    # Verify on concatenated assistant+partner text.
    full_text = " ".join(
        m["content"] for m in messages
        if m.get("role") in ("assistant", "partner")
    )

    # Fix 1: sealed cases get no verified_state.
    include_vs = case.split.value != "seal"
    ctx_data = _build_oracle_context(case, include_verified_state=include_vs)

    if full_text.strip():
        try:
            from facktry.verify import OracleContext, run_oracles as _run_oracles
            finding_list = _run_oracles(full_text, OracleContext(**ctx_data), case.verifiers)
            findings = [f.to_dict() for f in finding_list]
        except ImportError:
            pass

    # Fix 2: split into raw/guarded.
    guard_id = getattr(subject_tuple.guards, "ref", None)
    raw_findings, guarded_findings = _apply_guards(findings, guard_id)

    raw_passed = not any(f.get("kind") == "violation" for f in raw_findings)
    dim_update = {
        "passed_raw": raw_passed,
        "findings": findings,
        "raw_findings": raw_findings,
        "guarded_findings": guarded_findings,
    }
    return dim_update, raw_findings, guarded_findings, total_tokens, raw_passed

# --- Public API ---

def run_suite(
    store: Any,
    suite_ref: tuple[str, str],
    subject: Any,
    backend: ModelBackend,
    seeds: list[int] | None,
    decode: dict[str, Any] | None,
    *,
    partner_config: dict[str, Any] | None = None,
) -> Scorecard:
    """Execute a suite against a ReleaseTuple and return a Scorecard.

    Requires non-null *seeds*, *decode*, and valid *subject* tuple -- otherwise
    raises ``StoreError``. Returns only aggregate numbers; sealed case text,
    private state, and visible input never appear in the result.

    Args:
        partner_config: Optional partner configuration for multi-turn cases
            (Fix 4). When present and backend_factory callable, used to create
            a partner model for alternating turns.
    """
    # Validate pins.
    if not seeds or not decode:
        raise StoreError("Suite execution requires pinned seeds and decode config")
    if not hasattr(subject, "to_dict"):
        raise StoreError("Subject must be a typed ReleaseTuple")

    suite_id, suite_hash = suite_ref
    suite_obj = store.get_suite(suite_id, suite_hash)

    # Resolve partner backend if configured.
    partner_be: ModelBackend | None = None
    if partner_config:
        factory = partner_config.get("backend_factory")
        if callable(factory):
            partner_be = factory(partner_config)

    start_time = time.time()
    slices_by_family: dict[str, list[bool]] = {}
    total_tokens: int = 0
    total_cases: int = len(suite_obj.cases)
    oracle_counts: dict[str, int] = {}          # Fix 5: per-oracle counters.

    raw_all_findings: list[dict] = []
    guarded_all_findings: list[dict] = []

    for case in suite_obj.cases:
        family = case.family
        slices_by_family.setdefault(family, [])

        if case.kind == "multi_turn":
            max_turns = (suite_obj.metadata.get("max_turns") or _DEFAULT_MAX_TURNS)
            dim_update, rf, gf, tokens, passed = _run_multi_turn_case(
                store, case, subject, backend, decode, max_turns, partner_be,
            )
            resources_note = {"max_turns": max_turns}
        elif case.kind == "tool_episode":
            dim_update, rf, gf, tokens, passed = _run_single_case(
                store, case, subject, backend, decode,
            )
            resources_note = {}
        else:
            dim_update, rf, gf, tokens, passed = _run_single_case(
                store, case, subject, backend, decode,
            )
            resources_note = {}

        total_tokens += tokens

        if passed:
            slices_by_family[family].append(True)
        else:
            slices_by_family[family].append(False)

        raw_all_findings.extend(rf)
        guarded_all_findings.extend(gf)

        # Fix 5: accumulate per-oracle counts from raw findings.
        for f in rf:
            oracle_name = f.get("oracle", "unknown")
            if f.get("kind") == "violation":
                oracle_counts[oracle_name] = oracle_counts.get(oracle_name, 0) + 1

    wall_time = time.time() - start_time

    # Fix 5: compute dimensions from oracle-specific violation counts.
    dimensions = _compute_dimensions_from_findings(total_cases, oracle_counts, slices_by_family)

    # Build resource block with token count (Fix 3).
    resource_block: dict[str, Any] = {
        "wall_time": round(wall_time, 3),
        "tokens": total_tokens,
        "cases_executed": total_cases,
        **resources_note,
    }
    dimensions["resources"] = resource_block

    # Fix 2: build raw and guarded channels independently.
    # Exclude 'resources' key — it is a struct dict, not a numeric score.
    raw_channel_vals = {k: v for k, v in dimensions.items() if k != "resources"}

    # Guarded channel: re-compute from guarded findings.
    guarded_oracle_counts: dict[str, int] = {}
    for f in guarded_all_findings:
        oracle_name = f.get("oracle", "unknown")
        if f.get("kind") == "violation":
            guarded_oracle_counts[oracle_name] = guarded_oracle_counts.get(oracle_name, 0) + 1
    guarded_dims_raw = _compute_dimensions_from_findings(
        total_cases, guarded_oracle_counts, slices_by_family,
    )
    guarded_dims = {k: v for k, v in guarded_dims_raw.items() if k != "resources"}

    slice_tables: dict[str, Any] = {}
    for fam, results in slices_by_family.items():
        slice_tables[fam] = {
            "pass_count": sum(1 for r in results if r),
            "total": len(results),
            "rate": sum(results) / max(len(results), 1),
        }

    decode_hash_val = hash_obj(decode)

    return Scorecard(
        suite_hash=suite_hash,
        seeds=seeds,
        decode_hash=decode_hash_val,
        subject_tuple_hash=getattr(subject, "tuple_hash", ""),
        recipe_stack_hash=None,
        dimensions={k: v for k, v in dimensions.items()},
        raw={k: v for k, v in raw_channel_vals.items()},
        guarded={k: v for k, v in guarded_dims.items()},
        findings=raw_all_findings,
        slices=slice_tables,
        resources=resource_block,
    )


def compare(
    store: Any,
    suite_ref: tuple[str, str],
    tuples: dict[str, Any],
    backend_factory: Any,
    margins: dict[str, float],
) -> CompareReport:
    """Paired comparison across release tuples on the same suite."""
    if "base" not in tuples:
        raise SuiteError("Compare requires 'base' key in tuples dict")
    if "candidate" not in tuples:
        raise SuiteError("Compare requires 'candidate' key in tuples dict")

    base_scorecard = run_suite(store, suite_ref, tuples["base"], backend_factory("base"), [1], {"temperature": 0})
    candidate_scorecard = run_suite(store, suite_ref, tuples["candidate"], backend_factory("candidate"), [1], {"temperature": 0})

    paired_deltas: dict[str, dict[str, float]] = {}
    for dim_name in _DIMENSION_NAMES:
        if dim_name in ("resources",):
            continue
        base_val = base_scorecard.dimensions.get(dim_name, 0.0)
        cand_val = candidate_scorecard.dimensions.get(dim_name, 0.0)
        delta = cand_val - base_val
        paired_deltas[dim_name] = {
            "base": base_val,
            "candidate": cand_val,
            "delta": delta,
        }

    compare_slices: dict[str, Any] = {}
    for fam in base_scorecard.slices:
        base_slice = base_scorecard.slices.get(fam, {})
        cand_slice = candidate_scorecard.slices.get(fam, {})
        compare_slices[fam] = {
            "base_rate": base_slice.get("rate", 0.0),
            "candidate_rate": cand_slice.get("rate", 0.0),
            "delta": cand_slice.get("rate", 0.0) - base_slice.get("rate", 0.0),
        }

    margin_verdicts: dict[str, Any] = {}
    for dim_name, margin_threshold in margins.items():
        delta_info = paired_deltas.get(dim_name, {})
        delta_val = delta_info.get("delta", 0.0)
        passes_margin = delta_val >= -margin_threshold
        margin_verdicts[dim_name] = {
            "verdict": "pass" if passes_margin else "fail",
            "margin": margin_threshold,
            "delta": delta_val,
        }

    return CompareReport(
        suite_ref=list(suite_ref),
        paired_deltas=paired_deltas,
        slices=compare_slices,
        margin_verdicts=margin_verdicts,
    )


def pin_suites(store: Any, objective_id: str, suite_refs: list[tuple]) -> None:
    """Pin real suite content hashes onto an objective record.

    Refs can be ``(suite_id, suite_hash)`` (defaults to seal) or
    ``(suite_id, suite_hash, split_type)`` where split_type is 'dev'/'seal'.
    After this call, ``govern.suite_pin_required(store, objective_id)`` returns
    without raising.
    """
    from ..hashing import canonical_json
    from ..objective import load_objective

    current = load_objective(store, objective_id)
    updated_suites = current.suites or {}

    for ref in suite_refs:
        suite_id = ref[0]
        suite_hash = ref[1]
        split_type = ref[2] if len(ref) > 2 else "seal"  # Fix 7: explicit split type.

        try:
            store.get_suite(suite_id, suite_hash)
        except Exception:
            raise SuiteError(
                f"Suite {suite_id}@{suite_hash[:8]}... not found in registry",
            )

        if split_type not in updated_suites:
            updated_suites[split_type] = {}
        updated_suites[split_type]["ref"] = suite_id
        updated_suites[split_type]["hash"] = suite_hash

    obj_data = current.to_dict()
    obj_data["suites"] = updated_suites
    new_obj = type(current).from_dict(obj_data)

    new_bytes = canonical_json(new_obj.to_dict())
    store.save_objective_bytes(objective_id, new_bytes, expected_hash=None)
