# Phase 07 — `suite`

| Field | Value |
|---|---|
| **Status** | [ ] |
| **Depends on** | Phases 02, 04, 06 |
| **Checklist sections** | §7 (+ §18 sealed-custody, compare, suite-pin rows) |
| **ADR refs** | §7.5 (suite), §5.6 (Scorecard), §4 doctrine 6/8/20, §9.3 |

## Goal

Frozen, content-hashed eval sets with a blind custody boundary for sealed splits, pinned execution, and paired comparison across ReleaseTuples. This is the measurement backbone every later decision stands on.

## In scope (`facktry/suite/`)

### Suite definition & registry
- `SuiteCase`: id, family/slice, split (`dev|seal`), dependence keys, visible input, private state (runner-only), authorized tools, verifier configs (oracle names + params), tags, case kind (`single_turn`, `multi_turn`, `tool_episode`, `preference_pair`, `retention_probe`, `robustness_cell`, `differential_pair`).
- `Suite`: id, version, cases, content hash over canonical case bytes. Registry on disk (`suites/<id>@<hash>/suite.json`) + store index; same id with different content = different registry entry, never an overwrite.
- `pin_suites(store, objective_id, suite_refs)` — resolves refs to registered content hashes, freezes them onto the objective record (satisfies govern's `suite_pin_required` with real hashes; control-loop step 2).

### Execution
- `ModelBackend` protocol: `generate(messages, decode_config, tools) -> ModelOutput` (+ tool-call loop support for `tool_episode` and `multi_turn` kinds). Tests use scripted fake backends; real serving plugs in phase 16.
- `run_suite(store, suite_ref, subject: ReleaseTuple, backend, seeds, decode) -> Scorecard`:
  - Pins seeds, decode config, subject tuple hash on the scorecard.
  - Runs cases; runs `verify.run_oracles` per case with context from case private state/tools.
  - Populates **all** ADR §7.5 scorecard dimensions separately (task correctness, unsupported-claim rate, abstention/false-refusal, retention, robustness, privacy, preference, style distance, repetition/diversity, raw-vs-guarded, resources) — dimensions with no applicable cases are marked `n/a`, never silently zero.
  - Raw and guarded channel blocks both populated when the subject declares guards (guarded = outputs passed through the tuple's guard policy hooks; guard execution may be a lightweight policy engine here, full serve integration in phase 16).
  - Slice tables by case family; findings with severity; resource block (wall time, token counts when backend reports them).
- **Multi-turn path** (ADR doctrine 20): `multi_turn` cases execute turns with runner-side turn caps; dialogue objectives' suites must include them (a suite declaring `dialogue: true` with zero multi-turn cases fails registration lint).

### Sealed custody boundary (ADR doctrine 8 — the critical part)
- Sealed case text/private state is stored only in `suites/.../sealed/` payloads readable by the **runner**, and the planner-facing API (`run_suite`, `compare`, all `query_*` surfaces) returns only scorecards/aggregates/gate results.
- Custody mechanism: sealed execution happens through a `SealedRunner` object constructed with the suite payload; the planner-visible functions never receive or return case text — they receive a runner handle. Module-level API audit: no public function in `facktry.suite` (and later `facktry.agent_api`) returns `SuiteCase` objects for `seal` split — only counts, hashes, aggregates.
- Test must *prove* blindness: enumerate the planner-facing API surface and assert sealed case stems/private state/transcripts appear in no return value.

### `compare(store, suite_ref, tuples: dict[str, ReleaseTuple], backend_factory, margins) -> CompareReport`
- Runs the same suite (same hash, seeds, decode) on each tuple: **base**, **ancestor** (if any), **candidate**, **production wrapper** (if any) — the compare set is validated against the objective's baselines; missing `base`/`candidate` is an error.
- Emits paired deltas per dimension, slice tables, and no-worse-than verdicts vs objective margins.

## Out of scope

- `play`-driven trajectory cases (phase 14 adds the producer; suite's `multi_turn`/`tool_episode` execution here already supports transcripts).
- Judge-scored dimensions (phase 15; scorecard has the slot, marked `n/a` until calibrated judge exists).

## Fail-closed requirements

- Execution without pinned seeds/decode/subject tuple → refuse.
- Suite content hash recomputed at load; mismatch → `StoreError`.
- Sealed leakage = defect (ADR §13.1): the blindness test is mandatory, not aspirational.

## Tests

- Registry: register, hash-verify, same-id-different-content isolation.
- Runner pins seeds/decode/tuple on scorecard; refuses unpinned execution.
- All scorecard dimensions present (or explicitly `n/a`); raw+guarded channels populated when guards configured.
- **Sealed runner does not expose case text via planner-facing API** (§18 row): scripted attempt to extract stems/private state through every public function → nothing.
- **compare emits paired structure** (§18 row): fake backends with known behavior deltas → correct paired deltas + margin verdicts.
- Multi-turn case executes with turn cap respected (fake backend that never stops → capped).
- Suite-pin integration: `pin_suites` flips govern's gate from deny to allow (§18 shared row final wiring).

## Checklist updates (same change set)

- Checklist §7 all `[x]` + its test rows; §18 sealed/compare/suite-pin rows confirmed `[x]`. Progress summary row 7.

## Definition of done

Sealed custody is demonstrably blind; compare is paired and margin-aware; tests green; checklist updated.

## Handoff to phase 08

Phase 08 (decide) consumes scorecards + compare reports + gate configs. Scorecards must already carry everything decide needs (gate-evaluable observations per channel) so decide stays a pure aggregator.
