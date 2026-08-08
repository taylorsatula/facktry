# Phase 12 — `select`

| Field | Value |
|---|---|
| **Status** | [ ] |
| **Depends on** | Phase 11 |
| **Checklist sections** | §11 (+ §18 select row) |
| **ADR refs** | §7.9 (select), §4 doctrine 3, Appendix B ("Success ≠ min val loss") |

## Goal

Select checkpoints by gate-constrained optimization, never by last step or loss alone.

## In scope (`facktry/select.py`)

### API
```python
select_checkpoint(store, objective_id, run_id, *,
                  soft_objectives: list[SoftObjective],
                  hard_constraints: list[HardConstraint]) -> RankingArtifact
```
- Input: a train run's checkpoint set, each checkpoint carrying its probe/gate observations (from phase 11 keep-best records) plus optional on-demand measurement via suite probes.
- Semantics (ADR §7.9, normative): **maximize configured soft objectives subject to all hard gates ≥ baseline − margin (or absolute floor)**. Checkpoints failing any hard constraint are ranked below all passing ones regardless of soft score.
- **Forbidden defaults are enforced structurally:** calling without `soft_objectives` or with a soft objective of bare train/val loss → typed refusal. Selection criteria must name gate-backed observations.
- Tie-breaking: deterministic (lower step index wins) — documented, tested.

### Output — ranking artifact (`scorecard`-role)
Candidates considered, gate matrix (checkpoint × hard/soft gate, observed/threshold/pass), winner, rationale (which soft objectives decided among hard-passing candidates), margins used. The winner becomes the **adapter component of the candidate ReleaseTuple** — emit `build_candidate_tuple(store, objective_id, winner) -> ReleaseTuple` that clones interface pins from the objective/base and inserts the winning adapter hash, computing `tuple_hash`.

### Facade wiring
`agent_api.select_checkpoint` (facade existed in phase 09) now calls this for real: budget/policy checks, persists ranking artifact + candidate tuple, returns both.

## Out of scope

- Full sealed measure of the candidate (that's `measure`/`compare` → `decide` in the control loop, already built).

## Fail-closed requirements

- No hard-gate evidence for a checkpoint → that checkpoint cannot win (fail-closed, same rule as decide).
- Objective bounds: margins/floors come from the frozen objective or explicit call args recorded in the artifact — never hardcoded defaults that silently vary.

## Tests

- **Select does not pick last step when hard probes prefer earlier** (§18 row): fixture where last step has best loss but fails a hard probe; earlier checkpoint passes → earlier wins.
- Soft-objective maximization among hard-passing candidates; missing hard-gate evidence excludes a checkpoint; deterministic tie-break.
- Refusal when soft objectives absent or loss-only.
- Gate matrix artifact: all candidates × gates present, rationale string names the deciding objectives.
- `build_candidate_tuple`: adapter swapped, interface components hash-identical to pins, `tuple_hash` correct; `compat_check` candidate-vs-base passes with `allowed_diffs={"adapter"}`.

## Checklist updates

- Checklist §11 all `[x]` + test row; §18 select row `[x]`. Progress summary row 11.

## Definition of done

Selection produces ranking artifacts, and candidate tuple construction respects the interface lock; tests pass.

## Handoff to phase 13

Phase 13 reuses select and the full measure loop. Ranking artifacts must accept preference-run checkpoint sets with the same TrainCard/checkpoint shape.
