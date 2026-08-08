# Phase 11 — `train` (plugin, SFT, callbacks, TrainCard, smoke/scale wiring)

| Field | Value |
|---|---|
| **Status** | [ ] |
| **Depends on** | Phases 04, 05, 07, 09 |
| **Checklist sections** | §10 (SFT items), §4/§14 wiring completion |
| **ADR refs** | §7.8 (train), §5.10 (TrainCard), §9.2 (train hard gates), §4 doctrine 1/9/18 |

## Goal

Weight updates as governed, carded, callback-guarded runs. After this phase, `train_smoke` and `train_scale` in the facade do real work end-to-end: admission hash → smoke → decision → scale → checkpoints, with ancestors preserved.

## In scope (`facktry/train/`)

### Plugin interface
```python
class TrainBackend(Protocol):
    method: str                      # "sft", "dpo", ...
    def train(self, spec: TrainSpec, callbacks: Callbacks) -> TrainResult: ...
```
`TrainSpec`: parent ReleaseTuple (hash-verified), admitted data refs (**passing** AdmissionReport hash required), mixture, hparams (lr, steps, batch, adapter rank within objective bounds), seeds, output run dir, decode/interface pins. `TrainResult`: checkpoint artifact refs, metrics summary, guard report, peak VRAM, wall time.

Registry: `register_backend(method, backend)`. Core ships:
- `LocalTorchSFT` (lazy `torch`/`transformers`/`peft` imports from `facktry[train]` extra): target-only loss default (prompt tokens masked), conservative default hparams (low lr, few steps, small adapter rank — objective may bound, harness never ships reckless defaults), HuggingFace + local-file model loading only.
- `FakeBackend` (in `facktry.train.testing`, importable by tests): simulates steps/loss/callbacks deterministically — this is what CI tests use; **no test requires a GPU**.

### Callbacks (ADR §7.8 mandatory — framework-agnostic `Callbacks` protocol)
1. **Nonfinite/collapse** — NaN/Inf loss or grad-norm spike beyond configured factor → run status `guarded`, save guard checkpoint, stop cleanly.
2. **Periodic mini sealed probe** — every N steps, run a tiny frozen probe suite (dedicated smoke suite ref from objective) through the current weights via a probe backend; results appended to metrics stream.
3. **Keep-best** — retain the best checkpoint under hard probe constraints (probe score + zero hard findings), not the last one.
4. **VRAM/budget envelope** — exceeding VRAM ceiling or remaining budget → stop cleanly, persist best, `guarded` or `completed` per state.

### Metrics
Append-only `metrics.jsonl` via store (`step, loss, probe scores, lr, grad norm, tokens, wall`) — same schema the watch CLI tails.

### Run semantics
- Every attempt = new run dir; init from declared parent tuple only (parent hash verified before start); **ancestor/base artifacts never overwritten** (test hashes before/after).
- Corrective training is a new run from base/ancestor — the API has no "continue from specialist" path unless the objective records a waiver.
- `train_scale` via facade requires `govern.smoke_then_scale` (already implemented phase 04 — now exercised for real): linked completed smoke + allowing Decision + compatible code_hash + compatible admission hash + memory envelope.
- Every attempt writes a complete `TrainCard` (ADR §5.10 — incl. repeated-example exposure computed from admitted rows' dependence keys, teacher/reference ids, best-checkpoint ref under gate callbacks).

## Out of scope

- Preference method (phase 13) — plugin interface must already accommodate it.
- Remote orchestration backends (ADR §12 — explicitly not core).

## Fail-closed requirements

- Train start without passing admission report hash in inputs → typed refusal (facade + module level).
- Nonfinite loss → `guarded`, checkpoint saved, no silent continuation.
- Objective hparam bounds enforced: spec outside bounds refused before any compute.

## Tests (with FakeBackend unless noted)

- End-to-end smoke→scale happy path via facade: admission hash flows, smoke Decision allows, scale permitted; run dirs, metrics, TrainCard, checkpoints all persisted and hash-registered.
- **Scale denied without passing smoke** and **on admission hash mismatch** (§18 rows — end-to-end rerun of phase 04 logic).
- **Collapse/nonfinite → guarded** (§18 row): FakeBackend configured to emit NaN → status guarded, guard checkpoint exists.
- Keep-best: probe scores peak mid-run → best checkpoint ref ≠ last step.
- Target-only loss: unit test the masking function directly (pure tensor logic, CPU-only, tiny tensors — or pure-python equivalent if torch absent: implement mask construction framework-neutral).
- Parent preservation: parent tuple artifact hashes identical before/after train.
- TrainCard completeness incl. repeat-exposure math on fixture rows.
- Hparam bounds refusal.

## Checklist updates (same change set)

- Checklist §10: plugin, SFT, target-only, parent rules, hparams, metrics, all four callbacks, TrainCard `[x]`; preference rows stay `[ ]`. Test rows: collapse `[x]`. §18 smoke/scale rows confirmed. Progress summary row 10.

## Definition of done

`agent_api.train_smoke`/`train_scale` work end-to-end with FakeBackend in CI and accept `LocalTorchSFT` registration without API change; tests green; checklist updated.

## Handoff to phase 12

Phase 12 (select) consumes checkpoint sets + their probe/hard-gate records from this phase's runs. Keep-best already records per-checkpoint probe scores in a select-friendly structure (checkpoint ref → gate observations).
