"""Public admission API.

Every data mutation path goes through here — fail-closed gates, governed by policy
and budget, emitting a complete AdmissionReport with per-check histograms.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from ..errors import AdmitRejection, StoreError
from ..govern import BudgetCost, check_policy, charge_budget, suite_pin_required
from ..hashing import hash_obj as _hash_obj
from ..types import AdmissionReport, Channel, GateResult, SourceClass
from ._row import DataRow

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def admit(
    store: Any,
    objective_id: str,
    rows: list[dict],
    *,
    for_training: bool = True,
) -> AdmissionReport:
    """Fail-closed admission gate.

    Runs all nine checks from ADR §7.3.1, collects reject histograms, emits an
    AdmissionReport artifact, and returns it with pass/fail.

    Raises ``SuiteNotPinned`` via govern before any row-level checks when
    *for_training* is true.
    """
    from ..objective import load_objective

    obj = load_objective(store, objective_id)

    # Govern pre-checks
    if for_training:
        suite_pin_required(store, objective_id)

    check_policy(store, objective_id, "admit.run")
    charge_budget(store, objective_id, "admit.run", BudgetCost())

    # Convert input dicts to typed rows
    typed_rows = []
    for d in rows:
        try:
            typed_rows.append(DataRow.from_dict(d))
        except Exception as exc:
            raise AdmitRejection(str(exc), reason="schema_validation_error") from exc

    # Run all checks regardless of failures; aggregate full histogram
    all_rejects: Counter = Counter()
    all_gate_results: list[dict[str, Any]] = []

    # Import individual checks lazily
    from .checks import (
        attribution_check,
        diversity_check,
        leakage_check,
        mixture_check,
        schema_check,
        sealed_split_check,
        source_class_check,
        teacher_check,
        vocab_check,
    )

    checks = [
        ("schema", lambda: schema_check(typed_rows)),
        ("leakage", lambda: leakage_check(typed_rows, obj, store)),
        ("diversity", lambda: diversity_check(typed_rows, obj)),
        ("attribution", lambda: attribution_check(typed_rows)),
        ("vocab", lambda: vocab_check(typed_rows, obj)),
        ("mixture", lambda: mixture_check(typed_rows, obj)),
        ("source_class", lambda: source_class_check(typed_rows)),
        ("teacher", lambda: teacher_check(typed_rows, obj)),
        ("sealed_split", lambda: sealed_split_check(typed_rows, for_training=for_training)),
    ]

    overall_pass = True
    for name, fn in checks:
        ok, rejects = fn()
        all_rejects.update(Counter(rejects))
        overall_pass = overall_pass and ok
        all_gate_results.append(GateResult(
            name=name,
            severity="hard",
            comparator="zero",
            threshold=0,
            channel=Channel.na,
            observed=sum(rejects.values()),
            passed=ok,
            evidence=[],
        ).to_dict())

    # Keep count: only non-mixture rejections reflect actual row drops.
    # Mixture floors/caps are coverage metrics, not per-row filters.
    # TODO: track per-row survival across checks for exact counts.
    row_level_rejects = Counter(v for k, v in all_rejects.items()
                                if not k.startswith("below_floor:") and not k.startswith("above_cap:"))
    kept = max(0, len(typed_rows) - sum(row_level_rejects.values()))
    total_rejected = len(typed_rows) - kept

    # Build overlap matrix from dependence keys
    dep_keys = obj.dependence_keys or ["scenario_id"]
    split_sets: dict[str, dict[str, set]] = {}
    for r in typed_rows:
        s = r.split
        if s not in split_sets:
            split_sets[s] = {k: set() for k in dep_keys}
        for k in dep_keys:
            split_sets[s][k].add(r.dependence_keys.get(k, ""))

    overlap_matrix = {}
    splits_present = sorted(split_sets.keys())
    for i, s1 in enumerate(splits_present):
        for s2 in splits_present[i + 1:]:
            overlap_count = sum(len(split_sets[s1][k] & split_sets[s2][k])
                               for k in dep_keys)
            overlap_matrix[f"{s1}_vs_{s2}"] = overlap_count

    # Serialize split_sets as admitted_dep_keys for future cross-batch leakage checks
    admitted_dep_keys = {
        k: [{"split": s, "values": list(v)} for s, kv_map in sorted(split_sets.items())
            for k_name, v in kv_map.items() if k_name == k]
        for k in dep_keys
    }

    # Near-dup / template stats (lightweight summary)
    visible_texts = [_visible_text(r) for r in typed_rows]
    near_dupes = {"rate": _near_duplicate_rate(visible_texts)}
    families = Counter(_normalize(t)[:64] for t in visible_texts)
    template_families = dict(families.most_common())

    suites = obj.suites or {}
    seal_suite = suites.get("seal", {})
    suite_hash = seal_suite.get("hash", "") if isinstance(seal_suite, dict) else ""

    # Extract mixture deltas from rejection reasons
    mixture_deltas = {k: v for k, v in all_rejects.items()
                      if k.startswith("below_floor:") or k.startswith("above_cap:")}

    # Compute content hash over the report payload (excluding derived report_hash)
    report_payload = {
        "input_artifacts": [r.row_id for r in typed_rows],
        "keep_count": kept,
        "reject_count": total_rejected,
        "reject_reasons": dict(all_rejects),
        "overlap_matrix": overlap_matrix,
        "near_dupes": near_dupes,
        "template_families": template_families,
        "mixture_deltas": mixture_deltas,
        "teacher_id": typed_rows[0].teacher_id if typed_rows else "base",
        "transformation_policy_id": typed_rows[0].transformation_policy_id if typed_rows else "policy-1",
        "seeds": [],
        "suite_hash": suite_hash,
        "passed": overall_pass,
        "gate_results": all_gate_results,
        "admitted_dep_keys": admitted_dep_keys,
    }
    computed_hash = _hash_obj(report_payload)

    report = AdmissionReport(
        report_hash=computed_hash,
        input_artifacts=[r.row_id for r in typed_rows],
        keep_count=kept,
        reject_count=total_rejected,
        reject_reasons=dict(all_rejects),
        overlap_matrix=overlap_matrix,
        near_dupes=near_dupes,
        template_families=template_families,
        mixture_deltas=mixture_deltas,
        teacher_id=typed_rows[0].teacher_id if typed_rows else "base",
        transformation_policy_id=(typed_rows[0].transformation_policy_id if typed_rows else "policy-1"),
        seeds=[],
        suite_hash=suite_hash,
        passed=overall_pass,
        gate_results=all_gate_results,
        admitted_dep_keys=admitted_dep_keys,
    )

    # Persist in store
    store.save_admission_report(objective_id, report)

    return report


# ---------------------------------------------------------------------------
# Generate-and-admit pipeline
# ---------------------------------------------------------------------------


def generate_and_admit(
    store: Any,
    objective_id: str,
    spec: dict[str, Any],
) -> AdmissionReport:
    """ADR §7.3.2 sanctioned synthetic data pipeline.

    Order: construct → validate scenario → generate → filter → admit.
    """
    scenarios = spec.get("scenarios", [])
    generator = spec.get("generator")
    seed = spec.get("seed", 0)

    # Step 1: Construct and validate scenarios — fail fast before any generation
    for sc in scenarios:
        validate_scenario(sc)

    # Step 2: Generate candidates via backend protocol
    raw_candidates = generator.generate(scenarios, seed)

    # Step 3: Deterministic filter — catches obvious pathologies
    filtered = []
    filter_rejects: Counter = Counter()
    for candidate in raw_candidates:
        ok, reasons = _deterministic_filter(candidate)
        if not ok:
            filter_rejects.update(reasons)
        else:
            filtered.append(candidate)

    # Step 4: Admit survivors
    report = admit(store, objective_id, filtered, for_training=True)

    # Merge filter rejects into the final report; rebuild frozen model.
    merged_rejects = dict(report.reject_reasons)
    merged_rejects.update(dict(filter_rejects))
    d = report.to_dict()
    d["reject_reasons"] = merged_rejects
    d["seeds"] = [seed]
    report = AdmissionReport.from_dict(d)

    return report


# ---------------------------------------------------------------------------
# Parallel-generation merge
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GenerationPartManifest:
    part_id: int
    start_index: int
    end_index: int
    seed: int
    candidate_count: int
    kept_count: int = 0
    rejected_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "part_id": self.part_id,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "seed": self.seed,
            "candidate_count": self.candidate_count,
            "kept_count": self.kept_count,
            "rejected_count": self.rejected_count,
        }


@dataclass(frozen=True)
class MergeResult:
    rows: list[dict]
    merged_hash: str


def merge_generation_parts(parts: list[dict]) -> MergeResult:
    """Merge parallel generation parts by sorting on global index.

    Each part carries a dict with keys:
      - part_id, start_index, end_index, seed (manifest metadata)
      - candidates (list of row dicts, each carrying a row_id used as sort key)

    Output is deterministic regardless of part order.
    """
    from ..hashing import hash_obj

    all_rows = []
    for part in parts:
        candidates = part.get("candidates", [])
        for item in candidates:
            all_rows.append(item)

    # Sort by row_id (which encodes global index position)
    sorted_rows = sorted(all_rows, key=lambda r: str(r.get("row_id", "")))

    payload = {"rows": sorted_rows}
    h = hash_obj(payload)

    return MergeResult(rows=sorted_rows, merged_hash=h)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def validate_scenario(scenario: dict[str, Any]) -> None:
    """Validate scenario structure before generation.

    Raises ``AdmitRejection`` on structural failures so bad scenarios
    don't consume GPU budget.
    """
    msgs = (scenario.get("visible_input") or {}).get("messages", [])
    if not msgs:
        raise AdmitRejection(
            "Scenario visible_input has no messages",
            reason="empty_visible_input",
        )
    for i, msg in enumerate(msgs):
        role = msg.get("role") if isinstance(msg, dict) else None
        if i == 0 and role != "user":
            raise AdmitRejection(
                f"First message role is {role!r}, expected 'user'",
                reason="first_role_not_user",
            )
        expected_roles = iter(["user", "assistant"] * (len(msgs) // 2 + 1))
        for j in range(i + 1):
            next(expected_roles)
        expected_role = next(expected_roles, "user")
        if role != expected_role and i > 0:
            raise AdmitRejection(
                f"Message {i} has role {role!r}, expected {expected_role!r}",
                reason="bad_role_sequence",
            )


def _deterministic_filter(row: dict) -> tuple[bool, Counter]:
    """Thin structural pre-admit filter.

    Only catches obviously broken rows (empty content). Substantive checks
    (attribution, etc.) happen in the admit() gate — avoids duplicating logic
    and keeps the filter fast and non-opinionated about domain vocabulary.
    Returns (accepted, reject_reason_counter).
    """
    rejects = Counter()
    target = row.get("target", "").strip()
    if not target:
        rejects["empty_target"] += 1
    vis = _normalize_messages(row.get("visible_input", {}))
    if not vis:
        rejects["empty_visible_input"] += 1
    return not rejects, rejects


# ---------------------------------------------------------------------------
# Diversity helpers (also usable from checks.py)
# ---------------------------------------------------------------------------

def _visible_text(row: DataRow) -> str:
    return row._text_of_messages()


def _normalize(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def _near_duplicate_rate(texts: list[str], k: int = 4) -> float:
    if len(texts) <= 1:
        return 0.0
    shingles_set = {_shingles(t) for t in texts}
    n = len(shingles_set)
    total_pairs = len(texts) * (len(texts) - 1) / 2
    dup_pairs = 0
    s_list = list(shingles_set)
    for i in range(n):
        for j in range(i + 1, n):
            sim = _jaccard(s_list[i], s_list[j])
            if sim >= 0.85:
                dup_pairs += 1
    return dup_pairs / total_pairs if total_pairs else 0.0


def _shingles(text: str, k: int = 4) -> frozenset[str]:
    norm = _normalize(text)
    if len(norm) < k:
        return frozenset({norm}) if norm else frozenset()
    return frozenset(norm[i : i + k] for i in range(len(norm) - k + 1))


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _normalize_messages(vis: dict) -> str:
    parts = []
    for m in vis.get("messages", []):
        content = m.get("content", "") if isinstance(m, dict) else ""
        if content:
            parts.append(str(content))
    return " ".join(parts)
