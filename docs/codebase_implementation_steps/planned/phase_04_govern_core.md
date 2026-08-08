# Phase 04 — `govern` core (preflight, budget, policy, compat_check)

| Field | Value |
|---|---|
| **Status** | [ ] |
| **Depends on** | Phases 02, 03 |
| **Checklist sections** | §4 (all except smoke_then_scale wiring tests, which complete in phase 11) |
| **ADR refs** | §7.10 (govern), §5.0/§5.9 (MissionBrief, Policy/BudgetLedger), §5.2 (compat_check), §4 doctrine 1/4/7 |

## Goal

Implement typed, fail-closed refusals for budget exhaustion, policy denial, interface drift, and unsafe machine state.

## In scope (`facktry/govern.py`)

### Error taxonomy (`facktry/errors.py`)
`GovernDenial(Exception)` with subclasses: `MissionBriefRequired`, `BudgetExhausted`, `PolicyDenied`, `PreflightFailed`, `CompatMismatch`, `SmokeGateUnsatisfied`, `SuiteNotPinned`. Each carries a machine-readable `reason` string + details dict. Control flow keys off these types everywhere.

### `mission_brief_required(store, objective_id, experiment_spec=None) -> None`
Deny any experiment or objective run, including data-only investigations, when the Objective has no matching saved MissionBrief version/hash. A session draft or raw intent is not sufficient. Raises `MissionBriefRequired` with the missing/mismatched ref.

### `preflight(store, objective_id=None) -> PreflightReport`
- Resolve workspace paths; check disk headroom (configurable floor, default e.g. 5 GiB free); record hardware snapshot (CPU, RAM, GPU list via best-effort probe).
- GPU probe must **degrade gracefully**: no GPU / broken NVML (e.g. driver mismatch) is recorded in the report, not a crash. GPU-heavy actions later *require* a usable GPU entry in the report.
- **GPU exclusivity refusal:** if the objective's train/serve intent would co-locate with a conflicting large model service on the same GPU, refuse. Detection is config-driven (workspace `preflight.json` may declare occupied GPUs/services, e.g. a running inference server) plus a process-table probe for known server patterns — **no hardcoded host-specific GPU indices in core** (ADR §13.5). Absent any config/probe hit, pass and record "no conflicts detected".
- Verify preservation/rollback paths exist (pins dir writable, run dirs creatable).

### `BudgetLedger` operations
- `charge_budget(store, objective_id, action, cost: BudgetCost)` — atomic decrement; raises `BudgetExhausted` when the action would exceed any remaining dimension (wall time, GPU-hours, judge tokens, smoke count, scale count). Zero-remaining dimension blocks actions that consume it.
- Ledger seeded from objective budget at freeze (or first charge); persisted via store.

### Policy
- `check_policy(store, objective_id, capability: str) -> None` — allow/deny per `Policy` (objective policy overrides workspace default policy; default-deny for `data.use_private`, `data.remote_send`, `serve.flip_default`, `objective.supersede` unless explicitly allowed). Raises `PolicyDenied`.
- Capability vocabulary as constants: `train.smoke`, `train.scale`, `serve.flip_default`, `data.use_private`, `data.remote_send`, `judge.use`, `objective.supersede`, `admit.run`, `measure.sealed`, … (extensible, but deny unknown capabilities by default).

### `compat_check(a: ReleaseTuple, b: ReleaseTuple, allowed_diffs: frozenset[str] = frozenset()) -> CompatResult`
- Passes only when tokenizer, chat_template, prompt_policy, tool_schema, decode hashes match — except fields named in `allowed_diffs` (objective-declared, e.g. `{"adapter"}` for train-vs-base compare).
- Guard hash difference allowed only when the caller declares a raw-vs-guarded channel comparison.
- Returns structured result naming every mismatched component; `require_compat(...)` raises `CompatMismatch`.

### `smoke_then_scale(store, objective_id, scale_spec) -> None` (logic complete here; exercised end-to-end in phase 11)
Deny `train_scale` unless: a linked smoke run exists with status `completed`; its Decision permits scale; `code_hash` compatible; admission report hash compatible (or explicit declared-delta artifact); smoke memory envelope within tolerance. Each unmet condition → `SmokeGateUnsatisfied` with the specific reason.

### `suite_pin_required(store, objective_id) -> None`
Deny generate/admit-for-train when the objective has no frozen sealed suite hash. Raises `SuiteNotPinned`.

## Out of scope

- The agent_api facade that routes every mutation through these checks (phase 09). This phase delivers the checks themselves + tests calling them directly.
- Real GPU training integration (phase 11).

## Fail-closed requirements

- Every denial is a typed exception with a reason; mutation paths never use boolean-return-and-continue APIs.
- Budget charge is atomic under concurrent charges (single-writer transaction; test with threads).
- Unknown policy capability → deny.

## Tests

- Budget: charge decrements; insufficient → `BudgetExhausted`; concurrent charges can't overspend.
- Policy: default-deny capabilities denied; allowed capability passes; unknown capability denied.
- `compat_check`: identical tuples pass; tokenizer/chat_template/prompt_policy/tool_schema/decode drift each fail; `allowed_diffs={"adapter"}` passes adapter-only diff; guard diff only in declared raw/guarded compare. (**checklist §18: compat_check catches template/tokenizer drift**)
- `smoke_then_scale`: denied with no smoke run; denied when smoke failed; denied on admission hash mismatch (**checklist §18 both scale-denial rows** — full end-to-end reruns in phase 11).
- `mission_brief_required`: denied for missing/mismatched brief, passes for a saved matching version.
- `suite_pin_required`: denied unpinned, passes pinned (**checklist §18 suite pin row**, shared with admit phase).
- Preflight: passes on clean tmp workspace; refuses on disk-floor violation (simulate via monkeypatch); broken-GPU probe degrades to report entry.

## Checklist updates

- Checklist §4: all `[x]` except GPU-exclusivity may be `[x]` once config+probe detection works with tests; the four govern tests `[x]`. Progress summary row 4. Note under §10 tests that smoke/scale end-to-end reruns in phase 11.

## Definition of done

Typed denial machinery is complete and tested.

## Handoff to phase 05

Phase 05 (admit) must call `suite_pin_required` and `check_policy("data.use_private")`/`("admit.run")` — treat govern as a library here; the facade arrives in phase 09.
