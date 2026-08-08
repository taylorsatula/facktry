# Phase 08 — `decide`

| Field | Value |
|---|---|
| **Status** | [ ] |
| **Depends on** | Phases 04, 05, 07 |
| **Checklist sections** | §13 (+ §18 decide rows) |
| **ADR refs** | §5.0/§5.7 (MissionBrief, Decision + aggregation rules), §7.12 (decide), §5.8 (Defect), §4 doctrine 3 |

## Goal

Aggregate evidence into a deterministic `Decision`, dossier artifact, and defect updates. `decide` makes no model calls and uses no randomness.

## In scope (`facktry/decide.py`)

### API
```python
decide(store, objective_id, *,
       scorecards: list[Scorecard],
       admission: AdmissionReport | None,
       train_cards: list[TrainCard],
       budget: BudgetLedger) -> Decision
```
- Loads gate configs from the frozen objective; evaluates every gate against cited evidence (suite scorecard observations, admission report, verify findings surfaced via scorecards, train card fields).
- Applies the ADR §5.7 aggregation rules **in order** (normative — implement as explicit ordered checks, tested individually):
  1. Any failed `hard` gate → cannot `promote`.
  2. Any pending `human` gate → `ask_human` (or `hold` if inbox disabled by non-default policy).
  3. Failed hard gates with known intervention mapping → prefer `correct` while budget remains.
  4. Budget exhausted → `hold` or `abort` per objective exhaustion behavior — never silent continue.
  5. Soft failures alone → `correct` or `hold`, never `promote`.
  6. `diagnostic` failures never block or promote by themselves (may appear in dossier).
- `promote` additionally requires `human_promote` handling: when the objective's `human_promote` is true (default for model deliverables), decide returns `ask_human` for the final-promote human gate rather than `promote` directly (the actual `yield_release` happens after ingest, phase 09).

### Intervention mapping (ADR §7.12 table — implement as data, not if-else soup)
| Pattern detector | Class |
|---|---|
| Attribution/hidden-context fails | `data` |
| Mixture collapse / over-specialize | `mixture` |
| Keep-rate absurd / rubric wrong | `rubric` |
| Smoke OOM / nonfinite / unstable loss (from TrainCard + guard reports) | `hparam` |
| Train/serve/eval interface hash mismatch | `interface` |
| Budget blown | `stop` |
Each mapping emits a machine-readable hint (which gate, which evidence hash).

### Defects
- On `correct`/`abort`, upsert `Defect` records: match open defects by taxonomy + overlapping evidence; update `last_run_id` + append intervention with gate deltas; else create new. `defects_close` lands in phase 09's facade (store write primitive exists here).

### Dossier
- Written as a single `report`-role artifact (markdown): MissionBrief ref/hash, intent, subject hashes, gate table (severity, observed vs threshold, pass/fail, evidence hash), failing evidence pointers, intervention hint, budget remainder, compare summary when present. **Readable in one pass without opening other files** — the test asserts key sections exist, not formatting beauty.
- Decision persisted via store; `store.latest_decision(objective_id)` returns it.

## Out of scope

- The human inbox ingest path (phase 09 facade + phase 10 CLI). Decide only *creates* `human_requests` specs and pending inbox items via store.

## Fail-closed requirements

- Pure function of inputs + objective config + store state; no hidden global mutable state.
- A gate whose evidence is missing/unreadable counts as **failed** (fail-closed), never skipped.

## Tests

- Each aggregation rule in isolation:
  - hard fail → action ∈ {`correct`, `hold`, `abort`}, never `promote` (**§18 row**)
  - pending human gate → `ask_human` (**§18 row**)
  - budget exhausted → objective's declared exhaustion behavior
  - soft-only failures → never `promote`
  - diagnostic-only failures → no blocking effect; appears in dossier
  - missing evidence for a gate → treated as failed
  - repeated calls with identical inputs produce identical serialized Decisions (no hidden mutable state)
- Intervention mapping: each detector pattern → correct class + hint.
- Defect upsert: repeated same-failure decisions update one defect rather than spawning duplicates.
- Dossier artifact: hash-registered, contains gate table + intervention + budget sections.
- `human_promote=true` path yields `ask_human`, not bare `promote`.

## Checklist updates

- Checklist §13 all `[x]` + its two test rows; §18 decide rows `[x]`. Progress summary row 13 (note: done ahead of rows 8–12 per ADR build order).

## Definition of done

`decide` is a tested pure aggregator honoring every §5.7 rule; dossiers and defects persist.

## Handoff to phase 09

Phase 09 wraps `decide` and earlier modules in the governed facade. Its signature should accept exactly what the facade gathers from store queries.
