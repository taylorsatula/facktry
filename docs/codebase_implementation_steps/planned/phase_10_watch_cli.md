# Phase 10 — `watch` CLI

| Field | Value |
|---|---|
| **Status** | [ ] |
| **Depends on** | Phases 02, 09 |
| **Checklist sections** | §15 (+ §18 CLI rows) |
| **ADR refs** | §5.0 `MissionBrief`, §7.14 (watch), §3 (surfaces), §4 doctrine 13/22 |

## Goal

The human overseer's window. Bare `facktry` shows live truth with auto-focus and zero mandatory flags; mutation from the CLI is limited to explicit inbox/promote-ack subcommands.

## In scope (`facktry/cli/`)

### Commands (ADR §7.14.2)
| Invocation | Behavior |
|---|---|
| `facktry` · `facktry cli` · `facktry watch` | In-process live monitor (Rich `Live`), continuous refresh, auto-focus. Replaces the phase-00 placeholder. |
| `facktry status` | One-shot snapshot sharing render code with live mode (`--once` equivalent for live). |
| `facktry inbox` | List pending items (gate, age, objective). Subcommands: `facktry inbox show <id>`, `facktry inbox respond <id>` (validates against response_schema, records reviewer identity), `facktry inbox ingest <file>`. |
| `facktry show <id>` | Auto-detect id kind (MissionBrief / objective / run / decision / tuple / scorecard / inbox item) via store lookups; deep-dive render per kind. |
| `facktry ls` | Recent MissionBriefs / runs / decisions / objectives. |

Optional flags `--objective`, `--run`, `--once`, `--refresh`, `--home` exist but are never required for the common case.

### Auto-focus (ADR §7.14.3) — pure function
`resolve_focus(query_surface) -> Focus` implementing the exact priority: pending inbox → newest running → newest blocked/guarded → newest saved MissionBrief not attached to a frozen Objective → newest frozen objective → newest decision+pins → empty state with concrete next-step text. Unit-tested without a terminal (§18 row).

### Live layout (ADR §7.14.4 — fixed panes)
Header (objective id · MissionBrief id/version/hash · intent · autonomy · budget remaining · time in phase) · loop position (`elicit → save_brief → freeze_objective → pin_suites → admit → smoke → scale → select → measure → decide`, current highlighted) · active run (id/stage/status/parent/started/metrics spark) · gates (failures first, raw vs guarded) · latest decision · open defects top-N · inbox (count, oldest age, **visually loud** when non-zero) · release hashes (base vs candidate vs pinned prod) · machine (GPU util/mem/temp best-effort, disk free, heartbeats) · log tail (active run primary log, last lines).

### Constraints (ADR §7.14.5)
- In-process renderer; no subprocess hop.
- Only `query_*` reads; live refresh **never** starts training or mutates anything. Inbox respond/promote ack are the explicit subcommands above, nothing ambient.
- Missing metrics/logs/GPU degrade panes to placeholders ("no metrics yet") — never crash. Test with a bare workspace.
- Machine probes tolerate broken NVML (known host issue: driver/library mismatch) — render "GPU probe unavailable".

## Out of scope

- Per-domain dashboard JSON (ADR §7.14.1 — explicitly refused; layout is fixed panes only).

## Fail-closed requirements

- Read-only live path: a test runs the snapshot render against a workspace and asserts store mtimes/manifests unchanged.
- Empty workspace → helpful empty state naming the next step ("no active objective; agent must elicit and save a MissionBrief"), not a traceback.

## Tests

- Auto-focus ordering: seeded store states for each priority level, including a saved MissionBrief awaiting freeze → correct focus (**§18 row**).
- Empty-state message content (**§18 row**).
- `facktry status` renders against bare workspace and against populated fixture without exceptions (invoke via Click/argparse test runner, capture output).
- Snapshot is read-only (no store mutations).
- Missing metrics file / missing GPU → degraded panes, exit code 0.
- `facktry inbox respond` round-trip: valid response resolves item; invalid refused with schema error.

## Checklist updates (same change set)

- Checklist §15 all `[x]` + test rows; §18 CLI row `[x]`. Progress summary row 15.

## Definition of done

A human typing `facktry` during fixture activity sees objective, phase, active run, gates, defects, inbox pressure with no flags; tests green; checklist updated.

## Handoff to phase 11

Phase 11 (train SFT) writes the metrics/log artifacts these panes render — use the exact metrics line schema (`{"step":…, "loss":…, …}` JSONL) the spark pane already tails, so training shows up live with no CLI changes.
