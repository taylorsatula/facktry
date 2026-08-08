# Phase 16 — `serve`

| Field | Value |
|---|---|
| **Status** | [ ] |
| **Depends on** | Phases 02, 04, 07 |
| **Checklist sections** | §12 (+ §18 rollback row) |
| **ADR refs** | §7.11 (serve), §4 doctrine 5 (raw and guarded both first-class), §14 (human promote) |

## Goal

Load a full `ReleaseTuple`, apply versioned guards, expose raw + guarded channels, support canary and one-call rollback. Serving is where the interface lock becomes operational truth.

## In scope (`facktry/serve/`)

### Loading
- `load_tuple(store, tuple_hash) -> LoadedTuple`: resolves and hash-verifies **all eight components** (base weights ref, adapter, tokenizer, chat template, prompt policy, tool schema, decode, guards). Production paths **refuse partial loads** — any missing/mismatched component → typed refusal. Model execution goes through the same `ModelBackend` protocol as suites (a `LocalLlamaBackend`/HTTP backend plugs in; tests use fakes).

### Guards (policy as data)
- Guard policy document (hash-pinned, referenced by the tuple): ordered guard chain from the verify/patterns vocabulary — unsupported-action, claim≠execute, PII/canary, repetition, mode-leak, schema validate — each with action (`block|rewrite|fallback`) and config.
- `apply_guards(output, context, policy) -> GuardedResult`: guarded text + structured guard report (trips, actions taken).
- **Every response path emits raw and guarded records** — response log entries always carry both channels (summaries + hashes, not private payloads, per quiet-logging rule).

### Request handling
- Retries only for bounded, classifiable failures (schema-invalid, guard-trip-with-rewrite) with a retry cap; fallback response short, truthful, non-destructive.
- Logs quiet by default: summaries, errors, metrics, hashes — never private payloads.

### Canary & pins
- `canary_start(store, candidate_hash)`: side endpoint registration; paired probes (same probe suite against production pin and candidate) produce a canary report.
- `flip_default(store, candidate_hash)`: policy `serve.flip_default` + a promote-authorizing Decision required (human promote when objective demands); updates the production pin atomically.
- `rollback(store)`: **one call** restores the previous pinned tuple (pin history is append-only). 

### Service lifecycle
- A lightweight in-process HTTP service (stdlib `http.server` is acceptable; no framework dependency) exposing `/generate` (raw+guarded), `/health`. Preflight GPU-exclusivity rules apply when collocating with training on real deployments.

## Out of scope

- Production hardening (TLS, auth) — facktry serve is a local deployment harness; note in docs.

## Fail-closed requirements

- Partial/tampered tuple → no production load.
- Flip without authorizing decision/policy → typed refusal.
- Guard hash drift between decide-time evidence and serve-time load → `CompatMismatch` unless deliberately comparing channels.

## Tests

- Full-tuple load ok; each single-component-missing case refused; tampered component hash refused.
- Guards: each guard type trips on fixture output; raw record preserved alongside guarded; fallback is short/truthful.
- Retry cap respected; unclassifiable failure → fallback, no infinite retry.
- Canary: paired probe report compares candidate vs production on identical probes.
- Flip refused without decision; allowed with; pin updated atomically.
- **Rollback restores previous pinned tuple** (§18 row): pin A → flip B → rollback → pin A again, verified by hash.
- Quiet logging: private sentinel text in a request never appears in logs (summaries/hashes only).

## Checklist updates (same change set)

- Checklist §12 all `[x]` + rollback test row; §18 rollback row `[x]`. Progress summary row 12.

## Definition of done

Tuple serving with guards, dual channels, canary, flip, rollback all real and tested; checklist updated.

## Handoff to phase 17

Phase 17 finishes domain packs, skills pass 2, and the full conformance sweep. By then every module exists — the sweep is verification, not new features.
