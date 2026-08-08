# Phase 15 — `judge`

| Field | Value |
|---|---|
| **Status** | [ ] |
| **Depends on** | Phases 07, 14 |
| **Checklist sections** | §9 |
| **ADR refs** | §7.7 (judge), §4 doctrine 2 (judges never solely own hard gates), §12 (single calibrated judge is the design) |

## Goal

Implement optional LLM assessment that earns soft-gate credit only after calibration and can never own a hard gate.

## In scope (`facktry/judge/`)

### Core
- `JudgeBackend` protocol: `assess(batch, criteria) -> list[Assessment]`. Tests use a scripted fake; real backends (local llama-server etc.) are config-injected, never hardcoded.
- `assess(store, items, criteria: Criteria) -> JudgeReport`: batch assessment; **criteria content hash recorded** on the report; per-item scores + rationales; position-swap for pairwise compares (both legs run, order recorded, disagreement surfaced as its own signal).
- `Criteria`: id, version, prompt/rubric text, scale, severity-ceiling field. **Severity ceiling is enforced structurally:** judge-derived gate results are created with severity ≤ `soft` unless calibration status promotes them — and can never be created as `hard` (hard gates come from verify/suite/admit only). A code path attempting hard-severity judge results → typed refusal.

### Calibration (the gate on the judge)
- Ship calibration fixtures under `facktry/judge/calibration/` (hash-pinned items with known-good expected assessments: clear-pass, clear-fail, borderline cases).
- `calibrate(backend, criteria) -> CalibrationResult`: run fixtures; pass when agreement with expected labels ≥ threshold (default: all clear cases correct, borderline within one step).
- **After any judge model/prompt/criteria change, calibration must pass before judge outputs count as soft gates.** Enforcement: `JudgeReport` carries `calibration_ref`; `findings_to_gate_results`-equivalent for judge output refuses soft severity without a passing calibration for the exact criteria hash + backend id → forced `diagnostic`.

### Corpus overseer
- `oversee_corpus(items, criteria) -> OverseerReport`: aggregate pathology detection (canned openings, mode collapse, cross-session repetition) over a batch — complements admit's deterministic diversity meters; output severity ≤ soft/diagnostic.

### Replay mode
- `replay(store, trajectory_refs, new_criteria)`: apply new criteria to **hash-pinned historical trajectories** without resampling; report records source trajectory hashes + new criteria hash. Population is read from store, never regenerated.

### Privacy
- Before any *remote* judge backend call: redaction pass (shared `facktry/patterns.py`) over item text; policy `data.remote_send` + `judge.use` checked by the facade. Test asserts redaction applied and policy denial blocks remote judge.

## Out of scope

- Multi-judge panels (ADR §12 — explicitly not core).

## Fail-closed requirements

- Uncalibrated judge output is diagnostic-only.
- Calibration fixtures hash-verified at load.

## Tests

- Criteria hash recorded; pairwise swap runs both legs and flags disagreement.
- Calibration: passing fake backend → soft credit allowed; failing/mismatched criteria hash → forced diagnostic.
- Hard-severity judge result attempt → typed refusal.
- Replay: same trajectory hashes, new criteria, no regeneration (fake backend call count proves it).
- Redaction: PII sentinel stripped before fake-remote backend receives payload; policy denial blocks.
- Overseer flags canned-opening fixture.

## Checklist updates

- Checklist §9 all `[x]`. Progress summary row 9.

## Definition of done

Judge outputs flow into scorecards and decisions with calibration-gated severity; tests pass.

## Handoff to phase 16

Phase 16 (serve) is the production-shaped consumer of scorecard raw/guarded channels. Judge stays offline — serve must not depend on it.
