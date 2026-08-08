# Phase 13 — `train` preference path (DPO or equivalent)

| Field | Value |
|---|---|
| **Status** | [ ] |
| **Depends on** | Phases 11, 12 |
| **Checklist sections** | §10 (preference rows), §5 (pair rows), §18 preference rows |
| **ADR refs** | §7.8 preference pair contract (normative), §9.3 (preference runs still pass non-preference hard suites) |

## Goal

A preference training method that obeys the pair contract end-to-end and can never trade task correctness for preference margin.

## In scope (`facktry/train/preference.py` + admit extensions)

### Pair contract enforcement (ADR §7.8 table — all rows enforced in code)
| Rule | Enforcement point |
|---|---|
| Chosen: defensible source or explicit rubric | admit: pair rows must carry `chosen_source` (rubric id, verifier name, or human fixture ref) |
| Rejected: concrete undesirable behavior | admit: `rejected_defect` tag from controlled vocab required; "random alternate" rejected |
| **Identical visible input + state both sides** | admit: hash visible-input+state of both sides; mismatch → hard reject (**§18 row**) |
| Eval pairs held out | admit: dependence-key disjointness applies to pairs (existing machinery, pair-aware keys) |
| Reference frozen, hash preserved | train: spec requires reference tuple hash; verified at load; recorded on TrainCard |
| Post-train full re-measure | decide wiring below |

### Backend
`LocalTorchDPO` behind the same `TrainBackend` plugin interface (lazy torch imports; `facktry[train]` extra). Same callbacks, metrics, TrainCard, run-dir, parent rules as SFT. `FakePreferenceBackend` in `facktry.train.testing` for CI.

### Post-preference re-measure wiring
- A preference train run's Decision **must include** the non-preference hard suites (task, grounding, privacy, retention, diversity, deployment) for the candidate — not only preference accuracy/margin. Implement as: `decide` receives the objective's full gate set; the facade's preference-measure helper assembles scorecards for preference *and* task suites before calling decide. A decide call for a preference-produced candidate missing required non-preference suite evidence → those gates fail-closed (missing evidence = failed, phase 08 rule — this phase adds the test proving the composition).
- **Preference improvement + degraded hard task gates → `correct` or `hold`, never `promote`** (§18 row).

## Out of scope

- Judge-driven preference rubrics (phase 15 judge may later supply `chosen_source`; the contract already accepts it by ref).

## Fail-closed requirements

- Pair contract violations are admit-time hard failures with named reject reasons in the histogram.
- Reference model hash drift (tampered reference) → train refuses at load.

## Tests

- **Preference pairs rejected if inputs differ** (§18 row): same text, different visible input/state hashes → hard reject with named reason.
- Missing `chosen_source` / `rejected_defect` → reject.
- Pair-level dependence-key leakage across splits → reject.
- **Preference train still fails decide when task hard gates drop** (§18 row): FakePreferenceBackend improving margin while fixture task-suite scorecard regresses below floor → decide ∈ {`correct`, `hold`}, never `promote`.
- Reference hash preservation on TrainCard; tampered reference refused.
- DPO backend registration through the same plugin registry; callbacks fire identically to SFT.

## Checklist updates (same change set)

- Checklist §10 preference rows `[x]` (method, pair contract, re-measure wiring) + its two preference test rows; §18 preference rows `[x]`. Progress summary row 10 → fully `[x]`.

## Definition of done

Preference path contract-complete with both §18 preference rows green; checklist updated.

## Handoff to phase 14

Phase 14 (play) produces trajectories that can feed both suites and preference-pair harvest. Pair builders should accept play transcripts as input sources (by artifact ref) — keep transcript schema stable.
