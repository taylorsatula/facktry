# Phase T00 — `questions` tool (structured human Q&A)

| Field | Value |
|---|---|
| **Status** | [ ] |
| **Depends on** | `facktry-pi` package skeleton able to load an extension (may be minimal; does **not** depend on harness phases). If `facktry-pi` does not exist yet, this phase may create `facktry-pi/` enough to host one extension + tests. |
| **PI_FOUNDATION refs** | §6.2 parent tools (human interaction), §5 isolation, §10 launcher TUI |
| **ADR refs** | §3 human surface; §5.0 `MissionBrief`; §7.0 `elicit`; §10 human loop. This tool is **not** the inbox system or MissionBrief store — it is live, in-session Q&A while the operator agent is running. |
| **Upstream reference** | `@earendil-works/pi-coding-agent/examples/extensions/question.ts` (primary), `questionnaire.ts` (multi-question patterns) |

## Goal

Ship a facktry-specific Pi tool for structured human questions, with single- and multi-question calls, multiple-choice options, optional free text, and attachable detail. It is a human-I/O primitive, not a workflow engine. During `elicit`, its result is passed to `save_mission_brief`; the tool does not persist or authorize anything.

## Upstream differences

Pi's `question.ts` provides a sequential TUI list, optional custom text that replaces the selected option, non-TUI errors, transcript renderers, and cancellation. Facktry adds:

1. MCQ selection with optional detail; custom text remains a distinct path.
2. Single- and multi-question calls under one `questions` tool.
3. A stable result schema for inbox/dossier citation (`question_id`, option `value` vs display `label`, optional `detail`).
4. Registration inside the facktry image, never as a global `~/.pi` extension.

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
  allowOther?: boolean           # default true — show "Type something else" path
  allowDetail?: boolean          # default true — enable detail on MCQ
  detailPrompt?: string          # placeholder/hint; default "Add detail (optional)"
  required?: boolean             # default true — multi-question submit gating
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
- when focused and `allowDetail`: a discoverable footer hint for the normative detail key

Append synthetic rows when enabled:

- **Add detail…** — optional; use the normative detail key below rather than a permanent fake option when possible.

The keybinding summary below is normative; do not infer additional bindings from this section.

#### Selection and detail behavior

1. **Enter** on an MCQ option
   - Sets the answer to that option’s `value` / `label`.  
   - Does **not** clear existing detail if the user re-picks the same option.  
   - Switching to a **different** MCQ option clears detail (detail was about the previous choice).  
   - Single-question + `allowDetail`: enter `detail` mode after selection; empty Enter accepts without detail. Esc returns to `browse`.
   - Multi-question: Enter selects and advances without detail. The `d`/Ctrl+D binding in the keybinding summary opens detail before advance; detail submit then advances. The footer must show the binding.

2. **Detail editor (`detail` mode)**  
   - Prefilled with prior detail if any.  
   - Enter submits detail (trim end; allow multi-line if Editor does). Empty submit sets `detail: null`.
   - Esc with an empty editor accepts the MCQ selection without detail. Esc with text leaves detail mode, keeps the MCQ selection, and discards the unsaved buffer.
   - Detail does **not** change `value`/`label` of the option.  
   - Result fields: `was_custom: false`, `detail: string | null`.  

3. **"Type something else" (`other` mode)** — when `allowOther`
   - Synthetic last row like upstream.
   - Enter opens the editor; submit sets `was_custom: true`, `value`/`label` to the text, and `detail: null`.
   - Switching from custom back to MCQ clears custom text.  

4. **Esc in browse**  
   - Cancel the tool or questionnaire → `cancelled: true` with all answers discarded.

5. **Non-TUI / headless**  
   - Return an immediate structured tool error with `cancelled: true`; do not throw or wait for input.

Validation failures use the same error-content path. Successful and cancelled results retain the exact `QuestionsToolDetails` schema; it does not gain an error field.

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
- Mouse-only interaction; keyboard is primary. “Tap” means a deliberate key affordance, not a touch GUI.
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
- Use camelCase in the Pi tool schema: `allowOther`, `allowDetail`, and `detailPrompt`. Map to snake_case only at later Python bridge boundaries.

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
| Esc | Empty editor: finish with selection and no detail; otherwise return to browse and drop the unsaved buffer |

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

## Checklist and index updates

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

## Reference map (upstream → facktry)

| Upstream | Facktry |
|---|---|
| `question` tool | `questions` (array API) |
| options `label` + `description` | + `value` (questionnaire-style) |
| "Type something." exclusive free text | keep as `allowOther` |
| _(none)_ | `allowDetail` + detail editor on MCQ |
| `QuestionDetails` | `QuestionsToolDetails` |
| `questionnaire` tabs | multi branch of same tool |
