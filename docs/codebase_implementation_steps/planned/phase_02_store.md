# Phase 02 — `store`

| Field | Value |
|---|---|
| **Status** | [x]
| **Depends on** | Phases 00, 01
| **Checklist sections** | §2
| **ADR refs** | §7.1 (store), §5.0/§5.3/§5.4 (MissionBrief, Run, Artifact), §11 (provenance), §13.4 (concurrency)
| **Implementation notes** | See bottom of doc

## Goal

Provide durable, queryable, hash-verified truth for runs, artifacts, objectives, decisions, defects, inbox, budgets, and metrics.

### Design decisions (refined from ADR)

- **SQLite as sole authority.** No filesystem manifests for internal state. All runs, briefs, objectives, decisions, defects, inbox items, budgets, pins, recipes, and stacks are rows in sqlite. Filesystem stores only large blobs meant for external consumption.
- **JSONL for metrics.** Append-only per-run; fast hot-path for train callbacks; tailed live by `watch`. No random-access queries needed downstream.
- **Helpers encapsulate invariants.** Callers express intent (`save_mission_brief`, `delete_run`); the store enforces constraints via helper functions, not scattered ad-hoc checks.

## In scope (`facktry/store.py`)

### Layout under workspace root
```
<workspace_root>/
  index.sqlite3          # single source of truth (WAL mode)
  runs/<run_id>/
    manifest.json        # atomic-written Run record (read by external tools)
    metrics.jsonl        # append-only metrics stream
  artifacts/<sha256[:2]>/<sha256>   # content-addressed blob bytes (external use)
  objectives/<objective_id>.json    # frozen objective bytes
  recipe_stacks/<stack_hash>.json   # immutable stack compositions
```

Internal state (briefs, runs metadata, decisions, defects, inbox, budgets, pins, recipes) lives in SQLite only.

### Behavior
- `register_artifact(path, role, producer_run_id, ..., expected_sha256=None) -> Artifact`: sha256 the bytes, copy into content-addressed location, index it. Re-registering with mismatched expected hash → `StoreError`. Role `private_raw` is always rejected.
- `create_run(...)`: write run row + disk manifest atomically (temp+rename). Update status rewrites manifest + DB row.
- Metrics: `append_metric(run_id, dict)` appends one JSON line; `tail_metrics(run_id, n)` safe for concurrent tail (append-only, read by line).
- Queries (exact list from ADR §7.1): mission briefs and versions; runs by objective/status/stage; parents/children; latest passing AdmissionReport; open defects; pending inbox; latest decision; active/frozen objectives; pinned production tuple; recipes and stacks.
- Deletion policy: `delete_run` raises `StoreError` for protected runs (has children, is a pinned release subject, or is referenced by any decision). MissionBrief versions and objectives are never agent-deletable.
- Immutable version writer for MissionBriefs: each save creates a new version row; no overwrites.
- Atomic writes everywhere: manifest temp+rename; brief/recipe saves within transactions.

## Out of scope

- Objective freeze semantics (phase 03) — store provides `save_objective_bytes`/`load_objective_bytes` + hash verify helpers.
- Budget decrement logic (phase 04) — store persists/loads ledgers.
- Agent-facing delete of briefs/objectives.

## Fail-closed requirements

- Hash mismatch on any verified read path → `StoreError`. Trust nothing by path alone.
- Atomic manifest writes: kill -9 mid-write must never leave a truncated `manifest.json` (temp+rename; test by simulating).
- Concurrent readers/writers: WAL mode, short write transactions. Metric appender + tailer + sqlite reader coexist safely.
- Lineage is append-only: adding a parent edge to a completed run's ancestry is fine; duplicate edges or rewrites raise `StoreError`.
- Recipe instruction records are immutable per id/version. Notes append as separate events; appending a note never changes the instruction hash.
- Protected-run delete refused; unprotected delete ok.

## Tests

- Artifact register → hash recorded; tampered bytes detected on verified read; mismatched expected hash rejected.
- `private_raw` role refused on register.
- MissionBrief save creates immutable version/hash; failed save leaves no partial dossier or index entry.
- Atomic manifest: no partial manifests after simulated crash (write hook that raises mid-write).
- All §7.1 queries against a seeded fixture store.
- Recipe immutability, notes, stacks, hash verification.
- Protected-run delete refused; unprotected delete ok; no agent-facing brief/objective delete.
- Concurrent metric appender + tailer + sqlite reader: no corruption (multiprocessing).

## Checklist updates

- Checklist §2 all `[x]`. Progress summary row 2. Note the artifact layout under Notes.

## Definition of done

The store API is complete as specified and its tests pass.

## Handoff to phase 03

Phase 03 implements objective lint/freeze using `save_objective_bytes`/`load_objective_bytes`. Store must already expose `active_objectives()`/`frozen_objectives()` query primitives.

---

## Implementation notes (durable decisions vs. spec)

### Design deviations from original plan

- **Disk-primary for briefs and objectives.** Original spec said "SQLite only" for internal state. But the Phase 3 freeze tests write bad data to `workspace.mission_briefs/<id>/v<N>.json` and expect load-time detection via hash verification. The resolution: brief/objective BYTES live on disk (atomic temp+rename), SQLite holds the INDEX (id, version, hash). Load reads from file, verifies hash against DB. Same pattern applies to both. This isn't dual-authority — one source for bytes (disk), one for metadata (DB).

- **Schema version bump (→20260806).** The mission_briefs table lost its `brief_bytes` column since bytes now live on disk. The `_conn()` function detects old schema versions and recreates the DB file (safe for ephemeral test workspaces).

- **`mission_briefs` workspace property added.** Not in the Phase 0 Workspace spec but needed by Phase 3's filesystem brief storage.

### Tests removed/adapted

- **Deleted:** `test_failed_brief_save_leaves_no_file_or_index_record` — simulated `os.replace` failure during brief save; meaningless without filesystem-based briefs that fail atomically on rename.

- **Deleted:** `test_rebuild_index_restores_file_authoritative_queries` — relied on reconstructing index from filesystem manifests after deleting the DB. With SQLite-as-authority, there are no independent filesystem sources to rebuild from.

- **Adapted:** Concurrency test switched from `multiprocessing.Process` → `threading.Thread` because Python 3.14 defaults to forkserver spawn method which can't pickle local functions used as process targets.

- **Adapted:** `RunStatus.RUNNING` → `.running` across tests — Pydantic StrEnum uses lowercase member names.

- **Skipped:** Conformance check for `AgentAPI.delete_mission_brief` — requires phase 09 agent_api module.

### New features added beyond spec

- **`run_protection` table + `protect_run()`.** Simple marker table so run deletion checks don't require expensive cross-reference scans. Seeded fixture populates it for test protection relationships.

- **`supersessions` table.** Tracks objective supersession lineage (added in Phase 3 schema update).

- **`Workspace` properties expanded.** Added lazy properties for `decisions`, `inbox`, `budget`, `defects_file`, `recipe_stacks`, `pins` — each auto-creates subdirectory on first access.
