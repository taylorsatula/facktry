# Phase 05 — `admit`

| Field | Value |
|---|---|
| **Status** | [ ] |
| **Depends on** | Phases 02, 03, 04 |
| **Checklist sections** | §5 (+ shared §18 rows) |
| **ADR refs** | §7.3 (admit), §5.12 (AdmissionReport), §9.1 (admit hard gates), §4 doctrine 15/16/17/19 |

## Goal

Fail-closed data admission — the only blessed path by which data becomes train-eligible — plus `generate_and_admit`, the single sanctioned synthetic pipeline. No admitted data, no training; this phase makes that physically true.

## In scope (`facktry/admit/`)

### Row model
`DataRow` (internal, not a new ontology export): row id, split (`train|dev|seal` — seal rows never admitted for training), visible input (messages/turns), target, dependence keys (dict), source class, teacher id (nullable), labels/tags, transformation policy id, provenance refs. Rows carry a row hash.

### `admit(store, objective_id, rows, *, for_training: bool) -> AdmissionReport`
Runs every check from ADR §7.3.1, collects `GateResult`s, emits an `AdmissionReport` artifact, returns it with pass/fail:

1. **Schema/structure** — required fields, types; dialogue rows: valid role alternation/turn structure. Runs at scenario construction (`validate_scenario()`) **and** on materialized rows — construction failures surface before any generate call.
2. **Dependence-key leakage** — for each configured key, train∩eval, train∩seal, eval∩seal value sets must be disjoint (row-id disjointness is *not* sufficient). Checks against both the incoming batch and already-admitted rows for the objective in the store.
3. **Diversity meters** — unique visible inputs, unique final turns, template-family distribution caps (max share per family), near-duplicate cap (normalized-text shingle overlap). Configured thresholds from objective; large N is not a pass.
4. **Attribution** — every factual claim in targets must trace to visible input, verified state, or an authorized tool result recorded on the row. Rows whose target contains content only present in generator-side hidden context (the generator must declare its context; admit diffs) are hard rejects.
5. **Controlled vocabs** — labels/tags/transforms within declared enums.
6. **Mixture** — observed counts vs `TargetShape` floors/caps when the objective declares one; violations hard or soft per objective config; soft violations still recorded on the report.
7. **Source class** — every row labeled; any attempt to persist a row whose payload is raw private source → hard fail (store layer independently refuses `private_raw` artifacts).
8. **Teacher identity** — synthetic rows must name a teacher; teacher must be the frozen base or an explicit ancestor tuple unless the objective records a self-distill waiver.
9. **Suite pin** — `for_training=True` requires `govern.suite_pin_required` to pass first.

Reject-reason histogram (per check, counts) is mandatory on the report even when passing. Report includes: input artifact hashes, keep/reject counts, overlap matrix, near-dupe/template stats, mixture deltas, teacher id, transformation policy + seeds, frozen suite hash, gate results, pass/fail. **Train stages later must reference a passing report hash** — expose `store.latest_passing_admission(objective_id)` (already in store queries).

### `generate_and_admit(store, objective_id, plan) -> AdmissionReport`
ADR §7.3.2 pipeline, exactly this order:
1. Construct scenarios with explicit verified state; `validate_scenario()` each (structure failures die here).
2. Generate a bounded candidate batch via an injected `GeneratorBackend` protocol (`generate(scenarios, seed) -> candidates`) — **more candidates than keep target**. Core ships no GPU generator; tests use a fake backend.
3. Deterministic filter: grounding, unsupported actions, structure, privacy patterns (configured regex/canary lists).
4. `admit()` the survivors; require reject-reason histogram + coverage floors (min keeps per slice when configured).
5. Only then is the mixture smoke-train eligible (enforcement lands with train in phase 11 via admission-hash checks).

**Parallel generation:** deterministic global candidate indices (`seed + global_index` derivation); each part writes a manifest (part id, index range, seed, counts); merge is concatenation under index order — never a resample. Merged output hash reproducible from manifests alone.

## Out of scope

- Real LLM generator backends (domain packs / later integration; the protocol is the deliverable).
- `verify` oracles (phase 06) — admit's filters here are self-contained deterministic checks; shared privacy-pattern utilities may live in a small `facktry/patterns.py` both use.

## Fail-closed requirements

- Any hard check failure → report fails → batch unusable for training; there is no "admit anyway" flag.
- Checks run on *values*, not trust: leakage uses dependence-key value sets pulled from row payloads.
- Admission is re-run after every persist of new/changed rows (the API takes rows, not a path to skip checks).

## Tests (checklist §5 + §18 rows)

- Leakage at each dependence key detected (same `thread_id` in train+eval → fail), including leakage against previously admitted rows in store.
- Attribution: target citing a fact present only in hidden generator context → hard reject; fact present in visible input → passes.
- Role/structure construction failure raised by `validate_scenario` **before** the fake generator is invoked (assert generator not called).
- Diversity: duplicated inputs/template collapse/near-dupes rejected; large-N uniform batch fails.
- Source class: unlabeled row rejected; raw-private persist refused (store double-check).
- Teacher: specialist-teacher rows rejected without waiver; base-teacher passes.
- Suite pin: `for_training` admit denied when unpinned (§18 shared row with govern).
- Mixture floors/caps enforced vs `TargetShape`.
- `generate_and_admit` end-to-end with fake backend: construction → generate → filter → admit; histogram present; parallel-part merge is order-deterministic (same manifests → same merged hash).

## Checklist updates (same change set)

- Checklist §5 all `[x]` + its four test rows. §18: leakage, attribution, construction-failure, private-bytes, suite-pin rows `[x]`. Progress summary row 5.

## Definition of done

Admission is a real gate with a real report; pipeline works against fake backends; tests green; checklist updated.

## Handoff to phase 06

Phase 06 (verify) produces oracles that admit's grounding/unsupported-action filters and later suites will reuse. Keep admit's internal checks importable as functions so verify doesn't duplicate logic.
