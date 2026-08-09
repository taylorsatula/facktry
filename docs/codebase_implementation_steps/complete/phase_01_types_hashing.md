# Phase 01 — Core types & canonical hashing

| Field | Value |
|---|---|
| **Status** | [x] |
| **Depends on** | Phase 00 |
| **Checklist sections** | §1 |
| **ADR refs** | §5.0 `MissionBrief`, §5 (all core objects), §13.4 (deterministic hashing) |

## Goal

Define every ADR §5 core object as a self-validating Pydantic v2 model. Types enforce their own shape, coerce enums automatically, and reject unknown fields. Canonical JSON hashing feeds provenance.

## In scope

### `facktry/hashing.py`
- `canonical_json(obj) -> bytes` (sort keys, compact separators, utf-8).
- `hash_obj(obj) -> str`, `hash_bytes(b) -> str`, `hash_file(path) -> str` (streamed).

### `facktry/types.py`
Base class `HashableBase(pydantic.BaseModel)` provides:

- `extra="forbid"` — rejects unknown input keys (fail-closed).
- `str_strip_whitespace=False` — preserves exact bytes for hash-sensitive content.
- `to_dict()` → `model_dump(mode="json", by_alias=True)` — canonical dict matching wire format.
- `from_dict(d)` → `model_validate(d)` wrapped in `SerdeError` — same error type as the pre-Pydantic implementation.
- `store_dict` property → alias for `to_dict()`.
- `content_hash()` → SHA-256 hex over `model_dump(mode="json")` excluding derived hash fields listed in `_HASH_FIELD_NAMES`.

Enum values:

Enums use `StrEnum` so strings like `"hard"` coerce directly to `Severity.hard` during validation, and serialize back to plain strings via `mode="json"`.

- `RunStatus` (`pending|running|completed|failed|guarded|blocked`)
- `Severity` (`hard|soft|human|diagnostic`)
- `Channel` (`raw|guarded|n/a`)
- `DecisionAction` (`promote|hold|correct|abort|ask_human`)
- `SourceClass` (ADR §5.4 role list; Python name `tuple_class` maps to value `"tuple"")
- `InterventionClass` (`data|mixture|rubric|hparam|interface|stop`)
- `DefectStatus` (`open|closed|wont_fix`)
- `InboxStatus` (`pending|answered|expired`)
- `Split` (`dev|seal`)

Value objects:

- `TupleComponent(ref, hash_)` — wire-format key is `"hash"` via `Field(alias="hash")`; Python attribute avoids keyword collision.
- `BriefRef(id, version, brief_hash)` — frozen reference to an immutable MissionBrief version.

Core types (each inherits `HashableBase`; frozen where immutability is normative):

| Type | Key distinction |
|---|---|
| `Gate` / `GateResult` | GateResult extends Gate identically; severity/channel enums parsed automatically |
| `MissionBrief` | Frozen; has `supersede(**overrides)` creating new version + `parent_version` link; `_HASH_FIELD_NAMES = {brief_hash}` |
| `Objective` | Frozen; `mission_brief` typed as `BriefRef` (no longer raw dict) |
| `ReleaseTuple` | Frozen; all components are `TupleComponent`; `_HASH_FIELD_NAMES = {tuple_hash}`; `compute_tuple_hash()` recomputes from component `.hash_val` attrs |
| `Run` | Not frozen (status transitions); `mission_brief` typed as `BriefRef`; `status: RunStatus` auto-coerced |
| `Artifact` | Frozen; `_HASH_FIELD_NAMES = {sha256}` |
| `Scorecard` | `raw_channel`/`guarded_channel` mapped from wire-format keys `"raw"`/`"guarded"` via aliases; legacy `.raw`/`.guarded` properties preserved for backward compat |
| `Decision` | `action: DecisionAction` auto-parsed; `mission_brief_ref: BriefRef`; mutable default lists replaced with empty defaults |
| `Defect` | `status: DefectStatus` auto-parsed |
| `Policy` | Simple capabilities map |
| `BudgetLedger` | Numeric counters |
| `TrainCard` | Frozen; `mission_brief: BriefRef`; `recipe_adaptations` defaults to `[]` |
| `MixtureSpec` / `TargetShape` | TargetShape = MixtureSpec (same schema per ADR §5.x) |
| `AdmissionReport` | Frozen |
| `HumanInboxItem` | `status: InboxStatus` auto-parsed |
| `Recipe` | Frozen; `_HASH_FIELD_NAMES = {instruction_hash, notes_head}` |
| `RecipeStack` | Frozen; `_HASH_FIELD_NAMES = {stack_hash}` |

| Type | Key fields (ADR §5.x is normative; don't drop fields) |
|---|---|
| `Gate` / `GateResult` | name, severity, comparator, threshold, suite_ref/checker_ref, channel, observed, passed, evidence |
| `MissionBrief` | id/version, brief_hash, parent_version, operator_session_id, raw_mission, dossier, hard_gate_approvals, research_notes, objective_ref, created_at |
| `Objective` | mission_brief ref+hash, id, intent, deliverable, gates, constraints, budget, baselines, suites (with hashes), dependence_keys, mixture, policy, interface; `supersedes: str | None` |
| `ReleaseTuple` | the 8 components + `tuple_hash`; `compute_tuple_hash()` hashes component hashes |
| `Run` | run_id, objective_id, MissionBrief version/hash, stage, status, parents (id + relation label), spec, code_hash, env, hardware, inputs/outputs, guard_report, metrics_path |
| `Artifact` | path, sha256, role, producer_run_id, created_at, media_type |
| `Scorecard` | suite hash, seeds, decode hash, subject tuple hash, per-dimension aggregates, raw+guarded channel blocks, findings, slice tables, resource block |
| `Decision` | action, objective_id, MissionBrief ref, subject, gate_results, intervention, human_requests, dossier_ref, created_at |
| `Defect` | id, taxonomy, evidence, first/last run ids, interventions, status |
| `Policy` | capability allow/deny map |
| `BudgetLedger` | remaining wall time / GPU-hours / judge tokens / smoke / scale counts |
| `TrainCard` | all ADR §5.10 fields incl. repeated-example exposure |
| `MixtureSpec` / `TargetShape` | dimensions, floors, caps, quotas |
| `AdmissionReport` | all ADR §5.12 fields incl. reject-reason histogram, overlap matrix |
| `HumanInboxItem` | id, objective_id, gate_name, payload_ref, response_schema, created_at, status |

## Out of scope

- Lint/freeze logic (phase 03), compat_check (phase 04), aggregation rules (phase 08).
- Deep nested typed sub-models for opaque `dict[str, Any]` fields (gates list, dossier, etc.) — phased in as later modules land.
- No module-level behavior beyond serde/hash/validation.

## Fail-closed requirements

- Round-trip fidelity: `from_dict(to_dict(x)) == x` for every type, including nested tuples, enums, and optional fields. Pydantic's `model_validate` enforces this at parse time.
- Hash stability: same logical content → same hash across process restarts (tested via subprocess). `canonical_json(sort_keys=True)` guarantees deterministic output; `content_hash()` excludes derived hash fields so they can be recomputed.
- `tuple_hash` must change when any component hash changes. `compute_tuple_hash()` extracts from each `TupleComponent.hash_val` independently.
- Unknown enum values → `SerdeError` wrapping Pydantic `ValidationError`. No silent coercion beyond StrEnum string parsing.
- Extra fields rejected → `extra="forbid"` on `HashableBase` catches unknown keys at validation time.

## Tests

- **36 tests total** across 5 files — parametrized over all core types:
  - `test_hashing.py`: canonical JSON exact shape, SHA-256 vectors, subprocess stability.
  - `test_types_enums.py`: exact str-value sets match ADR spec; unknown enum values raise `SerdeError`.
  - `test_types_serde.py`: round-trip for all 16+ types; MissionBrief version provenance; missing required field raises `SerdeError`.
  - `test_release_tuple_hash.py`: tuple_hash differs when each component hash changes individually.
  - `test_recipe_types.py`: RecipeStack content_hash sensitive to recipe order and overrides; stable under repeated calls.

All green without warnings.

## Checklist updates

- Checklist §1 all items `[x]`. Progress summary row 1.

## Definition of done

All types are importable from `facktry.types` and their tests pass.

## Design decisions

- **Pydantic V2 over dataclasses.** Reduces ~80% of copy-pasted `to_dict`/`from_dict` boilerplate while adding automatic validation. Enums coerce transparently. `extra="forbid"` fails closed on unknown keys.
- **Frozen models where immutability is normative.** MissionBrief versions, ReleaseTuple, TrainCard, Recipe, RecipeStack are frozen (no mutation after construction). Run and mutable state containers remain unfrozen.
- **Aliases for wire-format keys.** TupleComponent uses Python attr `hash_val` with alias `"hash"` to avoid keyword collision; Scorecard uses `raw_channel`/`guarded_channel` aliased from wire keys `"raw"`/`"guarded"`. Legacy `.raw`/`.guarded` properties preserved for backward compat.
- **Content-hash excludes derived fields.** `_HASH_FIELD_NAMES` per-type set tells `content_hash()` which fields to skip — brief_hash, instruction_hash, stack_hash, tuple_hash, sha256. This prevents double-hashing and lets consumers recompute.
- **`from_dict` wraps SerdeError.** Preserves the pre-Pydantic error type for downstream code that catches it explicitly. Internal Pydantic ValidationError details visible via `cause` chain.

## Handoff to phase 02

Phase 02 (store) persists these types. `to_dict()` returns clean dicts ready for `canonical_json()`. The store does not need custom serializers. Types validate their own input via Pydantic, so `Store.save(type_instance)` can just call `type_instance.to_dict()`.
