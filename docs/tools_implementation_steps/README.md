# Facktry — Tools Implementation Steps

This directory tracks **operator-facing tools** for the facktry Pi session image (`PI_FOUNDATION.md`). It is separate from the harness phases in `codebase_implementation_steps/`.

Harness modules (`store`, `admit`, `train`, `agent_api`, …) live on the ADR track. Tools here are the LLM-callable surfaces inside `facktry run`: research, questions, and future `agent_api` façades.

## How to use

1. Read `../PI_FOUNDATION.md` and, where relevant, `../ADR.md`.
2. Pick the lowest-numbered doc in `planned/`.
3. Move to `active/` when Status is `[~]`; to `complete/` when definition of done is met (`[x]`).
4. Prefer one active tool phase at a time.
5. Ship real behavior + tests. No always-pass stubs.

### Lifecycle

| Directory | Meaning |
|---|---|
| `planned/` | Not started |
| `active/` | In progress |
| `complete/` | Done |

## Shared conventions

- **Host:** tools register via Pi `ExtensionAPI` inside `facktry-pi` (see `PI_FOUNDATION.md`). They must not install into `~/.pi/agent/` by default.
- **Package home:** target `facktry-pi/src/tools/` (and TUI helpers beside them). Until the tree exists, implement against the layout in `PI_FOUNDATION.md` §9.2. The red contract suite lives in `facktry-pi/tests/` and runs with `npm --prefix facktry-pi test`; it is intentionally separate from Python `pytest`. The initial Node tests import the emitted ESM `.js` boundary; the T00 TypeScript scaffold must provide that boundary before the suite can go green.
- **Reference implementations:** Pi upstream examples under `@earendil-works/pi-coding-agent/examples/extensions/` (e.g. `question.ts`, `questionnaire.ts`). Copy patterns, not global install paths.
- **Interactive UI:** `ctx.ui.custom()` + `@earendil-works/pi-tui` (`Editor`, `Key`, `matchesKey`, theme helpers). `executionMode: "sequential"` when the tool blocks on human input.
- **Human I/O:** refuse clearly when `mode !== "tui"`; never wait for a human in headless runs. Noninteractive tools such as `research` must support print/JSON modes.
- **Results:** always return model-facing `content[]` text **and** structured `details` for renderers/tests.
- **No harness bypass:** `questions` is a pure human-I/O primitive. The `elicit` skill collects answers and research context, then calls `save_mission_brief` once at the end. Research returns **proposals**, not passed gates or curated recipes; the MissionBrief stores only brief summaries plus references.
- **Long-running tools:** research-style workers must support abort, progress logs, and headless execution (no TUI required unless the tool is explicitly human I/O).

## Phase index

| Phase | Doc | Deliverable | Status |
|---|---|---|---|
| T00 | [planned/phase_T00_questions.md](planned/phase_T00_questions.md) | `questions` tool — structured MCQ + free text + tap-to-add-detail | [ ] |
| T01 | [planned/phase_T01_research.md](planned/phase_T01_research.md) | `research` tool — isolated literature→recipe worker + `papers` substrate | [ ] |
