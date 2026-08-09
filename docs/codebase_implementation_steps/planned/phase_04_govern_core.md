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
`GovernDenial(Exception)` with subclasses: `MissionBriefRequired`, `BudgetExhausted`, `PolicyDenied`, `PreflightFailed`, `CompatMismatch`, `SmokeGateUnsatisfied`, `SuiteNotPinned`. Each carries `self.reason` (str) + `self.details` (dict). Subclasses implement `__init__(message, *, reason="", details=None)` so control flow keys off type alone but diagnostics are structured.

### `mission_brief_required(store, objective_id, experiment_spec=None) -> None`
Deny any experiment or objective run, including data-only investigations, when the Objective has no matching saved MissionBrief version/hash. A session draft or raw intent is not sufficient. Raises `MissionBriefRequired` with the missing/mismatched ref.

### `preflight(store, objective_id=None) -> PreflightReport`
- Resolve workspace paths; check disk headroom (configurable floor, default e.g. 5 GiB free).
- **Hardware snapshot:** read from `<workspace_root>/hardware.json` if it exists; otherwise probe CPU/RAM/GPU, write the profile, then return it. This runs automatically on first startup — no manual JSON authoring required. Subsequent preflights re-read the cached file (optional periodic refresh if desired).
- GPU probe must **degrade gracefully**: no GPU / broken NVML (e.g. driver mismatch) is recorded in the profile/report, not a crash. GPU-heavy actions later *require* a usable GPU entry.
- **GPU exclusivity refusal:** if an objective was provided and its intent would co-locate with a conflicting large model service on the same GPU, refuse. Config-driven: read `<workspace_root>/preflight.json` for `{"occupied_services":[{"name":"inference","gpus":[7],"large_model":true}]}` — match against the objective's resource needs. No hardcoded host-specific GPU indices in core (ADR §13.5). If no config file or no match, pass.
- Verify preservation/rollback paths exist (pins dir writable, run dirs creatable).

Return value `PreflightReport`: `workspace_root`, `disk_free_bytes`, `hardware` (dict), `gpus` (list of dicts; degraded entries carry `unavailable` marker), `preservation_paths_ok`, `gpu_conflict` (None or descriptive string).

> **Note:** whoever creates a `Run` extracts `report.hardware` into `Run.hardware`. Preflight owns snapshot lifecycle; Run creation consumes it.

### `BudgetLedger` operations
Field naming convention: objective budget dict uses `smoke_runs` / `scale_runs` to match the Pydantic `BudgetLedger` type exactly. No aliasing needed.

**Store layer (`facktry/store.py`) additions:**
- `seed_budget(objective_id, ledger_bytes)` — write initial `BudgetLedger` row. Called by `charge_budget` as side effect of lazy init. Transactional.
- `load_budget(objective_id) -> BudgetLedger` — deserialize stored bytes into typed ledger. Raises `StoreError` if not yet seeded.

**Govern layer (`facktry/govern.py`):**
- `BudgetCost(wall_time, gpu_hours, judge_tokens, smoke_runs, scale_runs)` — dataclass or TypedDict matching `BudgetLedger` field names exactly.
- `charge_budget(store, objective_id, action, cost: BudgetCost)` — **lazy-seeds on first call**: reads the frozen objective's budget dict into a `BudgetLedger`, persists it, then decrements atomically within a single SQLite transaction. Raises `BudgetExhausted` when any dimension would go negative after the decrement. Zero-remaining dimension blocks further charges on it.

The lazy seed avoids Phase 3 coupling but requires the charge itself be atomic (read + init-or-decrement inside one WAL transaction). The concurrent-charge test enforces this.

### Policy
- `check_policy(store, objective_id, capability: str) -> None` — allow/deny per `Policy` (objective policy overrides workspace default policy; default-deny for `data.use_private`, `data.remote_send`, `serve.flip_default`, `objective.supersede` unless explicitly allowed). Raises `PolicyDenied`.
- Capability vocabulary as constants: `train.smoke`, `train.scale`, `serve.flip_default`, `data.use_private`, `data.remote_send`, `judge.use`, `objective.supersede`, `admit.run`, `measure.sealed`, … (extensible, but deny unknown capabilities by default).

### `compat_check(a: ReleaseTuple, b: ReleaseTuple, allowed_diffs: frozenset[str] = frozenset()) -> CompatResult`
- Compares all eight interface components: tokenizer, chat_template, prompt_policy, tool_schema, decode, guards. Base_model and adapter are excluded (those are weights, not interface).
- Components named in `allowed_diffs` are exempted (e.g., `{"adapter"}` for train-vs-base compare, `{"guards"}` for raw-vs-guarded channel comparison). Uses the same mechanism — no separate flag for guard diffs.
- Returns structured `CompatResult(passed, mismatches)` naming every mismatched component; `require_compat(...)` raises `CompatMismatch`.

### `smoke_then_scale(store, objective_id, scale_spec) -> None`
Checks implemented now:
- Linked smoke run exists with status `completed`.
- `admission_report_hash` matches (or explicit declared-delta artifact present).
- Memory envelope within tolerance.

Deferred (wired up in Phases 8+11 integration):
- Smoke Decision permits scale — stubbed as `SmokeGateUnsatisfied("decision_not_yet_available")`. The `decide` module doesn't exist until Phase 8, and end-to-end wiring completes in Phase 11. The smoke gate tests exercise the run-status and admission-hash paths today.

Each unmet condition → `SmokeGateUnsatisfied` with the specific reason. Scale spec keys: `smoke_run_id`, `code_hash`, `admission_report_hash`, `memory_envelope`.

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

## Handoff backward to phase 03 (fixture correction)

Objective budget dict keys must match `BudgetLedger` field names exactly (`smoke_runs` / `scale_runs`, not `smoke` / `scale`). If phase 3's freeze path already persists objectives with the wrong keys, either alias them during deserialization or patch the fixtures. Without this, lazy-seed-on-first-charge will produce Pydantic validation errors.
