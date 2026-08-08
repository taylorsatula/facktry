# Phase T00 — `questions` tool (structured human Q&A)

| Field | Value |
|---|---|
| **Status** | [ ] |
| **Depends on** | `facktry-pi` package skeleton able to load an extension (may be minimal; does **not** depend on harness phases). If `facktry-pi` does not exist yet, this phase may create `facktry-pi/` enough to host one extension + tests. |
| **PI_FOUNDATION refs** | §6.2 parent tools (human interaction), §5 isolation, §10 launcher TUI |
| **ADR refs** | §3 human surface; §5.0 `MissionBrief`; §7.0 `elicit`; §10 human loop. This tool is **not** the inbox system or MissionBrief store — it is live, in-session Q&A while the operator agent is running. |
| **Upstream reference** | `@earendil-works/pi-coding-agent/examples/extensions/question.ts` (primary), `questionnaire.ts` (multi-question patterns) |

## Goal

Ship a Pi tool the facktry operator can call to ask the human **structured questions** (single or multi), with multiple-choice options, optional free-text ("other"), and a facktry extension:

> **Tap to add detail** — after (or while) selecting a multiple-choice answer, the human can attach an optional free-text note without abandoning the chosen option.

The tool is intentionally simple: it is a human I/O primitive, not a workflow engine. During `elicit`, its structured result is later passed to `save_mission_brief`; the tool itself does not persist or authorize anything.

## Why not use stock `question.ts` as-is

Upstream `question.ts` already provides:

- Tool name `question`
- Params: `question: string`, `options: { label, description? }[]`
- TUI list with ↑↓ / Enter / Esc
- Always appends a synthetic **"Type something."** option that switches to an `Editor` and **replaces** the answer with free text (`wasCustom: true`)
- `executionMode: "sequential"`
- Non-TUI → error result
- `renderCall` / `renderResult` for transcript chrome
- Cancel → `answer: null`

Gaps for facktry:

1. Choosing a labeled option and **also** writing detail is impossible — "Type something." is mutually exclusive with the option labels.
2. Multi-question batches need either N tool calls or questionnaire-style tabs; facktry should support **one or many** questions in one tool call without a second tool name.
3. Result schema should be stable for later inbox/dossier citation (`question_id`, option `value` vs display `label`, optional `detail`).
4. Lives inside the **facktry image**, not as a global `~/.pi` extension.

## In scope

### Tool registration

- Extension entry that `pi.registerTool({ name: "questions", ... })` (plural — distinct from upstream `question` to avoid collisions if someone loads both).
- `label`: `Questions`
- `description`: clear guidance for the model — use when a human judgment, preference, or clarification is required before proceeding; prefer concrete options over open essay prompts when possible.
- `executionMode: "sequential"` (must not run parallel with sibling tools that assume answers already exist).
- `parameters` via TypeBox.

### Parameter schema

```text
questions: array of {
  id: string                     # stable id for this question (required)
  prompt: string                 # full question text (required)
  label?: string                 # short tab/header label; default Q1, Q2, …
  options: array of {
    value: string                # machine value returned to the model (required)
    label: string                # display label (required)
    description?: string         # secondary line under label
  }                              # min length 1
  allow_other?: boolean          # default true — show "Type something else" path
  allow_detail?: boolean         # default true — enable tap-to-add-detail on MCQ
  detail_prompt?: string         # placeholder/hint for detail editor; default "Add detail (optional)"
  required?: boolean             # default true — if multi-question submit gating uses this later
}
```

**Single-question call:** `questions` length 1 — UI is a simple list (no tab bar), matching upstream `question.ts` feel.

**Multi-question call:** `questions` length > 1 — tab bar + Submit pattern adapted from `questionnaire.ts` (□/■ answered markers, Tab/←/→ between questions, Submit only when all required answered).

Validation before UI:

- empty `questions` → error result  
- any question with empty `options` → error result  
- duplicate `id`s → error result  
- blank `prompt` / blank option `value` or `label` → error result  

### UI behavior (TUI)

Pattern after upstream: `ctx.ui.custom()` returning `{ render, invalidate, handleInput }`, using `@earendil-works/pi-tui` `Editor`, `Key`, `matchesKey`, `wrapTextWithAnsi`, `visibleWidth`, theme `fg`/`bg`.

#### Modes per question

| Mode | Meaning |
|---|---|
| `browse` | Navigate options with ↑↓ |
| `detail` | Editor open to attach/edit detail for the **currently highlighted or already-selected** MCQ option |
| `other` | Editor open for full free-text answer (replaces MCQ), same spirit as upstream "Type something." |

#### Option rows

For each MCQ option row, show:

- index + label  
- optional description  
- if this option is the current answer: success checkmark  
- if this option has non-empty detail: muted preview snippet (single line, truncated)  
- when focused and `allow_detail`: dim hint e.g. `Tab add detail` (exact copy can be tuned; must be discoverable in the footer)

Append synthetic rows when enabled:

- **Add detail…** — only meaningful once an MCQ option is selected OR as a second step after Enter on an option (see binding below). Prefer **not** a permanent fake option if keyboard binding is clearer; either design is acceptable if documented in the footer. Recommended UX (normative):

#### Selection + tap-to-add-detail (normative UX)

1. **Enter** on an MCQ option  
   - Sets the answer to that option’s `value` / `label`.  
   - Does **not** clear existing detail if the user re-picks the same option.  
   - Switching to a **different** MCQ option clears detail (detail was about the previous choice).  
   - Single-question + `allow_detail`: after select, **offer detail** — either auto-enter `detail` mode with empty optional editor, or stay in `browse` with footer `Enter confirm · Tab add detail · Esc cancel`.  
   - **Preferred (normative) for single-question:** after first Enter on option, enter `detail` mode with hint that empty Enter accepts without detail (fast path). Esc from empty detail accepts selection with no detail.  
   - **Multi-question:** Enter on option saves answer and advances (questionnaire style). **Tab** (when not moving between question tabs — see keys) or a dedicated key opens detail **before** advance; use **Shift+Enter** or **Ctrl+D** / **Tab in browse when option already selected** to add detail without advancing. Pick one chord, document in footer, test it. Recommended multi-question binding:  
     - `Enter` = select option and advance (no detail)  
     - `Ctrl+D` or `Tab` when focus is on an already-selected option = open detail editor; on detail submit, advance  
     - Footer must show the binding  

2. **Detail editor (`detail` mode)**  
   - Prefilled with prior detail if any.  
   - Enter submits detail (trim end; allow multi-line if Editor does). Empty submit = no detail (`detail: null` or omit).  
   - Esc = leave detail mode **keeping** the MCQ selection; discard unsaved editor buffer (or keep previous saved detail).  
   - Detail does **not** change `value`/`label` of the option.  
   - Result fields: `was_custom: false`, `detail: string | null`.  

3. **"Type something else" (`other` mode)** — when `allow_other`  
   - Synthetic last row like upstream.  
   - Enter opens editor; submit sets `was_custom: true`, `value`/`label` to the written text, `detail: null`.  
   - Switching from custom back to MCQ clears custom text.  

4. **Esc in browse**  
   - Cancel whole tool (single) or cancel questionnaire (multi) → `cancelled: true`, answers empty or partial per chosen policy. **Normative:** cancel discards all answers for this tool call (same as upstream questionnaire `cancelled: true`).  

5. **Non-TUI / headless**  
   - Immediate structured error; `cancelled: true`; no throw.  

### Result contract (normative)

Model-facing `content[0].text`: human-readable summary, e.g.

```text
Q: <prompt>
A: <label> [value=<value>]
Detail: <detail or (none)>
```

(repeat per question; note cancellations clearly.)

Structured `details`:

```ts
type QuestionsToolDetails = {
  cancelled: boolean;
  answers: Array<{
    id: string;
    prompt: string;
    value: string | null;     // null if cancelled / unanswered
    label: string | null;
    detail: string | null;    // tap-to-add-detail text; null if none or custom-other
    was_custom: boolean;      // true if "Type something else" path
    option_index: number | null; // 1-based into provided options; null if custom/cancel
  }>;
};
```

`renderCall`: show tool title + each prompt + option labels (dim).  
`renderResult`: success lines with checkmarks; show detail truncated; warning style if cancelled.

### Files to add (target layout)

```text
facktry-pi/
  src/
    tools/
      questions/
        index.ts           # registerTool export default extension factory OR named register
        schema.ts          # TypeBox schemas + normalize/validate
        types.ts           # QuestionsToolDetails, internal UI state types
        ui.ts              # ctx.ui.custom implementation (browse/detail/other)
        render.ts          # renderCall / renderResult
        format.ts          # content text builder
    extensions/
      index.ts             # registers questions among other tools
  tests/
    tools/questions/
      schema.test.ts
      format.test.ts
      # UI: pure helpers for state transitions if extracted; full TUI optional
```

If the monorepo is still design-only, creating `facktry-pi/` with this tool as the first concrete code is in scope for T00.

### Package / loader wiring

- Tool available when `facktry run` loads the facktry image.  
- **Not** written into `~/.pi/agent/extensions`.  
- Parent system prompt / `ding_help` equivalent lists `questions` once the help tool exists; until then, tool schema description is enough.  
- The canonical orchestration is `/home/admin/facktry/docs/skills/elicit-mission/SKILL.md`; T00 may add only a thin `ask-human` note for when to call `questions` versus waiting for the harness inbox.

## Out of scope

- Harness `HumanInboxItem` persistence (ADR inbox).  
- MissionBrief persistence as a side effect of `questions`: elicitation retains the working answers in session memory and calls `save_mission_brief` once at the end; `questions` remains a pure I/O primitive.  
- Auth, payments, or blocking multi-user forms.  
- LLM-side validation of answer quality.  
- Replacing `facktry watch` inbox UX.  
- Mouse-only interaction (keyboard is primary; "tap" means a deliberate key affordance, not a touch GUI).  
- Upstream PR to Pi (optional later; facktry ships its own tool).

## Fail-closed / product rules

1. Never invent answers if the user cancels — return `cancelled: true` and null values.  
2. Never block headless/`print` modes waiting for input.  
3. Do not expose a mutation path through this tool.  
4. Detail text is optional metadata; models must treat `value` as the primary answer. Prompt description should say so.  
5. Do not log detail/answer payloads to external services from this tool.
6. A successful `questions` result is not a MissionBrief and cannot authorize `freeze_objective` or an experiment until the complete dossier has been passed to `save_mission_brief`.

## Implementation notes (for the coding agent)

- Read upstream `question.ts` and `questionnaire.ts` fully before writing; reuse Editor theme wiring and wrap helpers.  
- Extract **pure** functions for: validate params, apply "select option" transition, apply "set detail", apply "set custom", multi-question advance — unit-test those without a TUI.  
- Keep UI file focused on rendering and key routing.  
- Prefer one cohesive tool (`questions`) over shipping both `question` and `questionnaire` names.  
- Match facktry naming: `allow_other` snake_case in tool params if other facktry tools use snake_case; if Pi ecosystem expects camelCase in tool JSON, use camelCase (`allowOther`) consistently with upstream and document it. **Normative for T00:** camelCase in tool schema (`allowOther`, `allowDetail`, `detailPrompt`) to match Pi examples; map to snake_case only at Python bridge boundaries later.

### Keybinding summary (normative — implement exactly)

**Single question, browse mode**

| Key | Action |
|---|---|
| ↑ / ↓ | Move highlight |
| Enter | Select option → enter detail mode if `allowDetail`, else finish |
| Esc | Cancel tool |

**Single question, detail mode**

| Key | Action |
|---|---|
| Enter | Accept detail (empty OK) → finish with MCQ + detail |
| Esc | Back to browse; keep selection; drop unsaved buffer |

**Single question, other mode**

| Key | Action |
|---|---|
| Enter | Submit custom text (empty = stay or no-op; do not finish empty — match upstream: empty returns to browse) |
| Esc | Back to browse |

**Multi question**

| Key | Action |
|---|---|
| ← / → or Tab / Shift+Tab | Change question tab / Submit tab (when not in editor mode) |
| ↑ / ↓ | Move highlight on options |
| Enter on option | Select; advance to next unanswered or next tab (no detail) |
| `d` or Ctrl+D on option | Select if needed + open detail mode; on detail Enter, save and advance |
| Enter on Submit tab | Finish if all required answered |
| Esc | Cancel entire questionnaire |

Footer strings must reflect the active mode.

## Tests

### Schema / pure logic

- Valid single and multi payloads normalize defaults (`allowOther`, `allowDetail` default true).  
- Reject empty questions, empty options, duplicate ids.  
- Select option A → answer value A; add detail → detail set, was_custom false.  
- Change from option A→B → detail cleared.  
- Custom other → was_custom true, detail null.  
- Cancel → cancelled true, answers empty.  

### Format / render

- `format` content includes prompt, label, detail.  
- `renderResult` handles cancelled, custom, detail, plain select.  

### Integration (if test harness allows)

- Tool registers and appears in `getAllTools()` under facktry loader.  
- Non-tui context returns error details without throwing.  

### Manual

- `facktry run` (or dev extension load): agent calls `questions`; human selects option, adds detail, confirms; model receives both.  
- Multi-question: answer Q1, detail on Q2 via `d`, submit.  
- Cancel path.  
- Headless `-p` with a forced tool call does not hang (mock or document manual N/A if agent won't call without TUI).

## Checklist / index updates (same change set)

- `tools_implementation_steps/README.md` phase T00 status → `[x]` when done.  
- If `PI_FOUNDATION.md` parent tool table still omits `questions`, add a row under F0 or F0 human-I/O: `questions` | structured human Q&A with MCQ + optional detail | no mutation.  
- Do **not** mark ADR harness checklist items done for this work.

## Definition of done

1. `questions` tool loads only via facktry operator image.  
2. Single- and multi-question flows work in TUI.  
3. Tap-to-add-detail works: MCQ value preserved + optional detail string in `details.answers[].detail`.  
4. Custom-other path still works and is distinct from detail.  
5. Cancel and non-TUI paths are safe.  
6. Unit tests for schema/transitions/format pass.  
7. README index status updated; this doc Status `[x]` and file moved to `complete/`.

## Handoff

- Later tools (research, harness façades) can call the same registration style.  
- The `elicit` skill uses this tool for adaptive question volleys, then hands the complete accepted answers and research pointers to `save_mission_brief` once at the end.  
- When ADR inbox exists, a separate tool or bridge may **copy** a `questions` result into `HumanInboxItem` gold answers — not part of T00.  
- If multi-question UX is too heavy, do not remove detail feature; multi may follow single in a T00.1 only if single ships complete with detail first — prefer one phase shipping both.

## Reference map (upstream → facktry)

| Upstream | Facktry |
|---|---|
| `question` tool | `questions` (array API) |
| options `label` + `description` | + `value` (questionnaire-style) |
| "Type something." exclusive free text | keep as `allowOther` |
| _(none)_ | `allowDetail` + detail editor on MCQ |
| `QuestionDetails` | `QuestionsToolDetails` |
| `questionnaire` tabs | multi branch of same tool |
