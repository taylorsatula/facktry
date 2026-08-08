# Phase 14 — `play`

| Field | Value |
|---|---|
| **Status** | [ ] |
| **Depends on** | Phases 06, 07 |
| **Checklist sections** | §8 |
| **ADR refs** | §7.6 (play), §4 doctrine 20 (multi-turn for dialogue) |

## Goal

Produce trajectories and episodes — for harvest into training data and for multi-turn/tool suites — with hard runner-side control and private world state kept out of subject prompts and artifacts.

## In scope (`facktry/play/`)

### `World` protocol (ADR §7.6)
```python
class World(Protocol):
    def reset(self, seed: int, scenario: dict) -> Observation: ...
    def step(self, action: Action) -> tuple[Observation, bool, dict]: ...   # (obs, done, info)
    def oracle_state(self) -> dict: ...        # private — runner only
    def export_transcript(self) -> Transcript: ...
```
Core ships `EchoWorld`/`CounterWorld` test fixtures (deterministic toy worlds); real worlds come from domain packs.

### Episode runner
- `run_episode(subject: ModelBackend, partner: PartnerConfig | None, world: World, *, max_turns: int, seed) -> Episode`:
  - Subject↔partner loop with **hard runner-side turn cap** — stop tokens advisory only; runner cuts at `max_turns` regardless (test with a subject that never stops).
  - **Private state hygiene:** `oracle_state()` content is never included in subject prompts and never written to open artifacts; transcripts persist visible turns + tool records only (private fields redacted at export, private summary may persist as `seal`-role).
  - Tool episodes: subject actions validated against the world's authorized action schema before `world.step` (reuses verify's unsupported-action logic).
- `PartnerConfig`: model/config id (or scripted partner for tests), engagement length, per-turn instructions, pain points, visible stop sequence.

### Analysis
- Deterministic analyzers run on transcripts **before** any LLM judge (phase 15 consumes their output): turn counts, loop/repetition detection, unresolved-request heuristic, tool-error rate, termination reason.
- **Simulator-realism scorecard**: when the partner is model-driven, emit a separate scorecard (scripted checks: persona consistency, engagement-length adherence, stop-sequence respect) — explicitly separate from the subject scorecard.

### Integration
- Episodes export as `replay`/`synthetic`-class artifacts → admit path (phase 05) for harvest.
- Suite `multi_turn`/`tool_episode` cases may name a world + scenario; phase 07's runner already supports transcripts — wire the bridge here (suite case → `run_episode` → verify oracles on transcript).

## Out of scope

- LLM realism judging (phase 15 may score transcripts; deterministic realism scorecard ships here regardless).

## Fail-closed requirements

- Turn cap is non-negotiable runner behavior.
- Private-state leak = defect: test asserts oracle-state values appear in no persisted transcript, no subject prompt log, no open artifact.

## Tests

- Hard turn cap with never-stopping fake subject.
- Private state exclusion (prompts + artifacts scanned for oracle-state sentinels).
- World protocol conformance for the shipped test worlds (reset determinism by seed, step contract, export shape).
- Unsupported subject action refused before `world.step`.
- Analyzer outputs deterministic on fixture transcripts; realism scorecard separate artifact from subject scorecard.
- Suite bridge: a `tool_episode` case executes through play and produces a normal scorecard.

## Checklist updates (same change set)

- Checklist §8 all `[x]`. Progress summary row 8.

## Definition of done

Episodes run capped and leak-free; transcripts feed admit and suites; tests green; checklist updated.

## Handoff to phase 15

Phase 15 (judge) consumes analyzer outputs + transcripts. Keep transcript JSON schema versioned (`transcript_schema_version` field) so judge replay mode can reprocess historical episodes.
