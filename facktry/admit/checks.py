"""Pure admission check functions.

Each function takes rows plus optional objective/store and returns a tuple of
(passed: bool, reject_reasons: dict[str, int]). All rows are checked regardless
of failures — full histogram always produced.

Importable by Phase 6 verify without duplicating logic.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from ..errors import StoreError
from ._row import DataRow

# Stop words excluded from attribution analysis — present everywhere,
# meaningless for grounding assessment.
_STOP_WORDS = frozenset({
    "the", "is", "a", "an", "to", "of", "in", "and", "or", "it",
    "not", "but", "was", "are", "be", "has", "had", "this", "that",
    "with", "for", "on", "at", "by", "from", "they", "their", "he",
    "she", "we", "you", "me", "his", "her", "its", "our", "can",
    "could", "will", "would", "just", "also", "so", "if", "than",
})

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


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


def _visible_text(row: DataRow) -> str:
    """Concatenate visible message texts from a row's visible_input."""
    return row._text_of_messages()


def _extract_claims(target: str) -> list[str]:
    """Extract claim-like spans from target text.

    Simple heuristic: split into sentences, then extract segments containing
    proper nouns, numbers, or domain-specific terms as potential claims.
    For red-test fixtures this reduces to sentence-level chunks.
    """
    # Sentence boundary splitting
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", target) if s.strip()]
    claims = []
    for sent in sentences:
        words = sent.split()
        # A word is "claim-bearing" if it contains digits, is capitalized,
        # or matches common entity patterns
        has_entity = any(
            w.isdigit() or w[0].isupper() or w.startswith("'s") or re.search(r"\d", w)
            for w in words
        )
        if has_entity or len(words) >= 3:
            claims.append(sent)
    return claims if claims else sentences


# ---------------------------------------------------------------------------
# Check 1: Schema / structure
# ---------------------------------------------------------------------------


def schema_check(rows: list[DataRow]) -> tuple[bool, dict[str, int]]:
    """Required fields present; dialogue rows: valid role alternation.

    Sequential state machine: messages must follow user→assistant→user→...
    pattern. Tool-use loops allow consecutive assistant turns when paired
    with tool results.
    """
    rejects: Counter = Counter()
    for r in rows:
        msgs = r.visible_input.get("messages", [])
        if not msgs:
            rejects["empty_input"] += 1
            continue

        prev_role = None
        for i, msg in enumerate(msgs):
            if not isinstance(msg, dict):
                rejects["invalid_message_format"] += 1
                break
            role = msg.get("role")
            if role is None:
                rejects["missing_role"] += 1
                break

            # First message must be user
            if i == 0 and role != "user":
                rejects["first_role_not_user"] += 1
                break

            # No two consecutive roles except assistant↔tool (tool-use loop)
            if prev_role is not None:
                if role == prev_role:
                    # Only allowed: assistant after tool_result
                    if not (prev_role == "tool" and role == "assistant"):
                        rejects["consecutive_same_role"] += 1
                        break
                elif prev_role == "assistant" and role != "tool":
                    # After assistant, only user or tool result follows
                    pass  # valid transition to user

            prev_role = role
    passed = not rejects
    return passed, dict(rejects)


# ---------------------------------------------------------------------------
# Check 2: Dependence-key leakage
# ---------------------------------------------------------------------------


def leakage_check(
    rows: list[DataRow],
    objective: Any,
    store: Any,
) -> tuple[bool, dict[str, int]]:
    """Train ∩ eval ∩ seal must be disjoint at configured dependence keys.

    Checks against both the current batch and previously-admitted rows via
    the store's latest passing admission report.
    """
    rejects: Counter = Counter()
    dep_keys = (objective.dependence_keys or ["scenario_id"])

    # Build value-sets per split per key from current batch
    split_sets: dict[str, dict[str, set[str]]] = {}
    for r in rows:
        split = r.split
        if split not in split_sets:
            split_sets[split] = {k: set() for k in dep_keys}
        for k in dep_keys:
            val = r.dependence_keys.get(k, "")
            split_sets[split][k].add(val)

    # Merge with previously-admitted rows from store.
    # Use set-based dedup to avoid unbounded growth across iterations.
    try:
        prev = store.latest_passing_admission(objective.id)
        if prev is not None:
            prev_keys = prev.admitted_dep_keys or {}
            for k in dep_keys:
                entries = prev_keys.get(k, [])
                all_prev_values: dict[str, set[str]] = {}  # split → deduplicated values
                for entry in entries:
                    s = entry.get("split", "train")
                    values = entry.get("values", [])
                    all_prev_values.setdefault(s, set()).update(values)
                for s, vals in all_prev_values.items():
                    if s not in split_sets:
                        split_sets[s] = {dk: set() for dk in dep_keys}
                    split_sets[s].setdefault(k, set()).update(vals)
    except StoreError:
        pass

    # Pairwise intersection checks across all splits
    splits_present = sorted(split_sets.keys())
    for i, s1 in enumerate(splits_present):
        for s2 in splits_present[i + 1:]:
            for k in dep_keys:
                vals_s1 = split_sets[s1].get(k, set())
                vals_s2 = split_sets[s2].get(k, set())
                overlap = vals_s1 & vals_s2
                if overlap:
                    rejects[f"leakage_{k}_{min(s1,s2)}_vs_{max(s1,s2)}"] += len(overlap)

    passed = not rejects
    return passed, dict(rejects)


# ---------------------------------------------------------------------------
# Check 3: Diversity meters
# ---------------------------------------------------------------------------


def diversity_check(
    rows: list[DataRow],
    objective: Any,
) -> tuple[bool, dict[str, int]]:
    """Unique inputs/final turns, template-family caps, near-duplicate cap."""
    rejects: Counter = Counter()
    constraints = (objective.constraints or {}).get("admission", {})

    visible_texts = [_visible_text(r) for r in rows]
    unique_inputs = len(set(visible_texts))

    # Duplicate rate check
    max_dup_rate = constraints.get("max_duplicate_rate", None)
    if max_dup_rate is not None and len(visible_texts) > 0:
        dup_count = len(visible_texts) - unique_inputs
        dup_rate = dup_count / len(visible_texts)
        if dup_rate > max_dup_rate:
            rejects["duplicate_exceeds_cap"] = dup_count

    # Min unique inputs
    min_unique = constraints.get("min_unique_inputs", None)
    if min_unique is not None and unique_inputs < min_unique:
        rejects["insufficient_unique_inputs"] = unique_inputs

    # Template family share — hash normalized text as family fingerprint
    families: Counter = Counter(_normalize(t)[:64] for t in visible_texts)
    total = len(visible_texts)
    max_share = constraints.get("max_template_family_share", None)
    if max_share is not None and total > 0:
        for family, count in families.items():
            if count / total > max_share:
                rejects["template_family_collapse"] += count
                break

    # Near-duplicate detection via k=4 character shingles
    max_near_dup = constraints.get("max_near_duplicate_rate", None)
    near_dup_pairs = 0
    if max_near_dup is not None and total > 1:
        shingle_map = {i: _shingles(t) for i, t in enumerate(visible_texts)}
        for i in range(total):
            for j in range(i + 1, total):
                sim = _jaccard(shingle_map[i], shingle_map[j])
                if sim >= 0.85:
                    near_dup_pairs += 1
        near_dup_rate = near_dup_pairs / total if total else 0
        if near_dup_rate > max_near_dup:
            rejects["near_duplicate_exceeds_cap"] = near_dup_pairs

    passed = not rejects
    return passed, dict(rejects)


# ---------------------------------------------------------------------------
# Check 4: Attribution integrity (entity-based via spaCy)
# ---------------------------------------------------------------------------


def attribution_check(rows: list[DataRow]) -> tuple[bool, dict[str, int]]:
    """Every factual claim in targets must trace to visible_input.

    Uses spaCy entity extraction to identify fact-bearing spans (PERSON,
    ORG, GPE, DATE, QUANTITY, CARDINAL, etc.) in the target, then verifies
    each resolves to content in the visible input. Hidden briefs in generator
    context that leak into targets are hard fails.

    Falls back to stop-word-filtered token overlap when NER finds nothing
    (short text, non-English, model unavailable).
    """
    from .attribution import check_attribution as _check_one

    rejects: Counter = Counter()
    for r in rows:
        ok, reason = _check_one(r)
        if not ok:
            rejects[reason] += 1

    passed = not rejects
    return passed, dict(rejects)


# ---------------------------------------------------------------------------
# Check 5: Controlled vocabs
# ---------------------------------------------------------------------------


def vocab_check(
    rows: list[DataRow],
    objective: Any,
) -> tuple[bool, dict[str, int]]:
    """Labels/tags within declared enums."""
    rejects: Counter = Counter()
    controlled = (objective.constraints or {}).get("controlled_vocabs", {})
    allowed_labels = controlled.get("labels", None)

    if allowed_labels is not None:
        for r in rows:
            for lbl in r.labels:
                if lbl not in allowed_labels:
                    rejects[f"undeclared_label:{lbl}"] += 1

    passed = not rejects
    return passed, dict(rejects)


# ---------------------------------------------------------------------------
# Check 6: Mixture vs TargetShape
# ---------------------------------------------------------------------------


def mixture_check(
    rows: list[DataRow],
    objective: Any,
) -> tuple[bool, dict[str, int]]:
    """Observed counts vs TargetShape floors/caps. Violations hard or soft per config."""
    rejects: Counter = Counter()
    spec = objective.mixture
    if spec is None:
        return True, {}

    dims = spec.dimensions if hasattr(spec, "dimensions") else spec.get("dimensions", [])
    floors = spec.floors if hasattr(spec, "floors") else spec.get("floors", {})
    caps = spec.caps if hasattr(spec, "caps") else spec.get("caps", {})

    # Count source_class distribution
    dist = Counter(r.source_class.value if hasattr(r.source_class, "value") else str(r.source_class) for r in rows)

    for dim_key, floor_val in floors.items():
        observed = dist.get(dim_key, 0)
        if observed < floor_val:
            rejects[f"below_floor:{dim_key}"] += floor_val - observed

    for dim_key, cap_val in caps.items():
        observed = dist.get(dim_key, 0)
        if observed > cap_val:
            rejects[f"above_cap:{dim_key}"] += observed - cap_val

    passed = not rejects
    return passed, dict(rejects)


# ---------------------------------------------------------------------------
# Check 7: Source class
# ---------------------------------------------------------------------------


def source_class_check(rows: list[DataRow]) -> tuple[bool, dict[str, int]]:
    """Every row labeled with source_class. Raw-private rejected outright."""
    rejects: Counter = Counter()
    for r in rows:
        sc = r.source_class
        if sc is None:
            rejects["missing_or_private_raw_source"] += 1
        elif isinstance(sc, str) and sc == "private_raw":
            rejects["missing_or_private_raw_source"] += 1
        elif hasattr(sc, "value") and sc.value == "private_raw":
            rejects["missing_or_private_raw_source"] += 1
    passed = not rejects
    return passed, dict(rejects)


# ---------------------------------------------------------------------------
# Check 8: Teacher identity
# ---------------------------------------------------------------------------


def teacher_check(
    rows: list[DataRow],
    objective: Any,
) -> tuple[bool, dict[str, int]]:
    """Synthetic rows must name a teacher matching frozen base/ancestor unless waived."""
    rejects: Counter = Counter()
    constraints = objective.constraints or {}
    no_self_distill = constraints.get("no_self_distill", True)
    baselines = objective.baselines or {}
    base_ref = baselines.get("base", {}) if baselines else {}
    ancestor_ref = baselines.get("ancestor", None)

    allowed_teachers = set()
    if base_ref:
        ref_id = base_ref.get("ref", "base") if isinstance(base_ref, dict) else str(base_ref)
        allowed_teachers.add(ref_id)
        allowed_teachers.add("base")
    if ancestor_ref:
        ref_id = ancestor_ref.get("ref") if isinstance(ancestor_ref, dict) else str(ancestor_ref)
        if ref_id:
            allowed_teachers.add(ref_id)

    for r in rows:
        sc_str = r.source_class.value if hasattr(r.source_class, "value") else str(r.source_class)
        if sc_str == "synthetic" and r.teacher_id:
            if no_self_distill and r.teacher_id not in allowed_teachers:
                # Check it's not the production specialist (common anti-pattern)
                if "specialist" in str(r.teacher_id).lower() or "production" in str(r.teacher_id).lower():
                    rejects["self_distillation_risk"] += 1
                elif not allowed_teachers or r.teacher_id not in allowed_teachers:
                    rejects["teacher_not_base_or_ancestor"] += 1

    passed = not rejects
    return passed, dict(rejects)


# ---------------------------------------------------------------------------
# Check 9: Sealed split exclusion (for training use)
# ---------------------------------------------------------------------------


def sealed_split_check(
    rows: list[DataRow],
    *,
    for_training: bool,
) -> tuple[bool, dict[str, int]]:
    """Seal rows are never admitted for training."""
    rejects: Counter = Counter()
    if not for_training:
        return True, {}

    for r in rows:
        if r.split == "seal":
            rejects["sealed_split"] += 1

    passed = not rejects
    return passed, dict(rejects)
