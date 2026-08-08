# Facktry — Implementation Checklist

| Field | Value |
|---|---|
| **Authority** | Companion to `ADR.md`. ADR defines *what*; this file tracks *done vs remaining*. |
| **Operator runtime** | `PI_FOUNDATION.md` — Pi session image / `facktry run` (parallel track; not a substitute for harness modules). |
| **Maintainer** | Every implementation agent **must** update this file in the same change set as code. |
| **Rule** | After context compaction, read `ADR.md` + **this file** before writing code. Do not trust chat memory for progress. |
| **Status values** | `[ ]` not started · `[~]` in progress / partial · `[x]` done and covered by required tests · `[-]` waived with written reason |

---

## How to use this file

1. Open `ADR.md` for the contract of the item you are building.  
2. Find the matching section below; mark `[~]` when you start.
3. Mark `[x]` only when behavior matches ADR **and** required tests exist/pass.
4. Add a one-line note under the item if something is subtle (hash scheme, path layout).
5. Never delete checklist items to hide work; waive with `[-]` + reason instead.
6. Keep the **Progress summary** table at the bottom accurate on every edit.
7. Work phase-by-phase using the per-phase docs in `codebase_implementation_steps/` (index: `codebase_implementation_steps/README.md`). Mark the phase doc status and the matching checklist sections in the same change set as code.

---

## 0. Repository skeleton

- [x] Package root installable (`pyproject.toml`, package name `facktry`)
- [x] Console entrypoint `facktry` → CLI main
- [x] Package importable: `import facktry`
- [x] `facktry/__init__.py` exports version
- [x] Workspace default `.facktry/` + `FACKTRY_HOME` discovery helper
- [x] `runs/` (or workspace-relative runs) gitignored
- [x] `.facktry/` gitignored as appropriate
- [x] `tests/` laid out and pytest discovers them
- [x] README pointing at `ADR.md`, this checklist, `docs/skills/`, and `docs/recipes/`
- [x] No runtime dependency on reference repositories

**Notes:**

Phase 00 red suite written and verified failing (14/14) in an isolated `.venv`
(no `--system-site-packages`). A stale editable `facktry` install from a prior
scaffolding probe (dist-info + `~/.local/bin/facktry`) made packaging-metadata
tests pass while the package was unimportable; purge prior installs before
trusting metadata tests. Green implementation to follow.



---

## 1. Core types (`facktry.types` or equivalent)

Serialize/deserialize stably; hashes canonical.

- [ ] `MissionBrief` + immutable versions / content hashes / supersede lineage (including recipe considerations and human tradeoffs)
- [ ] `Objective` + freeze immutability / supersede; every objective references a saved MissionBrief
- [ ] `ReleaseTuple` + `tuple_hash` over components
- [ ] `Run` + status enum
- [ ] `Artifact`
- [ ] `Gate` / `GateResult` (severities, channels raw|guarded|n/a)
- [ ] `Scorecard` (raw + guarded channels)
- [ ] `Decision` + actions enum
- [ ] `Recipe` + versioned instruction hash / append-only note hashes
- [ ] `RecipeStack` + immutable composition hash
- [ ] `Defect`
- [ ] `Policy` / `BudgetLedger`
- [ ] `TrainCard`
- [ ] `MixtureSpec` / `TargetShape`
- [ ] `AdmissionReport`
- [ ] `HumanInboxItem`
- [ ] Canonical JSON / hashing utilities used by all of the above

**Notes:**



---

## 2. `store`

- [ ] Workspace discovery (`FACKTRY_HOME`, walk parents for `.facktry/`)
- [ ] Create run directories; atomic manifest write
- [ ] Hash file on register; reject mismatch
- [ ] Index: runs by objective/status/stage
- [ ] Lineage parents/children
- [ ] Persist/load objectives (by id + hash verify)
- [ ] Persist/load MissionBrief versions; save-at-end API; query latest brief and version history
- [ ] Latest passing `AdmissionReport` for objective
- [ ] Open defects query
- [ ] Pending inbox query
- [ ] Latest decision / pinned production tuple
- [ ] Recipe catalog: load/list/show/version recipes; append structured use notes without editing instructions
- [ ] Recommend recipes from target effects, objective constraints, defects, notes, and prior outcomes
- [ ] Persist/load immutable `RecipeStack`s with hash verification
- [ ] Metrics stream path + append API
- [ ] No agent-facing delete of protected runs (parents, pins, decision subjects)
- [ ] Concurrent read-safe behavior documented/tested basically

**Notes:**



---

## 3. `objective` / `elicit`

- [ ] Adaptive `elicit` skill flow uses `questions` and optional `research` between volleys; session retrieves relevant recipes/notes during human reasoning and covers required sections
- [ ] `save_mission_brief` persists one complete immutable version at end of elicitation; individual hard-gate approvals and recipe considerations required
- [ ] Load / show
- [ ] Lint on freeze (ADR §5.0–§5.1 — saved complete MissionBrief, required sections, individual hard-gate approvals, and all Objective bullets)
- [ ] Freeze persists bytes + content hash
- [ ] Refuse mutate-after-freeze
- [ ] Supersede → new id, link to old
- [ ] List open/frozen objectives (for CLI auto-focus)
- [ ] Recipe policy lint: applicability, allowed/forbidden ids, conflicts, stack limits, budget, and no weakening of hard gates
- [ ] Compose and hash a compatible `RecipeStack` after MissionBrief exists

**Notes:**



---

## 4. `govern`

- [ ] `preflight` (paths, env, disk, GPU usable, hardware record)
- [ ] GPU exclusivity refusal when conflicting large services detected
- [ ] `BudgetLedger` decrement + deny when insufficient
- [ ] Policy allow/deny for agent capabilities
- [ ] `compat_check(tuple_a, tuple_b)`
- [ ] `smoke_then_scale` gate (smoke Decision, code_hash, admission hash, memory envelope)
- [ ] `suite_pin` required before generate/admit-for-train
- [ ] All mutation paths invoked from `agent_api` hit govern (no bypass)
- [ ] Every experiment path refuses a missing or mismatched MissionBrief

**Tests:**

- [ ] scale denied without passing smoke
- [ ] scale denied on admission hash mismatch
- [ ] compat_check catches template/tokenizer drift
- [ ] suite pin required before admit-for-train

**Notes:**



---

## 5. `admit`

- [ ] Schema/structure validation
- [ ] Role/turn structure at **construction** time
- [ ] Dependence-key leakage train∩eval∩seal
- [ ] Diversity meters (unique inputs/turns, template family, near-dupe)
- [ ] Attribution / hidden-context ban
- [ ] Controlled vocab checks
- [ ] Mixture vs TargetShape
- [ ] Source-class labeling; refuse raw private artifact writes
- [ ] Teacher identity default base/ancestor
- [ ] Emit `AdmissionReport` (histogram, overlaps, seeds, suite hash, pass/fail)
- [ ] Train refuses start without passing report ref
- [ ] `generate_and_admit` pipeline (construct → generate → filter → admit)
- [ ] Parallel gen: global indices + per-part manifests + ordered merge

**Tests:**

- [ ] leakage at dependence keys
- [ ] attribution/hidden-context rejection
- [ ] role/structure construction failure before generate
- [ ] private raw bytes refused on artifact write

**Notes:**



---

## 6. `verify`

- [ ] Schema/grammar/JSON oracle
- [ ] Regex/canary/PII oracle
- [ ] State-transition oracle
- [ ] Claim≠execute oracle
- [ ] Unsupported-action oracle
- [ ] Entailment oracle (when evidence docs present)
- [ ] Execution oracle hook (code/SQL domains)
- [ ] Abstention detector (configurable)
- [ ] Finding severity → hard gate wiring

**Tests:**

- [ ] claim≠execute
- [ ] unsupported-action

**Notes:**



---

## 7. `suite`

- [ ] Suite registry + content hash
- [ ] Case schema (id, family, split dev|seal, keys, visible input, private state, verifiers)
- [ ] Runner pins seeds + decode + subject tuple
- [ ] Dev suite inspectable
- [ ] **Sealed blind runner** (planner API: aggregates/gates only, no case text)
- [ ] `compare(tuples, suite)` paired deltas + slices + margins
- [ ] Scorecard dimensions (ADR §7.5 list) populated separately
- [ ] Raw + guarded channels on scorecard
- [ ] Multi-turn case execution path
- [ ] Pin-before-generate enforced via govern/objective

**Tests:**

- [ ] sealed runner does not expose case text via planner-facing API
- [ ] compare emits paired structure
- [ ] suite pin before admit-for-train (shared with govern)

**Notes:**



---

## 8. `play`

- [ ] Subject↔partner loop
- [ ] Hard runner-side turn cap
- [ ] `World` protocol (reset/step/oracle_state/export_transcript)
- [ ] Private state excluded from subject prompts + open artifacts
- [ ] Partner config (model id, length, instructions, stop sequence)
- [ ] Simulator-realism scorecard separate from subject
- [ ] Deterministic analyzers before judge

**Notes:**



---

## 9. `judge`

- [ ] Batch assess against criteria (criteria hash recorded)
- [ ] Corpus overseer (aggregate pathologies)
- [ ] Calibration fixtures shipped
- [ ] Calibration must pass before soft-gate credit
- [ ] Pairwise position swap
- [ ] Replay mode on pinned trajectories
- [ ] Privacy redaction before remote judge

**Notes:**



---

## 10. `train`

- [ ] Plugin interface
- [ ] SFT with target-only loss default
- [ ] Preference method (DPO or equivalent)
- [ ] Parent tuple init only; new run dirs; no overwrite
- [ ] Conservative default hparams / objective bounds
- [ ] Metrics append stream
- [ ] Callback: nonfinite/collapse → guarded + checkpoint
- [ ] Callback: periodic mini sealed probe
- [ ] Recipe retrieval available while interpreting smoke/scale metrics and choosing governed corrections
- [ ] Callback: keep-best under hard probes
- [ ] Callback: VRAM/budget envelope stop
- [ ] `TrainCard` complete (incl. repeat exposure, teacher/reference)
- [ ] RecipeStack hash and recipe-specific adaptations recorded in every train card
- [ ] Preference pair contract enforced at admit/train
- [ ] Post-preference full re-measure expectation wired to decide

**Tests:**

- [ ] preference pairs rejected if inputs differ
- [ ] preference train still fails decide when task hard gates drop
- [ ] collapse/nonfinite → guarded path

**Notes:**



---

## 11. `select`

- [ ] Hard-constrained optimization (not last step / not min loss alone)
- [ ] Ranking artifact with gate matrix + rationale
- [ ] Winner → candidate `ReleaseTuple` adapter component

**Tests:**

- [ ] select does not pick last step when hard probes prefer earlier

**Notes:**



---

## 12. `serve`

- [ ] Load full `ReleaseTuple` (refuse partial prod loads)
- [ ] Guard policy application (versioned hash)
- [ ] Raw + guarded logging always
- [ ] Bounded retries + short truthful fallback
- [ ] Canary side endpoint + paired probes
- [ ] Flip default only under policy + decision
- [ ] One-call rollback to previous pin

**Tests:**

- [ ] rollback restores previous pinned tuple

**Notes:**



---

## 13. `decide`

- [ ] Aggregate per ADR §5.7 rules
- [ ] Hard fail → no promote
- [ ] Human pending → `ask_human`
- [ ] Budget exhaust → hold/abort
- [ ] Soft-only → no promote
- [ ] Diagnostic ignored for promote/select
- [ ] Intervention class mapping → defects
- [ ] Dossier artifact (single-pass readable)
- [ ] Applied RecipeStack ref/hash included in scorecards, Decisions, and yielded releases
- [ ] Decision persisted in store

**Tests:**

- [ ] decide refuses promote on any hard fail
- [ ] decide routes human gates to `ask_human`

**Notes:**



---

## 14. `agent_api`

- [ ] `save_mission_brief` / `show_mission_brief` / `list_mission_briefs` (immutable version + hash; save once at end of elicitation)
- [ ] `freeze_objective` / `show_objective` / `supersede_objective` (freeze requires saved MissionBrief)
- [ ] `preflight`
- [ ] `pin_suites`
- [ ] `admit` / `generate_and_admit`
- [ ] `run_stage`
- [ ] `train_smoke` / `train_scale`
- [ ] `select_checkpoint`
- [ ] `measure` / `compare`
- [ ] `decide`
- [ ] `inbox_list` / `inbox_ingest`
- [ ] `defects_list` / `defects_close`
- [ ] `yield_release`
- [ ] `query_*` read surface shared with CLI
- [ ] `list_recipes` / `show_recipe` / `recommend_recipes` / `compose_recipe_stack`
- [ ] `append_recipe_note` records every governed use, including failures/non-promotions, without changing recipe instructions
- [ ] Structured results; secrets never in manifests
- [ ] Every mutator calls govern

**Notes:**



---

## 15. `watch` CLI

- [ ] Entry: `facktry` / `facktry cli` / `facktry watch` → live monitor
- [ ] `facktry status` one-shot
- [ ] `facktry inbox` list + respond/ingest
- [ ] `facktry show <id>` auto-detect MissionBrief/objective/run/decision/tuple/scorecard kind
- [ ] `facktry ls`
- [ ] Auto-focus order (ADR §7.14.3)
- [ ] Fixed live layout panes (ADR §7.14.4)
- [ ] In-process Live renderer (no subprocess hop)
- [ ] Workspace auto-discovery (no mandatory -r)
- [ ] Missing metrics degrade, don’t crash
- [ ] Live view read-only (no ambient train start)

**Tests:**

- [ ] auto-focus ordering
- [ ] empty-state message

**Notes:**



---

## 16. Domain pack mechanism

- [ ] Registration API without core importing concrete domains
- [ ] `_template` domain pack skeleton (schemas, suites dir, README)
- [ ] `run_stage` dispatches to registered domain stages

**Notes:**



---

## 17. Skills (operator model)

Canonical skills live in `docs/skills/`. Each skill is markdown the operating model loads before acting; package copies are mirrors.

- [ ] `docs/skills/README.md` — how skills work
- [ ] `docs/skills/operating-facktry/SKILL.md` — default operating doctrine
- [ ] `docs/skills/elicit-mission/SKILL.md` — adaptive question/research outline; save complete MissionBrief at end
- [ ] `docs/skills/freeze-objective/SKILL.md`
- [ ] `docs/skills/preflight/SKILL.md`
- [ ] `docs/skills/pin-suites/SKILL.md`
- [ ] `docs/skills/admit-data/SKILL.md`
- [ ] `docs/skills/generate-and-admit/SKILL.md`
- [ ] `docs/skills/train-smoke/SKILL.md`
- [ ] `docs/skills/train-scale/SKILL.md`
- [ ] `docs/skills/measure-and-compare/SKILL.md`
- [ ] `docs/skills/decide/SKILL.md`
- [ ] `docs/skills/yield-release/SKILL.md`
- [ ] `docs/skills/human-inbox/SKILL.md`
- [ ] `docs/skills/defects-and-correct/SKILL.md`
- [ ] `docs/skills/watch-progress/SKILL.md`
- [ ] `docs/skills/recipe-authoring/SKILL.md`
- [ ] Skills revised after `agent_api` names stabilize (pass 2)
- [ ] Skills mention only real import paths once code exists

**Notes:**

Initial skills written against ADR contracts before code exists. After API solidifies, update call examples to match real signatures.

### 17.1 Recipes (model-effect catalog)

Recipes live in `docs/recipes/<recipe-id>/RECIPE.md`; `_template/RECIPE.md` is authoring guidance. The curated recipe body is versioned and hashed; `## Recipe Notes` is append-only institutional memory.

- [ ] `docs/recipes/README.md` — catalog rules and proposal → recipe lifecycle
- [ ] `docs/recipes/_template/RECIPE.md` — structured effect recipe template
- [ ] Parse/lint recipe front matter and required sections
- [ ] Load/list/show immutable recipe versions with instruction hashes
- [ ] Append structured notes with run/evidence refs; reject edits/deletes to prior notes
- [ ] Compose compatible recipes into an immutable `RecipeStack` with ordered refs, overrides, allocation, and validation plan
- [ ] `RecipeStack` cannot bypass govern/admit/smoke/sealed measure/decide or weaken Objective hard gates
- [ ] Recipe retrieval is encouraged during planning, training-method choice, correction, and human-inbox reasoning
- [ ] Recipe notes inform planning but never satisfy measured gates alone
- [ ] Every governed use appends measured or failure evidence back to the relevant recipe notes
- [ ] Recipe instruction changes create a new version; notes do not change old operational meaning
- [ ] No secrets, raw private examples, or identifying data in recipe sources or notes

**Notes:**


---

## 18. Cross-cutting ADR §13.3 tests

Mirror of mandatory test categories — check off when green in CI/local pytest:

- [ ] admit leakage at dependence keys
- [ ] attribution/hidden-context rejection
- [ ] role/structure construction failure before generate
- [ ] claim≠execute and unsupported-action oracles
- [ ] smoke_then_scale denial without passing smoke
- [ ] scale denial on admission hash mismatch
- [ ] select does not pick last step when hard probes prefer earlier
- [ ] decide refuses promote on any hard fail
- [ ] decide routes human gates to `ask_human`
- [ ] sealed runner does not expose case text via planner-facing API
- [ ] suite pin required before admit-for-train
- [ ] preference pairs rejected if inputs differ
- [ ] preference train still fails decide when task hard gates drop
- [ ] recipe recommendation ranks relevant recipes from target effect, defects, notes, and prior outcomes
- [ ] recipe stack rejects incompatible or unapproved recipe combinations
- [ ] recipe notes append without changing the referenced instruction hash
- [ ] failed and non-promoted recipe uses still append structured evidence
- [ ] recipe application cannot weaken Objective hard gates or skip governed stages
- [ ] compat_check catches template/tokenizer drift
- [ ] CLI auto-focus ordering and empty state
- [ ] rollback restores previous pinned tuple
- [ ] private raw bytes refused on artifact write paths
- [ ] freeze and experiment denied without a saved MissionBrief
- [ ] individual hard-gate approvals are required in the MissionBrief

---

## 19. Success criteria (ADR §14)

- [ ] 1 — Save hashed MissionBrief, then freeze hashed Objective with gates/budget/baselines/suites
- [ ] 2 — Agent iterates data+train under budget without per-step human ops
- [ ] 3 — Hard enforced; soft cannot promote alone; diagnostic cannot select
- [ ] 4 — Sealed blind; paired compare includes base/ancestor/candidate
- [ ] 5 — Human inbox + CLI pressure
- [ ] 6 — Pin ReleaseTuple + reproducible dossier
- [ ] 7 — Bare `facktry` situational awareness
- [ ] 8 — Curated recipes compound through governed, measured, hashed RecipeStacks and append-only use notes/recommendations
- [ ] 9 — Ancestors hash-unchanged after corrective trains
- [ ] 10 — §13.3 / section 18 tests pass
- [ ] 11 — Every objective and experiment traces to an immutable MissionBrief containing intent, success case, research pointers, and hard-gate approvals

---

## Progress summary

Update timestamps (UTC) and counts whenever you edit this file.

| Area | Status | Last update (UTC) | Agent note |
|---|---|---|---|
| 0 Skeleton | [~] | red suite written; green impl pending |
| 1 Types | [ ] | | |
| 2 store | [ ] | | |
| 3 objective | [ ] | | |
| 4 govern | [ ] | | |
| 5 admit | [ ] | | |
| 6 verify | [ ] | | |
| 7 suite | [ ] | | |
| 8 play | [ ] | | |
| 9 judge | [ ] | | |
| 10 train | [ ] | | |
| 11 select | [ ] | | |
| 12 serve | [ ] | | |
| 13 decide | [ ] | | |
| 14 agent_api | [ ] | | |
| 15 watch CLI | [ ] | | |
| 16 domain packs | [ ] | | |
| 17 skills | [ ] | | |
| 17.1 recipes | [ ] | | |
| 18 mandatory tests | [ ] | | |
| 19 success criteria | [ ] | | |

**Currently in progress:** Phase 00 skeleton (red suite written; green impl pending)

**Phase doc:** `codebase_implementation_steps/active/phase_00_skeleton.md`

**Blocked on:** _(none)_

**Last global review:** 2026-08-07 — MissionBrief/elicit contract enshrined across ADR, operator foundation, and tool plans; implementation remains incomplete; no active phase.

---

## Agent handoff blurb (paste into new sessions)

```text
Implement facktry per /home/admin/facktry/docs/ADR.md.
Track progress only in /home/admin/facktry/docs/IMPLEMENTATION_CHECKLIST.md (update checkboxes in the same commit/change as code).
Operator skills are under /home/admin/facktry/docs/skills/ and recipes under /home/admin/facktry/docs/recipes/ — keep both aligned with `agent_api` and governed execution.
Do not build an MVP that bypasses govern/admit/smoke/measure. Do not depend on reference repositories at runtime.
```
