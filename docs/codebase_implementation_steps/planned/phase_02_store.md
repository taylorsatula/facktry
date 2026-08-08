# Phase 02 — `store`

| Field | Value |
|---|---|
| **Status** | [ ] |
| **Depends on** | Phases 00, 01 |
| **Checklist sections** | §2 |
| **ADR refs** | §7.1 (store), §5.0/§5.3/§5.4 (MissionBrief, Run, Artifact), §11 (provenance), §13.4 (concurrency) |

## Goal

Durable, queryable, hash-verified truth for runs, artifacts, objectives, decisions, defects, inbox, budgets, and metrics. Everything later modules know comes from here.

## In scope (`facktry/store.py`, plus `facktry/errors.py` if not already present)

### Layout under workspace root
```
.facktry/
  index.sqlite3          # query index (WAL mode)
  runs/<run_id>/
    manifest.json        # atomic-written Run record
    metrics.jsonl        # append-only metrics stream
    artifacts/           # run-local large outputs (symlink or copy from store)
  artifacts/<sha256[:2]>/<sha256>   # content-addressed artifact bytes
  mission_briefs/<brief_id>/v<version>.json  # immutable saved dossiers
  objectives/<objective_id>.json    # frozen bytes (phase 03 writes these; store provides paths)
  recipes/<recipe_id>/              # parsed recipe instruction artifacts/index refs
  recipe_stacks/<stack_hash>.json   # immutable compositions
  recipe_notes/<recipe_id>.jsonl    # append-only subsequent-use notes
  decisions/<decision_id>.json
  defects.jsonl          # append-only defect events
  inbox/<item_id>.json
  budget/<objective_id>.json        # BudgetLedger
  pins/production_tuple.json        # pinned production ReleaseTuple
```

### Behavior
- `register_artifact(path, role, producer_run_id, ...) -> Artifact`: sha256 the bytes, move/copy into content-addressed location, index it. **Re-registering with a mismatched expected hash → `StoreError`.** Artifacts with role implying raw private content are refused here at the store layer as a second line of defense (admit is the first): define `SourceClass.PRIVATE_RAW = "private_raw"` as a reserved role that `register_artifact` always rejects.
- `create_run(...)` / `update_run_status(...)` / manifest writes atomic (write temp + `os.replace`).
- Metrics: `append_metric(run_id, dict)` appends one JSON line; `tail_metrics(run_id, n)` safe for concurrent tail (append-only, read by line).
- sqlite index (WAL): tables for mission briefs (brief_id, version, hash, parent_version, objective_ref, created_at), runs (objective_id, mission_brief_hash, status, stage, created_at), artifacts, lineage edges (parent → child + relation), decisions, inbox, pins. Index is a *query cache*: manifests on disk are the truth; provide `rebuild_index()`.
- Queries (exact list from ADR §7.1): mission briefs and immutable versions; runs by objective/status/stage; parents/children; recipes and immutable instruction versions; recipe notes; ranked recipe recommendations by target/objective/defects/prior outcomes; immutable RecipeStacks; latest **passing** AdmissionReport for objective; open defects; pending inbox; latest decision; active/frozen objectives; pinned production tuple; metrics tail.
- Deletion policy: `delete_run` exists but raises `StoreError` for protected runs (has children, is a pinned release subject, or is referenced by any decision). MissionBrief versions referenced by an Objective or experiment are never agent-deletable. No agent-facing delete API beyond this guarded one — archival is an overseer filesystem operation, not a store feature.

## Out of scope

- Objective freeze semantics (phase 03) — store only provides `save_objective_bytes`/`load_objective_bytes` + hash verify helpers.
- Budget decrement logic (phase 04) — store only persists/loads ledgers.

## Fail-closed requirements

- Hash mismatch on any artifact read path (`get_artifact(verify=True)`) → `StoreError`. Trust nothing by path alone.
- Atomic manifest writes: kill -9 mid-write must never leave a truncated `manifest.json` (temp+rename; test by simulating).
- Concurrent readers (one process appending metrics, another tailing + querying sqlite) must not error or corrupt. WAL mode, short write transactions.
- Lineage is append-only: adding a parent edge to a completed run's ancestry is fine; rewriting existing edges is not.
- Recipe instruction artifacts are immutable. Notes append as separately hashed events; appending a note never changes the referenced instruction hash. Recommendation results are derived read models, not new recipe instructions.

## Tests

- Artifact register → hash recorded; tampered bytes detected on verified read; mismatched expected hash rejected.
- `private_raw` role refused on register (partially satisfies checklist §18 "private raw bytes refused on artifact write paths" — admit phase adds the row-level path).
- MissionBrief save creates an immutable version/hash and never overwrites a prior version; failed save leaves no index entry or partial dossier.
- Atomic manifest: no partial manifests after simulated crash (write hook that raises mid-write).
- All §7.1 queries against a seeded fixture store, including recipe lookup/recommendation and RecipeStack reads.
- Recipe note append advances the notes head while preserving the instruction hash; attempts to rewrite prior notes are refused.
- Protected-run delete refused; unprotected delete ok.
- Concurrent metric appender + tailer + sqlite reader threads/processes: no corruption.

## Checklist updates (same change set)

- Checklist §2 all `[x]`. Progress summary row 2. Note the artifact layout under Notes.

## Definition of done

Store API complete per above, tests green, checklist updated.

## Handoff to phase 03

Phase 03 implements objective lint/freeze using `save_objective_bytes`/`load_objective_bytes`. Store must already expose `active_objectives()`/`frozen_objectives()` query primitives (index on objective records).
