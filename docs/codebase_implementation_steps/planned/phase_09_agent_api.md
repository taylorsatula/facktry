# Phase 09 — `agent_api`

| Field | Value |
|---|---|
| **Status** | [ ] |
| **Depends on** | Phases 02–08 |
| **Checklist sections** | §14 |
| **ADR refs** | §5.0 `MissionBrief`, §7.0/§7.13 (elicit/agent_api), §3 (operator surfaces), §4 doctrine 1/4 (govern-enforced arrows) |

## Goal

The single governed mutation surface for the LLM agent. Every operation the agent can perform exists here with structured results, and **every mutation path passes through govern** — calling `train`/`admit`/`suite` modules directly is not the agent's API.

## In scope (`facktry/agent_api.py`)

### Result envelope
`ApiResult`: `ok: bool`, `status` string, `data` (structured payload), `error` (`{type, reason, details}` from the typed error taxonomy), `artifact_refs`. Govern denials surface as `ok=False, error.type="GovernDenial.*"` — never as tracebacks.

### Operations (ADR §7.13 table — all present; capabilities may not be dropped)
| Operation | Implementation notes |
|---|---|
| `save_mission_brief` / `show_mission_brief` / `list_mission_briefs` | phase 03 functions; save creates one immutable version/hash at the end of elicitation and never overwrites an earlier version. Recipe candidates, notes consulted, and human tradeoffs are durable planning provenance. |
| `freeze_objective` / `show_objective` / `supersede_objective` | phase 03 functions; freeze requires a complete matching MissionBrief; supersede checks policy `objective.supersede` and recipe policy/stack constraints. |
| `preflight` | `govern.preflight`. |
| `list_recipes` / `show_recipe` | Read-only curated recipe catalog and append-only notes. |
| `recommend_recipes` | Read-only ranking from target effects, Objective constraints, defects, notes, and prior outcomes; recommendations are proposals, not gates. |
| `compose_recipe_stack` | Resolve exact recipe versions, ordering, overrides, conflicts, allocation, and validation into an immutable stack; no govern bypass. |
| `append_recipe_note` | Append structured evidence after every governed recipe use, including failure/non-promotion; never edits instructions or prior notes. |
| `pin_suites` | suite registry pins + objective update (phase 07) — mutation via govern suite-pin rules. |
| `admit` / `generate_and_admit` | policy `admit.run` (+ `data.use_private` when declared) + `suite_pin_required` + budget charge. |
| `run_stage` | Runs a registered domain stage in a proper `Run` (lineage, MissionBrief version/hash, spec, code_hash, env, hardware, metrics path). Every stage requires a frozen Objective with a matching saved MissionBrief. Until phase 17, the stage registry may be empty — unregistered stage name → typed error, not improvisation. |
| `train_smoke` / `train_scale` | **Facade exists now; backend lands in phase 11.** Until a train backend is registered, both return `ok=False` with typed "no train backend" error (a real denial, not a silent pass). Enforce: admission-hash check, `smoke_then_scale` (scale), budget charge, policy `train.smoke`/`train.scale`. |
| `select_checkpoint` | Facade now; phase 12 backend. |
| `measure` / `compare` | policy `measure.sealed` where applicable; sealed custody inherited from suite (returns scorecards/aggregates only). |
| `decide` | phase 08; persists decision; creates inbox items for `human_requests`. |
| `inbox_list` / `inbox_ingest` | list pending; ingest validates response against item's `response_schema`, records reviewer identity + timestamp, marks answered, and resolves the pending human gate. Agents may read the inbox; ingest is permitted for both surfaces but schema-invalid responses are refused. |
| `defects_list` / `defects_close` | close requires a resolution note; `wont_fix` requires reason. |
| `yield_release` | **Only** after a `promote`-authorizing state: policy `serve.flip_default`, human-promote satisfied when required (ingested response artifact exists — agents may not mark human gates passed without one), then pins the tuple in store. Returns pinned tuple hash. |
| `query_*` | Read-only surface shared with the CLI: `query_objectives`, `query_runs`, `query_run`, `query_decisions`, `query_defects`, `query_inbox`, `query_budget`, `query_pins`, `query_metrics_tail`. These are the *same store queries* the watch CLI uses in phase 10 — implement them here, import there. |

### Cross-cutting
- Secrets: operation specs reference secret *names*; values expand from a secret store (env-var backed default) at execution time and are never written into manifests, specs, or results. Test asserts secret values appear in no persisted artifact.
- Every mutating op: policy check → preflight subset where relevant → budget charge → execute → persist → structured result. `save_mission_brief` is the deliberate end-of-elicitation persistence call; experiment mutations additionally call `mission_brief_required`. Recipe retrieval is encouraged before intervention selection, during training/correction reasoning, and after human-inbox answers; every applied recipe gets an evidence-backed note after the attempt. A test walks all mutating ops with a deny-all policy and asserts every one is refused (no bypass).

## Out of scope

- Train/select backends (phases 11–12) — the facade contract and denial behavior are this phase's deliverable.
- CLI (phase 10 consumes `query_*`).

## Fail-closed requirements

- No public function in `agent_api` mutates store state without a govern check on the path (the deny-all sweep test enforces this mechanically).
- Sealed blindness holds through `measure`/`compare`/`query_*` (re-run the phase 07 blindness assertions against the facade surface).

## Tests

- Envelope shape on success and on each denial type.
- Recipe recommendations use target/defect/note fixtures; composition rejects conflicts and hard-gate weakening; notes append without changing instruction hashes.
- Save MissionBrief returns immutable version/hash; all experiment operations without a matching brief return typed `MissionBriefRequired`.
- Deny-all policy sweep over all mutators → all refused with typed errors.
- Inbox: item created by `decide(ask_human)`; schema-invalid ingest refused; valid ingest resolves the human gate and unblocks a subsequent `decide`.
- `yield_release` refused without human-promote satisfaction; succeeds after valid ingest; pins tuple.
- Secrets: configured secret name used by an op → value never in any artifact/manifest.
- `train_smoke` with no backend → typed denial (not success); `train_scale` without smoke → `SmokeGateUnsatisfied` (facade-level; end-to-end in phase 11).

## Checklist updates (same change set)

- Checklist §14 all `[x]`. Progress summary row 14. Note in §17 skills that API names are now stable enough for pass 2 (phase 17 does the actual revision).

## Definition of done

Full facade with governed mutations, structured results, inbox loop closed, release pinning gated; tests green; checklist updated.

## Handoff to phase 10

Phase 10 (watch CLI) imports `query_*` verbatim — do not create a second read layer. Auto-focus ordering (ADR §7.14.3) includes saved briefs not yet attached to a frozen Objective and is implemented as a pure function over `query_*` results so it can be unit-tested without a terminal.
