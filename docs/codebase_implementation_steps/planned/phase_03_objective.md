# Phase 03 — `objective`

| Field | Value |
|---|---|
| **Status** | [ ] |
| **Depends on** | Phases 01, 02 |
| **Checklist sections** | §3 |
| **ADR refs** | §5.0–§5.1 (MissionBrief, Objective + freeze lint), §7.0/§7.2 |

## Goal

Save a complete, versioned `MissionBrief`, then lint and freeze a hashed, immutable `Objective`. Incomplete or ungrounded missions must not enter the control loop.

## In scope (`facktry/objective.py`)

### API
- `save_mission_brief(store, dossier: MissionBrief) -> SavedMissionBrief` — creates one immutable version with canonical bytes and content hash; never overwrites an earlier version. The operator calls this once at the end of elicitation.
- `load_mission_brief(store, brief_id, version=None) -> MissionBrief` — verifies the saved hash before deserialization.
- `show_mission_brief(store, brief_id, version=None) -> dict` — human/agent-readable dossier view.
- `list_mission_briefs(store, objective_id=None)` — newest saved versions first.
- Saved MissionBriefs retain recipe considerations and human tradeoffs as planning provenance.
- `lint_objective(obj: Objective) -> list[LintViolation]` — pure; returns every violation.
- `freeze_objective(store, obj) -> FrozenObjective` — runs lint; on any violation raises `ObjectiveLintError` carrying all violations; otherwise persists canonical bytes + content hash via store and registers it as active/frozen.
- `load_objective(store, objective_id) -> Objective` — reads bytes, **verifies hash before deserialize**, `StoreError` on mismatch.
- `show_objective(store, objective_id) -> dict` — human/agent-readable view.
- `supersede_objective(store, old_id, new_obj) -> FrozenObjective` — lint + freeze the new objective with `supersedes=old_id`; the old record's bytes are **never mutated** (mark it `superseded` via a separate index flag, not by editing its bytes).
- `list_objectives(store, status=None)` — open/frozen objectives for CLI auto-focus (newest first).

### Lint rules (ADR §5.0–§5.1, all mandatory)
1. A complete saved MissionBrief version/hash exists and matches the Objective's `mission_brief` reference.
2. Required universal and domain-specific MissionBrief sections are complete; raw intent alone is insufficient.
3. Every proposed hard gate has an exact definition and explicit individual human approval recorded in the brief.
4. Every hard gate is machine-checkable (has `checker_ref` or `suite_ref`) **or** explicitly severity `human`.
5. Model deliverables (`release_tuple` in deliverable) name ≥1 paired model suite and a `base` baseline.
6. Sealed suite hashes present, **or** the objective explicitly declares `pin_suites_on_first_iteration: true` (the ADR-sanctioned alternative: pin immediately as step one of the loop).
7. All budget fields non-negative; at least one exhaustion behavior defined (`hold` or `abort`).
8. `dependence_keys` non-empty when any split data will exist (objective declares suites or data stages).
9. `no_self_distill` constraint present and defaults to true when absent.
10. Recipe policy/stack refs must hash-verify, satisfy applicability/conflict/budget rules, and preserve hard gates.

## Out of scope

- `pin_suites` mechanics that touch the suite registry (phase 07 adds hash verification against real suite artifacts; this phase only validates the objective-side fields and stores pins).
- Policy enforcement of objective policy hooks (phase 04/09).

## Fail-closed requirements

- Freeze is all-or-nothing: a failed lint writes nothing.
- Frozen bytes are immutable: any code path that would rewrite an existing objective file raises `ObjectiveFrozenError`. Supersede is the only evolution mechanism.
- Load-with-tampered-bytes fails loudly (hash verify), never silently repairs.

## Tests

- MissionBrief save: one complete dossier persists with a stable version/hash; revised saves create a new version; tampered or partial records refuse load.
- Recipe considerations round-trip; recipe policy/stack lint rejects invalid refs, conflicts, budgets, or weakened gates.
- Each lint rule: one fixture violating exactly that rule → refused with that violation named; the fully-valid fixture freezes.
- Freeze persists bytes; reload round-trips; tampered file on disk → load raises.
- Freeze without a saved MissionBrief, with incomplete sections, or without individual hard-gate approvals → typed refusal.
- Mutate-after-freeze attempt refused.
- Supersede creates new id, links old, old bytes unchanged (hash equality before/after).
- `list_objectives` ordering for auto-focus.

## Checklist updates

- Checklist §3 all `[x]`. Progress summary row 3.

## Definition of done

Lint, freeze, load, supersede, and list are implemented and tested.

## Handoff to phase 04

Phase 04 consumes frozen objectives for budget and policy checks. Expose `objective.policy` and `objective.budget` as typed structures; govern must not re-parse them.
