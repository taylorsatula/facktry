# Phase 01 — Core types & canonical hashing

| Field | Value |
|---|---|
| **Status** | [x] |
| **Depends on** | Phase 00 |
| **Checklist sections** | §1 |
| **ADR refs** | §5.0 `MissionBrief`, §5 (all core objects), §13.4 (deterministic hashing) |

## Goal

Define every ADR §5 core object as a typed, serializable, hashable dataclass. These types are the contracts for later modules.

## In scope

### `facktry/hashing.py`
- `canonical_json(obj) -> bytes` (exact scheme from README: sort keys, compact separators, utf-8).
- `hash_obj(obj) -> str`, `hash_bytes(b) -> str`, `hash_file(path) -> str` (streamed, not whole-file read).

### `facktry/types.py` (split into `facktry/types/` submodules only if the file grows unmanageable — one file is fine)
Enums (str-valued): `RunStatus` (`pending|running|completed|failed|guarded|blocked`), `Severity` (`hard|soft|human|diagnostic`), `Channel` (`raw|guarded|n/a`), `DecisionAction` (`promote|hold|correct|abort|ask_human`), `SourceClass` (ADR §5.4 role list), `InterventionClass` (`data|mixture|rubric|hparam|interface|stop`), `DefectStatus`, `InboxStatus`, `Split` (`dev|seal`).

Dataclasses with `to_dict`/`from_dict` and (where they affect decisions) a `content_hash()` method:

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

- Lint/freeze logic (phase 03), compat_check (phase 04), aggregation rules (phase 08). Types are inert data + hashing only.
- No module-level behavior beyond serde/hash.

## Fail-closed requirements

- Round-trip fidelity: `from_dict(to_dict(x)) == x` for every type, including nested lists/dicts/optional fields.
- Hash stability: same logical content → same hash across process restarts (test by hashing in a subprocess).
- `tuple_hash` must change when any component hash changes.
- Unknown enum values on deserialize → typed `SerdeError`, not silent acceptance.

## Tests

- Parametrized round-trip serde for all 16 types, including immutable MissionBrief versions.
- Canonical hash stability incl. subprocess run; dict key ordering invariance.
- `tuple_hash` sensitivity per component.
- Enum rejection of bad values.

## Checklist updates

- Checklist §1 all items `[x]`. Progress summary row 1.

## Definition of done

All types are importable from `facktry.types` and their tests pass.

## Handoff to phase 02

Phase 02 (store) persists these types. Keep `to_dict` output exactly what `canonical_json` consumes — the store must not need custom serializers.
