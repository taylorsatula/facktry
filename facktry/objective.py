"""Objective lint/freeze/supersede and MissionBrief persistence helpers.

The functions here orchestrate the pre-loop contract: every experiment must start
from a saved ``MissionBrief`` and a hashed, immutable ``Objective`` whose gates
and budget are machine-enforceable before any mutation occurs.

Each public function takes a *store* parameter explicitly — no hidden global state.
"""

from __future__ import annotations

import json
from typing import Any

from .errors import ObjectiveFrozenError, ObjectiveLintError, SerdeError, StoreError
from .hashing import canonical_json, hash_bytes
from .types import MissionBrief, Objective, RunStatus

# ---------------------------------------------------------------------------
# Lint violation type
# ---------------------------------------------------------------------------

class LintViolation(str):  # noqa: SLOT000
    """A named lint failure carrying human-readable detail."""

    def __new__(cls, name: str, detail: str = "") -> LintViolation:
        msg = name if not detail else f"{name}: {detail}"
        return super().__new__(cls, msg)

    @property
    def name(self) -> str:
        return self.split(":")[0].strip() if ":" in self else self

    @property
    def detail(self) -> str:
        parts = self.split(":", 1)
        return parts[1].strip() if len(parts) > 1 else ""

# ---------------------------------------------------------------------------
# Pure lint (no store access)
# ---------------------------------------------------------------------------

_REQUIRED_DOSSIER_KEYS = frozenset({
    "intent", "deliverable", "domain", "task", "audience",
    "success_case", "failure_cases", "anti_goals", "baselines",
    "must_not_regress", "constraints", "evaluation_plan",
    "questions", "assumptions",
})


def lint_objective(obj: Objective, *, store: Any = None) -> list[LintViolation]:
    """Return every violation found in *obj* against the ADR §5.1 freeze rules.

    When *store* is provided, additional checks requiring external data
    (rule 1 brief existence, rule 10 recipe refs) are also performed.
    """
    errors: list[LintViolation] = []

    # Rule 1 – MissionBrief reference resolves (needs store)
    if store is not None:
        try:
            store.get_mission_brief(obj.mission_brief.id, obj.mission_brief.version)
        except (StoreError, FileNotFoundError):
            errors.append(
                LintViolation(
                    "mission_brief missing",
                    f"{obj.mission_brief.id} v{obj.mission_brief.version}",
                )
            )

    # Rule 4 – hard gates machine-checkable or severity=human
    for g in obj.gates or []:
        sev = g.get("severity")
        if sev == "hard":
            suite_ref = g.get("suite_ref")
            checker_ref = g.get("checker_ref")
            if not suite_ref and not checker_ref:
                errors.append(
                    LintViolation(
                        "Hard gate without checker/suite ref",
                        g.get("name", "<unnamed>"),
                    )
                )

    # Rule 5 – model deliverables need paired sealed suite + base baseline
    if "release_tuple" in (obj.deliverable or ""):
        suites = obj.suites or {}
        baselines = obj.baselines or {}
        seal_suite = suites.get("seal")
        if not seal_suite:
            errors.append(LintViolation("Missing sealed suite for model deliverable"))
        elif not seal_suite.get("hash"):
            errors.append(LintViolation("Sealed suite missing hash", "suites.seal.hash"))
        if not baselines.get("base"):
            errors.append(LintViolation("Missing base baseline for model deliverable", "baselines.base"))

    # Rule 6 – sealed suite hashes present or pin_suites_on_first_iteration declared
    if not seal_suite and not (obj.constraints or {}).get("pin_suites_on_first_iteration"):
        errors.append(LintViolation(
            "No sealed suite hash and pin_suites_on_first_iteration not declared"
        ))

    # Rule 7 – budget non-negative + exhaustion behaviour defined
    budget = obj.budget or {}
    for dim in ("wall_time", "gpu_hours", "judge_tokens"):
        val = budget.get(dim)
        if isinstance(val, (int, float)) and val < 0:
            errors.append(
                LintViolation(f"Budget {dim} must be non-negative", str(val))
            )
    on_exhaustion = budget.get("on_exhaustion")
    if on_exhaustion not in ("hold", "abort"):
        errors.append(
            LintViolation(
                "Exhaustion behaviour required (hold/abort)",
                f"budget.on_exhaustion={on_exhaustion}",
            )
        )

    # Rule 8 – dependence keys non-empty when split data implied
    has_splits = bool(obj.suites or [])
    if obj.dependence_keys is not None and len(obj.dependence_keys) == 0:
        if has_splits:
            errors.append(
                LintViolation("Dependence keys empty but suites imply split data")
            )

    # Rule 9 – no_self_distill must default true, not false
    constraints = obj.constraints or {}
    if constraints.get("no_self_distill") is False:
        errors.append(LintViolation("no_self_distill=False requires explicit waiver"))

    # Rule 10 – recipe policy validates refs and doesn't weaken gates (needs store)
    recipe_policy = obj.recipe_policy or {}
    allowed = recipe_policy.get("allowed", [])
    removes_gates = recipe_policy.get("removes_hard_gates", [])
    if removes_gates:
        errors.append(
            LintViolation(
                "Recipe stack weakens hard gates",
                ", ".join(removes_gates),
            )
        )
    if allowed and store is not None:
        try:
            all_recipes = store.list_recipes()
            known_ids = {r["id"] for r in all_recipes}
            # Only enforce when some recipes are already registered
            if known_ids:
                unknown = [a for a in allowed if a not in known_ids]
                if unknown:
                    errors.append(LintViolation(
                        "Recipe refs not found", ", ".join(unknown)
                    ))
        except StoreError:
            pass

    return errors

# ---------------------------------------------------------------------------
# MissionBrief module API  (wraps store.save_mission_brief / get etc.)
# ---------------------------------------------------------------------------

def save_mission_brief(store: Any, brief: MissionBrief) -> MissionBrief:
    """Save one immutable version of *brief*. Atomic disk write + DB index."""
    return store.save_mission_brief(brief)


def load_mission_brief(store: Any, brief_id: str, version: int | None = None) -> MissionBrief:
    """Load from disk; verify hash against DB index; raise ``StoreError`` on tamper."""
    v = _latest_version(store, brief_id) if version is None else version
    return store.get_mission_brief(brief_id, v)


def show_mission_brief(store: Any, brief_id: str, version: int | None = None) -> dict[str, Any]:
    """Human-readable view of a saved brief (dict with canonical keys)."""
    b = load_mission_brief(store, brief_id, version)
    d = b.to_dict()
    d["version"] = version or _latest_version(store, brief_id)
    return d


def list_mission_briefs(store: Any, objective_id: str | None = None) -> list[MissionBrief]:
    """List newest saved versions first."""
    return store.list_mission_briefs(objective_id)


def _latest_version(store: Any, brief_id: str) -> int:
    row = store._db.execute(
        "SELECT MAX(version) AS mv FROM mission_briefs WHERE brief_id=?",
        [brief_id],
    ).fetchone()
    if row is None or row["mv"] is None:
        raise StoreError(f"No mission brief {brief_id}")
    return row["mv"]

# ---------------------------------------------------------------------------
# Objective freeze / load / supersede / list
# ---------------------------------------------------------------------------

def freeze_objective(store: Any, obj: Objective) -> Objective:
    """Lint → persist as frozen.

    All-or-nothing: any lint failure writes nothing to disk or DB.
    Raises :class:`ObjectiveFrozenError` if the id was already frozen;
    raises :class:`ObjectiveLintError` on validation issues carrying all named
    violations.
    """
    # Already-frozen check
    existing = store._db.execute(
        "SELECT 1 FROM objectives WHERE objective_id=?",
        [obj.id],
    ).fetchone()
    if existing:
        raise ObjectiveFrozenError(obj.id)

    violations = lint_objective(obj, store=store)

    # --- Brief-level checks that need the store -----------------------------------
    brief: MissionBrief | None = None
    try:
        brief = store.get_mission_brief(obj.mission_brief.id, obj.mission_brief.version)
    except (StoreError, FileNotFoundError):
        violations.append(
            LintViolation("mission_brief missing", obj.mission_brief.id)
        )
    else:
        # Rule 2 – dossier completeness
        missing = _REQUIRED_DOSSIER_KEYS - set(brief.dossier.keys())
        if missing:
            violations.append(
                LintViolation("Incomplete dossier sections", ", ".join(sorted(missing)))
            )
        # Rule 3 – hard gates have individual human approval
        approved_gates = {a.get("gate") for a in brief.hard_gate_approvals}
        for g in obj.gates or []:
            if g.get("severity") == "hard":
                name = g.get("name", "<unnamed>")
                if name not in approved_gates:
                    violations.append(
                        LintViolation(
                            "Hard gate without individual human approval",
                            name,
                        )
                    )

    if violations:
        raise ObjectiveLintError(violations)

    # Use the actual brief hash from the saved brief, not the input placeholder.
    # This ensures govern's mission_brief_required can verify the match.
    data = obj.to_dict()
    if brief is not None:
        data["mission_brief"]["brief_hash"] = brief.brief_hash

    # Enforce rule 9 default at freeze time: no_self_distill defaults true
    constraints = dict(data["constraints"]) if data["constraints"] else {}
    constraints.setdefault("no_self_distill", True)
    data["constraints"] = constraints
    b = canonical_json(data)
    h = hash_bytes(b)

    # Persist via store (writes DB row + disk file)
    store.save_objective_bytes(obj.id, b, expected_hash=h, frozen=True)

    return Objective.from_dict(json.loads(b.decode()))


def load_objective(store: Any, objective_id: str) -> Objective:
    """Load a frozen objective from disk, verifying its hash.

    Raises ``StoreError`` on tamper detection.
    """
    raw = store.load_objective_bytes(objective_id, verify=True)
    if raw is None:
        raise StoreError(f"Unknown objective {objective_id}")
    return Objective.from_dict(json.loads(raw.decode()))


def show_objective(store: Any, objective_id: str) -> dict[str, Any]:
    """Human-readable view including supersede metadata from the index."""
    obj = load_objective(store, objective_id)
    d = obj.to_dict()

    row = store._db.execute(
        "SELECT frozen FROM objectives WHERE objective_id=?",
        [objective_id],
    ).fetchone()
    d["status"] = "frozen" if row and row[0] else "draft"

    superseded_by_row = store._db.execute(
        "SELECT superseding_id FROM supersessions WHERE superseded_id=?",
        [objective_id],
    ).fetchone()
    if superseded_by_row:
        d["status"] = "superseded"
        d["superseded_by"] = superseded_by_row[0]

    return d


def supersede_objective(
    store: Any,
    old_id: str,
    new_obj: Objective,
) -> Objective:
    """Create a new objective that replaces *old_id*, leaving old bytes intact.

    The new objective must have ``supersedes=old_id``. The old record's bytes
    are never mutated; only the supersession index is updated.
    """
    if new_obj.supersedes != old_id:
        raise ObjectiveLintError(["Supersede requires supersedes=<old_id>"])

    # Validate old exists and is frozen
    old_raw = store.load_objective_bytes(old_id, verify=True)
    if old_raw is None:
        raise StoreError(f"Cannot supersede non-existent objective {old_id}")

    frozen = freeze_objective(store, new_obj)

    with store._db as conn:
        conn.execute(
            "INSERT OR IGNORE INTO supersessions "
            "(superseded_id, superseding_id) VALUES (?, ?)",
            [old_id, frozen.id],
        )

    return frozen


def list_objectives(
    store: Any,
    status: str | None = None,
) -> list[Objective]:
    """List objectives newest first, optionally filtered by active/frozen/superseded."""
    rows = store._db.execute(
        "SELECT objective_id FROM objectives ORDER BY ROWID DESC"
    ).fetchall()
    result = []
    for r in rows:
        oid = r[0]
        try:
            obj = load_objective(store, oid)
        except StoreError:
            continue
        if status:
            shown = show_objective(store, oid)
            if shown.get("status") != status:
                continue
        result.append(obj)
    return result
