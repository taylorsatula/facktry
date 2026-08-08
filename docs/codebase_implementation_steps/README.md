# Facktry — Codebase Implementation Steps

This directory decomposes the ADR (`/home/admin/facktry/docs/ADR.md`) into sequential implementation phases. **Do not implement the codebase in one pass.** Complete a phase, verify its definition of done, update `IMPLEMENTATION_CHECKLIST.md` in the same change set, then continue.

**Operator runtime (parallel track):** the Pi session image / `facktry run` foundation is specified in [`../PI_FOUNDATION.md`](../PI_FOUNDATION.md). It is **not** one of the harness phases below; it may proceed in parallel (F0+) and must not mark harness checklist items done or bypass future `govern`.

## How to use

1. Read `../ADR.md` and `../IMPLEMENTATION_CHECKLIST.md` first (mandatory per checklist rules). Then read the phase doc you are about to work on.
2. Each phase doc is self-contained: goal, dependencies, deliverables, fail-closed behavior, tests, checklist updates, definition of done, handoff notes.
3. Mark the phase doc's **Status** field `[~]` when you start and `[x]` when its definition of done is met. Mirror the same state in `IMPLEMENTATION_CHECKLIST.md`.
4. Phases are ordered. Do not start phase N+1 with phase N incomplete, and do not implement out-of-phase scope "early" — the phases are layered so later work lands on stable contracts.
5. Every phase ships real, fail-closed behavior with tests. No stubs that always pass, no facades that log TODO, no bypass paths around `govern`.
6. Run the full test suite (`pytest`) before marking any phase done. Earlier-phase tests must stay green.

### Phase lifecycle

Phase docs live in three directories reflecting their state:

| Directory | Meaning |
|---|---|
| `planned/` | Not yet started. Pick the lowest-numbered doc here when starting work. |
| `active/` | Currently in progress. Move the doc here when you mark its Status `[~]`. |
| `complete/` | Definition of done met, tests green, checklist updated. Move the doc here when you mark its Status `[x]`. |

**Workflow:** when starting a phase, `mv planned/phase_NN_*.md active/`; when done, `mv active/phase_NN_*.md complete/`. Only one doc should be in `active/` at a time.

## Shared conventions (binding for all phases)

- **Package:** `facktry` (importable, pip-installable, console script `facktry`). No runtime dependency on reference repositories.
- **Hashing:** canonical JSON = `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")`, then SHA-256 hex. One shared helper in `facktry/hashing.py`; every type/artifact/suite/objective hash uses it. Never hand-roll per-module hash schemes.
- **Workspace:** `.facktry/` discovered via `facktry/workspace.py`: `FACKTRY_HOME` env → walk cwd/parents for `.facktry/` → create in cwd. Agents and humans must land on the same workspace without flags.
- **Types:** dataclasses (or pydantic-free equivalents) with explicit `to_dict`/`from_dict`; enums as `str`-valued `Enum`. Typed public surfaces; explicit error types (e.g. `GovernDenial`, `AdmitRejection`, `StoreError`) — never bare `Exception` for control-flow denials.
- **Dependencies:** core depends on stdlib only (`rich` added in the watch phase). `torch`/training libs are **optional extras** (`facktry[train]`) imported lazily inside the train backend — core and tests must import and run without them.
- **Pluggable backends:** anything that needs a model (generation, suite execution, judging) talks to a narrow callable protocol so tests use fakes and real backends are injected later. Core never shells out to a GPU directly.
- **Privacy:** no raw private bytes in artifacts, manifests, logs, or test fixtures. Tests assert this on write paths.
- **Status markers:** `[ ]` not started · `[~]` in progress · `[x]` done (behavior + tests) · `[-]` waived with written reason.

## Phase index

| Phase | Doc | Deliverable | Status |
|---|---|---|---|
| 00 | [planned/phase_00_skeleton.md](planned/phase_00_skeleton.md) | Installable package, workspace discovery, gitignore, pytest scaffold | [ ] |
| 01 | [planned/phase_01_types_hashing.md](planned/phase_01_types_hashing.md) | All core types, enums, canonical hashing | [ ] |
| 02 | [planned/phase_02_store.md](planned/phase_02_store.md) | Durable store: run dirs, artifacts, sqlite index, queries, metrics | [ ] |
| 03 | [planned/phase_03_objective.md](planned/phase_03_objective.md) | Objective lint/freeze/supersede | [ ] |
| 04 | [planned/phase_04_govern_core.md](planned/phase_04_govern_core.md) | Preflight, budget ledger, policy, compat_check | [ ] |
| 05 | [planned/phase_05_admit.md](planned/phase_05_admit.md) | Fail-closed admission + generate_and_admit | [ ] |
| 06 | [planned/phase_06_verify.md](planned/phase_06_verify.md) | Deterministic oracles | [ ] |
| 07 | [planned/phase_07_suite.md](planned/phase_07_suite.md) | Suite registry, sealed blind custody, paired compare | [ ] |
| 08 | [planned/phase_08_decide.md](planned/phase_08_decide.md) | Decision aggregation, dossier, defects | [ ] |
| 09 | [planned/phase_09_agent_api.md](planned/phase_09_agent_api.md) | Full governed agent facade | [ ] |
| 10 | [planned/phase_10_watch_cli.md](planned/phase_10_watch_cli.md) | Human CLI: live monitor, status, inbox, show, ls | [ ] |
| 11 | [planned/phase_11_train_sft.md](planned/phase_11_train_sft.md) | Train plugin, SFT, callbacks, TrainCard, smoke/scale wiring | [ ] |
| 12 | [planned/phase_12_select.md](planned/phase_12_select.md) | Hard-constrained checkpoint selection | [ ] |
| 13 | [planned/phase_13_train_preference.md](planned/phase_13_train_preference.md) | Preference method + pair contract | [ ] |
| 14 | [planned/phase_14_play.md](planned/phase_14_play.md) | World protocol, subject↔partner loops | [ ] |
| 15 | [planned/phase_15_judge.md](planned/phase_15_judge.md) | Calibrated LLM judge | [ ] |
| 16 | [planned/phase_16_serve.md](planned/phase_16_serve.md) | Tuple serving, guards, canary, rollback | [ ] |
| 17 | [planned/phase_17_domain_packs_final.md](planned/phase_17_domain_packs_final.md) | Domain pack registry, skills pass 2, recipe catalog/composition, full conformance sweep | [ ] |
