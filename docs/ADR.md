# ADR: Facktry — Autonomous Model Training Harness

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-05 |
| **Location** | `/home/admin/facktry` |
| **Audience** | Implementation agents and human overseers |
| **Authority** | This document is the sole product specification for facktry. Implement against it. Do not invent a reduced scope, “phase 1,” or temporary architecture that must be thrown away. |
| **Progress tracking** | `/home/admin/facktry/docs/IMPLEMENTATION_CHECKLIST.md` — agents **must** update checkboxes in the same change set as code. After context compaction, read ADR + checklist before coding. |
| **Operator skills** | `/home/admin/facktry/docs/skills/` — playbooks for the model that *runs* facktry (`agent_api`). Keep aligned with real API names as code lands. |
| **Operator recipes** | `/home/admin/facktry/docs/recipes/` — versioned, evidence-backed specifications for creating named effects in a model stack. |
| **Operator host** | `PI_FOUNDATION.md` — the isolated Pi session image launched by `facktry run`; it binds the operator to `questions`, `research`, recipes, and the eventual `agent_api`. |

---

## 1. Purpose

Facktry is an autonomous training harness. A human overseer states a mission, budget, hard principles, and final promote authority. A skilled LLM agent then iterates data construction, training, and evaluation inside policy until the mission’s gates pass or the budget is exhausted. The human does not drive trainers, write stage CLIs, or babysit loss curves. The human monitors live state, answers judgments that cannot be automated, and authorizes promotion.

Natural-language intent is not yet an executable objective. Before any objective is frozen, facktry runs an adaptive `elicit` stage: the operator uses structured human questions, researches between question volleys when useful, and assembles a complete, saved `MissionBrief`. Every objective and experiment—including a data investigation that never touches weights—requires that brief as part of its provenance.

**Deliverable of a successful model objective:** a pinned `ReleaseTuple` (the full shippable stack: base weights, adapter if any, tokenizer, chat template, prompt policy, tool/state schema, decode defaults, guard policy) plus a `Decision` whose cited hard gates are reproducible from content-hashed artifacts alone.

**Deliverable of a successful data-only objective:** admitted corpus artifacts plus a `Decision`. Corpus work is otherwise intermediate fuel for model objectives.

Facktry compounds model-development knowledge: the operator retrieves recipes during planning, training, correction, and human reasoning, then records outcomes for future selection. Model changes remain explicit, hashed, evaluated, and governed.

**Words in, model out** is the default shape for finetune objectives: harvest or synthesize data → admit → smoke train → scale train → select checkpoint → paired sealed measure → decide → yield `ReleaseTuple`.

---

## 2. Relationship to prior experiment work

A prior experiment factory on this machine demonstrated content-hashed runs, manifests, lineage, metrics streams, disposable local inference servers, and a trajectory-validation library. It did **not** close an autonomy loop: no frozen mission object, no fail-closed data admission as a prerequisite to train, no smoke-then-scale governor, no multi-gate checkpoint selection, no sealed blind eval custody, no defect memory, no human inbox, no promote/canary as first-class decisions, and no objective-centric live monitor.

Facktry is **greenfield**. It does not import, share registries with, or subclass prior experiment implementations. Behavioral ideas worth preserving (hash everything that affects a decision; lineage; append-only metrics; read-only observation separate from mutation) are restated in this ADR as facktry requirements. Engineering invariants from `SHARED_KNOWLEDGE.md` are folded into doctrine and module contracts below. Host-specific paths, voice case-study constants, and one-off hyperparameters are **not** part of facktry.

### Repository structure

Facktry is a monorepo with two first-class packages:

- **Python `facktry` package** — the harness, public CLI, `watch` surface, `agent_api`, persistence, policy, data, training, evaluation, decisions, serving, and domain-pack interfaces.
- **TypeScript `facktry-pi` package** — the isolated Pi operator runtime, launcher, resource loader, prompts, skills, extensions, research worker, and Pi-facing tools.

At repository level, keep the structure deliberately small:

```text
facktry/
├── Python package and its tests
├── facktry-pi/          # TypeScript Pi package and its tests
├── docs/                # ADR, plans, and implementation guidance
└── reference_repos/     # local prior art; ignored and never a runtime dependency
```

The Python and TypeScript packages are developed and released together, but remain separate build/install units. `facktry-pi` calls the Python `agent_api`; it does not duplicate `govern`, `store`, or other harness authority. The repository layout does not require one file or package per ADR module; internal file layout remains an implementation choice. Experiment state and artifacts live in the discovered `.facktry` workspace, not in either package.

---

## 3. Operator surfaces

Two surfaces. Do not collapse them.

| Surface | Who | Job | Mutates weights/data? |
|---|---|---|---|
| **`agent_api` + skills** | LLM agent | Elicit/save MissionBrief, freeze objectives, admit data, train, measure, decide, correct | Yes, under `govern` policy |
| **`facktry` CLI (`watch`)** | Human overseer | See live truth; work human inbox; inspect history | No in live view; inbox/promote acknowledgements only via explicit subcommands |

The agent must not require the human to type training commands. The human must not require run-id archaeology to answer “what is it doing?”

---

## 4. Doctrine

These are fail-closed laws. An implementation that violates them is incorrect even if demos look fine.

1. **Mission and objective before mutation.** Every objective and experiment, including data-only investigations, requires a saved `MissionBrief`; no data mutation, training, measure, or other experiment stage may start until its `Objective` is frozen with gates, baselines, budget, suite refs, and interface pins.
2. **Hard gates are code; soft gates are scores.** LLM judges never solely own safety, privacy, leakage, schema validity, split integrity, tool honesty, or claim≠execute.
3. **Scores change control flow or are labeled diagnostic.** Diagnostic metrics must not select checkpoints or authorize promote.
4. **Admit before train; smoke before scale; measure before promote.** Each arrow is enforced by `govern`, not by convention.
5. **Raw and guarded are both first-class.** Serving retries and filters must not hide unguarded model failures in any `Decision`.
6. **Paired comparison for model decisions.** Candidate is judged against base and, when they exist, ancestor and production wrapper—same suite hash, seeds, state, and decode config.
7. **Interface lock.** Train, eval, and serve load one `ReleaseTuple` identity. Drift is a failed gate (`compat_check`).
8. **Sealed suites are blind to the planner.** Sealed execution returns aggregates and `GateResult`s. Case text from sealed suites must not enter agent planner context.
9. **Preserve ancestors.** Every train attempt is a new run directory. Never overwrite base, ancestor adapters, or prior pinned releases.
10. **Human only at irreducible boundaries.** Taste, research fit, borderline adjudication, policy break-glass, final promote. Not loss curves. The CLI surfaces those boundaries; it does not micro-drive training.
11. **Domain logic in domain packs.** Core remains task-agnostic. No SMS-, trajectory-edit-, or customer-specific rules in core modules.
12. **Rugged composition.** One control loop. Few modules. Thin protocols. No parallel type zoos, workflow engines, or plugin religions that do not change a `Decision`.
13. **Bare `facktry` shows live truth.** Auto-focus active objective/run/inbox. No mandatory registry-path or run-id flags for the common case.
14. **Optimize the stack, not only weights.** Model + data + prompt/interface + serve/guards are one release. Good loss with a wrong template or guard is failure.
15. **Private data never becomes an artifact.** Raw or identifying text is memory-scoped and local. Artifacts hold hashes, counts, policy ids, redacted derivatives, aggregates.
16. **Freeze measure before new train data.** Sealed suite content hashes pin before corpus generation for that objective iteration.
17. **Synthetic data is coverage, not quality proof.** Generation feeds deterministic admit; quality is sealed/human measure on held-out suites.
18. **No self-distillation by default.** Teachers and train parents default to frozen base or explicit ancestor—not the deployed specialist—unless the objective records an explicit waiver.
19. **Attribution integrity.** Every fact required to produce a training target must appear in the visible model input, verified state, or an authorized tool result available at inference. Hidden scenario briefs in targets are a hard admit failure.
20. **Multi-turn for dialogue.** Conversational objectives require multi-turn suites and play; single-turn probes alone are insufficient for measure or promote.
21. **Elicit before freeze.** Natural-language missions must pass adaptive elicitation before freeze. The operator follows the `elicit` skill’s outline, chooses the question path, uses the structured questions tool for human input, and may use isolated research between volleys. The human approves every proposed hard gate individually. Research is proposal evidence, not a gate.
22. **Intent is durable provenance.** The completed MissionBrief is saved as an immutable version before `freeze_objective`; it records the user’s request, success case, research pointers, and gate approvals. Session chat alone never satisfies this requirement.
23. **Recipe-guided compounding.** During planning, training, correction, and human-interactive reasoning, the operator should retrieve relevant recipes, notes, defects, and prior outcomes; successful or failed uses append structured evidence back to the recipe book. Catalog growth improves candidate selection but never replaces fresh measurement, hard gates, or human authority.

---

## 5. Core objects

Serializable, boring, hashed when they affect decisions. Do not grow ontology for its own sake; every type below participates in control flow or provenance.

### 5.0 `MissionBrief`

Saved, versioned intent dossier required for **every objective and experiment**, including a data investigation that may never produce or modify a model. A working draft may live in the operator session while elicitation is in progress, but no experiment or objective freeze may proceed until the complete dossier is saved.

Each save creates an immutable version with a stable brief id, version number, parent version when applicable, content hash, originating operator session, and timestamp. A post-freeze change creates a new brief for a superseding Objective; prior versions remain readable.

Required fields:

| Field | Meaning |
|---|---|
| `id` / `version` | Stable brief identity and immutable version number |
| `brief_hash` | Content hash over the saved dossier bytes |
| `parent_version` | Prior version when this is a revised pre-freeze dossier |
| `operator_session_id` | Pi/operator session that conducted elicitation |
| `raw_mission` | Original human request, preserved verbatim where allowed |
| `dossier` | Structured intent, success case, constraints, evaluation plan, and question history |
| `hard_gate_approvals[]` | Exact proposed hard gates and individual human responses |
| `research_notes[]` | One-line summaries, stable references, retrieval metadata, and research run/artifact refs |
| `recipe_considerations[]` | Recipe refs/versions and notes consulted, human tradeoffs, and selected/rejected effect candidates; planning provenance, not measured evidence |
| `objective_ref` | Optional draft/frozen Objective reference when known; the Objective→MissionBrief link is authoritative, and adding a reverse index never mutates brief bytes |
| `created_at` | Save timestamp |

Required contents:

- original human mission and the human-readable intent
- deliverable, domain/task, and audience
- the human’s definition of a success case
- failure cases, anti-goals, and must-not-regress behavior
- baselines and relevant constraints, data limits, and budget
- evaluation plan and proposed suites/checkers
- every proposed hard gate with its exact definition and **individual human approval**
- question rounds: exact prompts, accepted answers, values/details, order, and meaningful revisions
- very brief one-line research summaries with references (URLs, paper ids, or other stable pointers), retrieval metadata, and research run/artifact refs; full paper bodies are not required in the brief and may be fetched later
- recipe candidates and relevant notes consulted during elicitation or human-interactive reasoning, the human’s material tradeoff decisions, and any selected/rejected effect rationale; recipe notes remain planning evidence
- open assumptions and any draft Objective reference

The MissionBrief is provenance and intent evidence, not a measured `GateResult`; research recorded in it remains proposal evidence. The canonical `elicit` skill defines the required outline, while the operator chooses its own path through follow-up questions.

### 5.1 `Objective`

Frozen mission contract. Immutable after freeze except via **supersede** (new objective id that references the old one).

Required fields:

| Field | Meaning |
|---|---|
| `id` | Stable unique id |
| `mission_brief` | Exact saved `MissionBrief` version ref + content hash; required for every objective |
| `intent` | Human-readable mission |
| `deliverable` | `release_tuple` \| `admitted_corpus` \| both |
| `gates[]` | Hard/soft/human/diagnostic gates with thresholds, directions, suite or checker refs |
| `constraints` | Privacy tier, self-distill waiver flag (default false), interface pins, offline-only, max adapter rank, etc. |
| `budget` | Wall time, GPU-hours, judge tokens, max smoke runs, max scale runs |
| `baselines` | `ReleaseTuple` refs: `base` required for model objectives; `ancestor` and `production` when they exist |
| `suites` | Dev and sealed suite refs **with content hashes** |
| `dependence_keys` | Fields that define leakage units (e.g. `prompt_id`, `thread_id`, `scenario_id`, `template_id`) |
| `mixture` | Optional `MixtureSpec` / `TargetShape` |
| `policy` | Autonomy hooks: what auto-runs vs `ask_human`; `human_promote` default **true** for model deliverables |
| `interface` | Pinned prompt policy, tool schema, decode profile ids that candidate tuples must match |
| `recipe_policy` | Optional target effects, allowed/forbidden recipe ids, stack-size and compatibility constraints; exact stacks are recorded per run |

**Freeze lint (must refuse freeze on violation):**

- A complete saved `MissionBrief` version exists, its hash is recorded, and its deliverable matches the Objective.
- Every required universal and domain-specific brief section is complete; raw intent alone is insufficient.
- Every proposed hard gate has an exact definition and explicit individual human approval recorded in the brief.
- Every hard gate is machine-checkable **or** explicitly severity `human`.
- Model deliverables name at least one paired model suite and a `base` baseline.
- Sealed suite hashes are present before any generate/train under this objective (or freeze includes the suite artifacts to be pinned immediately as step one of the loop).
- Budget all non-negative; at least one exhaustion behavior defined (`hold` or `abort`).
- `dependence_keys` non-empty when any split data will exist.
- Constraint `no_self_distill` defaults true.
- When `recipe_policy` or a preselected `RecipeStack` is present, recipe refs/hashes, compatibility constraints, and validation requirements lint successfully; no selected stack weakens an Objective hard gate.

### 5.2 `ReleaseTuple`

The only shippable model identity. Promotion pins one. Eval loads them. Train emits a candidate.

| Component | Requirement |
|---|---|
| `base_model` | Ref + content hash (weights or immutable store id) |
| `adapter` | Ref + hash, or null |
| `tokenizer` | Revision + hash |
| `chat_template` | Content hash of exact template bytes used |
| `prompt_policy` | Id + hash (system variants, mode rules) |
| `tool_schema` | Id + hash (may be empty schema) |
| `decode` | Id + full config hash (temp, top_p, max tokens, stop, seed policy) |
| `guards` | Id + hash of guard policy |
| `recipe_stack` | Exact `RecipeStack` ref + hash used to create this tuple, or null when no recipe was applied; provenance, not an independent serving component |
| `tuple_hash` | Hash over all component hashes and the recipe-stack hash |

`compat_check(a, b)` passes only when tokenizer, chat_template, prompt_policy, tool_schema, and decode hashes match (or differ only on fields the objective explicitly allows, e.g. adapter weights during train-vs-base compare). Guard hash may differ only when comparing raw vs guarded channels deliberately.

### 5.3 `Run`

One attempt at one unit of work.

| Field | Meaning |
|---|---|
| `run_id` | Unique |
| `objective_id` | Owning mission |
| `mission_brief` | Exact saved MissionBrief version/hash inherited from the Objective |
| `stage` | Free string from a small core set plus domain stages: e.g. `generate`, `filter`, `admit`, `train_smoke`, `train_scale`, `select`, `measure`, `decide`, `canary` |
| `status` | `pending` \| `running` \| `completed` \| `failed` \| `guarded` \| `blocked` |
| `parents[]` | Lineage run ids + relation labels |
| `spec` | Parameters without secret materialization |
| `code_hash` | Source tree / package version hash |
| `env` | Freeze record (python, CUDA, key packages, offline flags) |
| `hardware` | GPU/CPU/disk snapshot at start |
| `inputs[]` / `outputs[]` | `Artifact` refs |
| `guard_report` | Optional structured trip record |
| `metrics_path` | Append-only metrics stream |
| `recipe_stack` | Exact `RecipeStack` ref + hash used by this run, when applicable |

### 5.4 `Artifact`

`path + sha256 + role + producer_run_id + created_at + media_type?`

**Source-class roles** (when applicable): `public`, `fictional`, `private_redacted`, `synthetic`, `replay`, `preference`, `train`, `dev`, `seal`, `report`, `checkpoint`, `tuple`, `decision`, `scorecard`, `admission`, `mission_brief`, `recipe`, `recipe_stack`, `recipe_evidence`, `log`.

Raw private sources are never artifacts. If private data is read, it is in-process only; on-disk products are redacted or aggregate.

### 5.5 `Gate` / `GateResult`

| Field | Meaning |
|---|---|
| `name` | Stable id |
| `severity` | `hard` \| `soft` \| `human` \| `diagnostic` |
| `comparator` | e.g. `<=`, `>=`, `==`, `in_range`, `zero` |
| `threshold` | Numeric or enum |
| `suite_ref` / `checker_ref` | What produced the observation |
| `channel` | `raw` \| `guarded` \| `n/a` |
| `observed` | Value |
| `passed` | Bool |
| `evidence[]` | Artifact refs |

### 5.6 `Scorecard`

Result of running a suite against one `ReleaseTuple` (or corpus subject where applicable).

Must include:

- suite content hash, seed list, decode hash, subject tuple hash
- applied `RecipeStack` hash when applicable
- per-dimension aggregates listed in §7.4 (not a single blended “quality”)
- `raw` and `guarded` channels when guards exist—both always populated for model serve paths
- findings with severity
- slice tables by case family when families exist
- resource block: wall time, tokens, peak VRAM if known

### 5.7 `Decision`

| Field | Meaning |
|---|---|
| `action` | `promote` \| `hold` \| `correct` \| `abort` \| `ask_human` |
| `objective_id` | |
| `mission_brief_ref` | Saved brief version that grounded the objective and decision |
| `subject` | Candidate tuple and/or corpus artifact refs |
| `recipe_stack_ref` | Exact applied `RecipeStack` ref + hash, when applicable |
| `gate_results[]` | All cited results |
| `intervention` | When `correct`: class `data` \| `mixture` \| `rubric` \| `hparam` \| `interface` \| `stop` plus machine-readable hint |
| `human_requests[]` | When `ask_human`: inbox item specs |
| `dossier_ref` | Artifact humans can read in one pass |
| `created_at` | |

**Aggregation rules (normative):**

- Any failed `hard` gate → cannot `promote`.
- Any pending `human` gate → `ask_human` (or `hold` if inbox disabled by policy, which is non-default).
- Failed hard gates with known intervention mapping → prefer `correct` over `abort` while budget remains.
- Budget exhausted → `hold` or `abort` per objective, never silent continue.
- Soft failures alone → `correct` or `hold`, never `promote`.
- Diagnostic failures never block or promote by themselves; they may appear in the dossier.

### 5.8 `Defect`

Durable memory so the agent does not rediscover the same failure every session.

| Field | Meaning |
|---|---|
| `id` | |
| `taxonomy` | Controlled vocab, extensible (e.g. `hidden_context`, `split_leakage`, `self_distill_risk`, `claim_not_executed`, `retention_drop`, `schema_construction`, `over_specialize`, `pref_degraded_task`, `interface_drift`, `privacy_emit`, `collapse_nonfinite`, `keep_rate_out_of_band`) |
| `evidence[]` | |
| `first_run_id` / `last_run_id` | |
| `interventions[]` | What was tried + gate deltas |
| `status` | `open` \| `closed` \| `wont_fix` |

### 5.9 `Policy` / `BudgetLedger`

Policy: allow/deny for agent capabilities (`train.scale`, `train.smoke`, `serve.flip_default`, `data.use_private`, `data.remote_send`, `judge.use`, `objective.supersede`, …).

BudgetLedger: remaining wall time, GPU-hours, judge tokens, smoke/scale counts. `govern` decrements and blocks when insufficient for the requested action.

### 5.10 `TrainCard`

Twin of every train checkpoint set. Required fields:

- objective id, run id, linked MissionBrief version/hash, parent tuple hash
- admission report hash, mixture/source-class counts
- interface / tuple component hashes used at train time
- effective example count, optimizer steps, token counts
- **repeated-example exposure** (how often identical dependence keys were seen)
- target-length summary
- lr schedule summary, seed
- peak VRAM, wall time
- teacher id (synth) and/or reference id (preference)
- best checkpoint ref under gate callbacks if any
- recipe stack hash and any recipe-specific adaptations

### 5.11 `MixtureSpec` / `TargetShape`

When the objective declares distributional requirements:

- dimensions: domain, task/action, length band, interaction type, source class
- floors and caps per dimension
- replay / OOD quota (anti over-specialization)
- unknown-state, ambiguity, pivot quotas when abstention and topic-shift matter

`admit` compares observed counts to the spec. Violations are hard or soft per objective configuration; if soft, they must still appear on the `AdmissionReport`.

### 5.12 `AdmissionReport`

Required output of every admit. Train stages must reference a **passing** report hash.

Include: input artifact hashes; keep/reject counts; **reject-reason histogram**; dependence-key overlap matrix train/eval/seal; near-dupe and template-family stats; mixture deltas vs `TargetShape`; teacher id; transformation policy id + seeds; suite hash that was already frozen; pass/fail + gate results.

### 5.13 `HumanInboxItem`

| Field | Meaning |
|---|---|
| `id` | |
| `objective_id` | |
| `gate_name` | Why the human is needed |
| `payload_ref` | Blinded artifacts when required |
| `response_schema` | Structured answer spec |
| `created_at` / `age` | |
| `status` | `pending` \| `answered` \| `expired` |

### 5.14 `Recipe` / `RecipeStack`

A `Recipe` is a versioned, evidence-backed specification for creating a named behavioral effect in a model stack. It is not merely a research recommendation, prompt fragment, hyperparameter dump, or guarantee. Its ingredients may span data, training, prompt/interface, serving, and evaluation because facktry optimizes the released stack rather than weights in isolation.

The canonical human-authored source is `<recipe-id>/RECIPE.md` under `docs/recipes/`. The facktry parses it into a `Recipe` artifact with a stable instruction hash over front matter and instructional sections, plus an append-only notes head/hash for the notes stream. A full source snapshot may also be registered for audit. A recipe source must declare:

- stable id, version, title, status, target effect(s), and observable measures
- scope and applicability: model families, domains, interfaces, prerequisites, and incompatibilities
- mechanism: why the ingredients are expected to create the effect
- ingredients: data/source classes and mixture constraints; training method/parent/reference and safe parameter ranges; interface/serving changes; evaluation suites and baselines
- ordered governed procedure, adaptation knobs, tradeoffs, regressions, and failure signatures
- evidence, tested configurations, curator, and provenance
- an append-only `## Recipe Notes` section for subsequent uses

A `RecipeProposal` returned by research is provisional evidence. It becomes a reusable `Recipe` only when curated into a reviewed `RECIPE.md`; research never silently edits the catalog.

A `RecipeStack` is an immutable composition for one objective iteration or run. It records ordered recipe refs and hashes, resolved parameter overrides, ingredient allocation, compatibility/conflict decisions, and the validation plan. Stacks are selected under the Objective's `recipe_policy`, never by unconstrained concatenation. Every governed run and resulting `ReleaseTuple` records the exact stack hash.

Recipe notes are append-only institutional memory. A note records the date, run/objective, base and surrounding stack, adaptation, observed effect, regressions, evidence refs, recommendation, and confidence. Each note is separately hashed and advances the notes head; notes may inform future composition but cannot satisfy a gate by themselves. Changing recipe instructions creates a new recipe version; appending a note does not change the instruction hash or operational meaning of the prior version. Notes contain no secrets, raw private examples, or identifying data.

Recipes and stacks cannot weaken Objective hard gates, bypass `govern`, `admit`, smoke training, sealed measurement, `decide`, or human promotion. The intended effect must be demonstrated by the ordinary paired evaluation path.

---

## 6. Status machine

```text
pending → running → completed
                  → failed
                  → guarded    # guard tripped; best artifacts may exist
                  → blocked    # govern/policy/budget refused start
```

Lineage is via parent edges, not a global enum of every science stage ever invented. Domain packs may add stage names freely; core interprets status and lineage, not domain semantics.

---

## 7. Modules

Each module has one job. File layout is the implementer’s choice; **behavioral boundaries are not**. Cross-module calls go through clear functions; modules share `store` as the source of truth.

### 7.0 `elicit`

**Job:** turn a human mission into a complete, durable `MissionBrief` before objective freeze or any experiment.

Requirements:

- Start from the human’s natural-language mission and use the canonical `elicit` skill as an outline, not a rigid decision tree. The operator chooses its own adventure while covering every required universal and domain-specific section.
- Use the Pi `questions` tool (or an equivalent structured human-I/O port) for question volleys. Use the isolated `research` tool between volleys when research can make the next questions or proposals more useful.
- Cover intent/deliverable, domain/task/audience, success case, failure cases and anti-goals, baselines and must-not-regress behavior, constraints/data/budget, and the evaluation plan.
- Present proposed hard gates for **individual human approval**. The operator may propose thresholds and definitions, but may not silently authorize them.
- At the end of elicitation, call `save_mission_brief` once with the complete dossier. The saved version is immutable and includes one-line research summaries plus references; it is not a full paper archive.
- Refuse or block `freeze_objective` and every experiment path when the required brief is absent, incomplete, or unsaved. A session transcript or partial question result is not a brief.
- `elicit` does not measure quality, pass gates, or treat research recommendations as proof.

### 7.1 `store`

**Job:** durable, queryable truth for runs, artifacts, objectives, decisions, defects, inbox, budgets, metrics.

Requirements:

- Filesystem run directories + sqlite (or equivalent) index is acceptable.
- Content-hash every artifact at write; refuse register if hash mismatches bytes.
- Atomic manifest writes.
- Queries at minimum: get/list mission briefs and immutable versions; get/list runs by objective/status/stage; parents/children; get/list/version recipes and append recipe notes; recommend recipes by target effect, objective, defects, and prior outcomes; get/list RecipeStacks; latest passing `AdmissionReport` for objective; open defects; pending inbox; latest decision; active/frozen objectives; pinned production tuple; metrics tail for a run.
- **No agent-facing delete** of runs that are parents, pinned releases, or referenced by decisions, nor of MissionBrief versions referenced by objectives or experiments. Archival may exist as an explicit overseer operation outside the agent tool allowlist.  
- Workspace discovery: `FACKTRY_HOME` if set, else walk cwd/parents for `.facktry/`, else create `.facktry/` in cwd per policy. Humans and agents must land on the same workspace without flag gymnastics.

### 7.2 `objective`

**Job:** load, lint, freeze, supersede, show objectives.

Requirements:

- Freeze persists objective bytes + hash; subsequent loads verify hash.
- Lint rules in §5.0–§5.1 are mandatory, including the saved MissionBrief and individual hard-gate approvals.
- Supersede creates a new id; does not mutate the old record.
- Expose “open objectives” for CLI auto-focus.
- Validate any selected `RecipeStack` against `recipe_policy`, recipe hashes, applicability, conflicts, and budget before freeze or execution.

### 7.3 `admit`

**Job:** fail-closed data admission and the only blessed synthetic path.

#### 7.3.1 Checks (normative)

1. **Schema / structure** — required fields present; types valid; for dialogue, role alternation and turn structure valid. Structure checks run at **scenario construction time** and again on materialized rows. Construction failures must not require a GPU generate to discover.
2. **Dependence-key leakage** — train ∩ eval ∩ seal empty at configured keys. Row-id disjointness alone is insufficient.
3. **Diversity meters** — unique inputs, unique final turns, template-family entropy/collapse caps, near-duplicate caps. Large N is not a pass.
4. **Attribution** — every factual claim in targets must be supported by visible input, verified state, or authorized tool result. Hidden briefs in generator context that leak into targets are hard fails.
5. **Controlled vocabs** — labels/tags/transforms in declared enums.
6. **Mixture** — vs `TargetShape` when present.
7. **Source class** — every row labeled; raw private write attempts fail.
8. **Teacher identity** — synth rows record teacher; default enforcement base/ancestor only.
9. **Suite pin** — refuse admit for training use if objective’s sealed suite hash is not frozen.

Emit `AdmissionReport`. Train must not start without a passing report ref in the train run’s inputs.

#### 7.3.2 `generate_and_admit`

Single blessed pipeline for synthetic data:

1. Construct scenarios with explicit verified state; validate structure.
2. Generate bounded candidate batch (**more candidates than will be kept**).
3. Deterministic filter: grounding, unsupported actions, structure, privacy patterns as configured.
4. Admit survivors; require reject-reason histogram and coverage floors.
5. Only then is smoke train allowed on this mixture.

Parallel generation: deterministic global candidate indices; per-part manifests; merge is concatenation under index order, not a new sample. Seeds and transformation policy recorded.

Default teacher: frozen base or ancestor tuple—not production specialist—unless objective constraint waives with recorded reason.

### 7.4 `verify`

**Job:** deterministic oracles producing findings. Cheap by default.

Minimum oracle capabilities:

| Oracle | Failure meaning |
|---|---|
| Schema/grammar/JSON | Malformed structured output |
| Regex/canary/PII | Privacy or memorization emit |
| State transition | World state inconsistent with claims |
| Claim≠execute | Text asserts side effect without tool-confirmed success |
| Unsupported action | Action not authorized by schema/policy |
| Entailment | Claim not supported by supplied evidence docs |
| Execution | Code/SQL/etc. unit failure |
| Abstention | Confident answer where state is insufficient (when configured) |

Structural tagging where possible: `known_from_input`, `retrieved_by_tool`, `user_requested`, `tool_confirmed`.

Hard findings feed hard gates. Machine-checkable safety lives here and in `serve` guards—not as long refusal essays baked into every training target (safety–style conflation).

### 7.5 `suite`

**Job:** frozen eval sets, execution, paired compare.

Requirements:

- Registry of suites with **content hashes**. Cases carry: id, family/slice, split (`dev`|`seal`), dependence keys, visible input, private state (runner-only), authorized tools, verifiers, tags.
- Case kinds: single-turn; multi-turn trajectory; tool episode; preference pair; OOD/capability retention probe; robustness cell (length, prompt variant, temperature); differential pair.
- **Dev** suites: inspectable by agent.
- **Sealed** suites: executed via blind runner. Planner API returns scorecards/aggregates/gate results only—not case stems, private state, or full transcripts. Implementation must make accidental sealed leakage difficult (separate process or equivalent custody boundary).
- Execution pins seeds, decode config, and subject `ReleaseTuple`.
- `compare(tuples, suite)` runs the same suite on each tuple and emits paired deltas, slice tables, and no-worse-than evaluations against objective margins.
- Compare set for model decisions: **base**, **ancestor** (if any), **candidate**, **production wrapper** (if any).

**Scorecard dimensions** (report separately; do not collapse into one vanity score):

1. Task/action correctness  
2. Unsupported claim / hallucinated-state rate  
3. Abstention / clarification / false-refusal  
4. Capability retention outside target domain  
5. Robustness (context length, prompt variants, temperatures)  
6. Privacy / memorization  
7. Preference win rate and margin (when applicable)  
8. Style / distribution distance to reference  
9. Repetition / duplicate / semantic diversity  
10. Raw failures vs guarded failures  
11. Resource use, latency, memory headroom  

Distributional metrics alone never select checkpoints or promote. Suite hashes for an objective iteration freeze **before** generating that iteration’s training corpus.

### 7.6 `play`

**Job:** produce trajectories/episodes for harvest and for suites.

Requirements:

- Subject↔partner loop with **hard runner-side turn caps** (stop tokens are advisory; models ignore them).
- `World` protocol for tool/domain tasks: `reset(seed, scenario) -> obs`, `step(action) -> (obs, done, info)`, `oracle_state() -> private`, `export_transcript()`.
- Private world/simulator state never enters subject prompts or open persisted artifacts.
- Partner (faux-human) config: model/config id, engagement length, per-turn instructions, pain points, visible stop sequence.
- When partner is model-driven, emit a **simulator-realism scorecard** separate from the subject scorecard.
- Run deterministic analyzers on transcripts before any LLM judge.

Dialogue objectives must exercise `play` in measure, not only single-turn prompts.

### 7.7 `judge`

**Job:** optional LLM assessment. Never sole owner of hard gates.

Requirements:

- Batch assessment of trajectories/outputs against caller-supplied criteria (criteria hash recorded).
- Optional corpus overseer for aggregate pathologies (canned openings, mode collapse, cross-session repetition).
- **Calibration fixtures** ship with the harness. After any judge model/prompt/criteria change, calibration must pass before judge outputs may count as soft gates. Failed calibration → judge severity forced to diagnostic.
- Pairwise compares: swap position order; record both legs.
- Replay mode: apply new criteria to hash-pinned historical trajectories without resampling the population.
- Redact private content before sending to remote judges; prefer local judges when privacy constraints demand.

### 7.8 `train`

**Job:** weight updates that emit checkpoints, `TrainCard`s, and metrics—never silent overwrites.

Requirements:

- Plugin interface for methods; required methods: **SFT** and at least one **preference** method (DPO or equivalent). Additional methods may exist but must obey the same cards, callbacks, and parent rules.
- **Target-only loss** by default for SFT (prompt tokens masked).
- Conservative defaults for capacity, learning rate, and steps until sealed suites justify stronger steering (objective may set bounds; harness should not ship reckless defaults).
- Init from declared parent `ReleaseTuple` only. Corrective training is a **new run** from base or ancestor—not continued training that destroys the parent.
- Mixture includes domain data plus replay/OOD when the objective’s `MixtureSpec` requires it.
- Metrics: append-only stream suitable for `watch` (step, loss, probe scores, lr, grad norm, tokens, wall).
- **Callbacks (mandatory):**
  - nonfinite / collapse detection → `guarded`, save guard checkpoint
  - periodic **mini sealed probe** (tiny frozen subset or dedicated smoke suite)
  - keep-best checkpoint under hard probe constraints
  - VRAM and budget envelope → stop cleanly, persist best
- Every attempt writes a complete `TrainCard`.

#### Preference pair contract (normative)

Admit and train must enforce:

| Rule | |
|---|---|
| Chosen | Defensible source or explicit rubric |
| Rejected | Concrete undesirable behavior, not a random alternate |
| Input identity | **Identical** visible input and state for both sides |
| Eval pairs | Held-out subjects/templates |
| Reference | Frozen reference model/adapter; hash preserved |
| After train | Re-run task, grounding, privacy, retention, diversity, deployment suites—not only preference accuracy/margin |

Preference improvements that degrade hard task gates produce `correct` or `hold`, never `promote`.

### 7.9 `select`

**Job:** choose a checkpoint under constraints.

```text
maximize configured soft objectives
subject to all hard gates ≥ baseline − margin (or absolute floor)
```

Forbidden defaults: “last step wins,” “minimum training loss wins,” “minimum val CE wins” as the sole rule.

Emit a ranking artifact: candidates considered, gate matrix, winner, rationale. Winner becomes the adapter component of the candidate `ReleaseTuple`.

### 7.10 `govern`

**Job:** control plane. If govern can be bypassed by calling `train` directly, the design is wrong—mutation paths go through govern checks.

Responsibilities:

| Check | Behavior |
|---|---|
| `preflight` | Resolve paths; env; disk headroom; GPU free memory; driver usable; record hardware; verify rollback/preservation paths exist; **refuse to co-place mutually exclusive large model services on the same GPU** |
| `smoke_then_scale` | `train_scale` requires a linked smoke run: status completed, Decision allowing scale, compatible `code_hash`, compatible `AdmissionReport` hash (or explicit declared delta artifact), memory envelope within tolerance of smoke |
| `budget` | Deny actions that exceed ledger |
| `compat_check` | Interface lock across tuples |
| `policy` | Allow/deny tools including `data.use_private`, remote send, promote flip |
| `suite_pin` | Deny generate/admit-for-train if sealed suite not frozen for objective |

Canonical interface is pinned on the objective. Prompt variants may exist for robustness testing; they are not a substitute for data diversity. Safety instructions in prompts stay short enough that they do not become the model’s learned style; enforcement stays in verify/serve.

### 7.11 `serve`

**Job:** load a full `ReleaseTuple`, apply guards, support canary and rollback.

Requirements:

- Load all tuple components; refuse partial loads for production paths.
- Guard policy as data: unsupported-action, claim≠execute, PII/canary, repetition, mode-leak, schema validate—as configured by hash.
- Every response path can emit **raw** and **guarded** records.
- Retries only for bounded, classifiable failures. Fallback short, truthful, non-destructive.
- Logs quiet by default; retain summaries, errors, metrics, hashes—not private payloads.
- Canary: side endpoint; paired probes against production; flip default only under policy (default requires human promote Decision).
- Rollback: one call restores previous pinned tuple; tested in automated tests with fixtures.

Guards are part of the released system. Decisions always show unguarded model quality too.

### 7.12 `decide`

**Job:** pure aggregation from evidence to a `Decision` (plus dossier write).

Inputs: scorecards, admission reports, train cards, gate configs from objective, budget state, open human gates, defect context.

Apply §5.7 aggregation rules. Write dossier artifact: intent, subject hashes, gate table, failing evidence pointers, intervention hint, budget remainder. Dossier must be readable without opening a dozen files.

Map common failures to intervention classes to feed defects (examples):

| Pattern | Intervention class |
|---|---|
| Attribution/hidden context | `data` |
| Mixture collapse / over-specialize | `mixture` |
| Keep-rate absurd / rubric wrong | `rubric` |
| Smoke OOM or unstable loss | `hparam` |
| Train/serve template mismatch | `interface` |
| Budget blown | `stop` |

### 7.13 `agent_api`

**Job:** stable facade for the LLM agent. This is the mutation API.

Required operations (names may be bikesheded but capabilities may not):

| Operation | Governed effects |
|---|---|
| `save_mission_brief` / `show_mission_brief` / `list_mission_briefs` | Save one complete immutable brief version at the end of elicitation; inspect intent provenance |
| `freeze_objective` / `show_objective` / `supersede_objective` | Objective lifecycle; freeze requires the saved brief |
| `preflight` | `govern.preflight` |
| `pin_suites` | Freeze sealed/dev hashes on objective |
| `admit` / `generate_and_admit` | Data path |
| `run_stage` | Domain stage in a run |
| `train_smoke` / `train_scale` | Train path |
| `select_checkpoint` | Checkpoint → candidate tuple |
| `measure` / `compare` | Suites |
| `decide` | Decision + dossier |
| `inbox_list` / `inbox_ingest` | Human loop (ingest usually from CLI; agent may read) |
| `defects_list` / `defects_close` | Memory |
| `yield_release` | Pin tuple after authorize |
| `query_*` | Read models shared with CLI |
| `list_recipes` / `show_recipe` | Discover curated effect recipes and their append-only notes |
| `recommend_recipes` | Rank relevant recipes from target effects, objective constraints, open defects, notes, and prior outcomes; read-only proposal |
| `compose_recipe_stack` | Resolve compatible recipe versions and overrides into an immutable stack; no mutation or gate bypass |
| `append_recipe_note` | Append a structured subsequent-use note with run/evidence refs; never edits recipe instructions |

`save_mission_brief` is the only blessed persistence path for the dossier. Each call creates a new immutable version, returns its ref and hash, and may not overwrite a prior version. The call is made once at the end of elicitation; a working draft remains session-scoped until then.

All operations return structured results (status, artifact refs, errors). Secrets expand from a secret store; never write secret values into manifests.

### 7.14 `watch` (human CLI)

**Job:** situational awareness and narrow human response. First-class module—not a afterthought script.

#### 7.14.1 What to learn from the prior experiment CLI—and what to refuse

**Carry forward:** registry-backed state; lineage; append-only metrics streams; read-only live rendering; machine probes (GPU, disk, process heartbeat); separation of mutation from observation.

**Refuse:** bare invocation that does nothing useful; mandatory `--watch-run` / registry path for common case; subprocess hop to a second entrypoint for default live view; experiment-specific dashboard JSON as a prerequisite to see anything; run-list-centric UI without objective, decision, defect, and inbox.

#### 7.14.2 Commands

| Invocation | Behavior |
|---|---|
| `facktry` · `facktry cli` · `facktry watch` | Default **live** monitor; auto-focus; continuous refresh |
| `facktry status` | One-shot snapshot of the same focus (SSH/scripts) |
| `facktry inbox` | List pending human items; subcommands to respond/ingest |
| `facktry show <id>` | Deep dive; auto-detect MissionBrief/objective/run/decision/tuple/scorecard |
| `facktry ls` | Recent runs/decisions/objectives |

Optional flags (`--objective`, `--run`, `--once`, `--refresh`, `--home`) exist but are not required for common monitoring.

#### 7.14.3 Auto-focus order

When no id is provided:

1. Item waiting on **human inbox** (loudest)
2. Newest **running** run
3. Newest **blocked** or **guarded** run
4. Newest saved **MissionBrief** not yet attached to a frozen Objective
5. Newest open **frozen objective**
6. Newest **Decision** + pinned tuple summary
7. Empty state with concrete next step (“no active objective; agent must elicit and save a MissionBrief”)

#### 7.14.4 Default live layout (fixed)

Objective-centric, fixed panes—no per-domain JSON required:

- **Header:** objective id · MissionBrief id/version/hash · intent (truncated) · autonomy · budget remaining · time in phase  
- **Loop position:** elicit → save_brief → freeze_objective → pin_suites → admit → smoke → scale → select → measure → decide (current highlighted)  
- **Active run:** id · stage · status · parent · started · latest metrics spark  
- **Gates:** hard/soft; raw vs guarded; failures first  
- **Decision:** latest action · one-line rationale  
- **Defects:** open top-N taxonomy labels  
- **Inbox:** count · oldest age · gate reasons (visually loud if non-zero)  
- **Release:** short hashes base vs candidate vs pinned prod  
- **Machine:** GPU util/mem/temp · disk free · train/infer heartbeats  
- **Log tail:** active run primary log last lines  

Live refresh never starts training. Inbox respond and promote ack are explicit subcommands only.

#### 7.14.5 Implementation constraints

- In-process live renderer (e.g. Rich Live). **No** subprocess hop for default path.
- Same `store` queries as `agent_api`.
- Missing metrics/logs degrade panes; they do not crash the monitor.
- `facktry status` shares render/snapshot code with live mode.
- Automated tests cover auto-focus ordering and empty-state behavior.

### 7.15 Domain packs

**Job:** task-specific science without core contamination.

A domain pack supplies:

- elicitation branches and required MissionBrief sections  
- schemas and controlled vocabs  
- generators, filters, labelers, stratifiers  
- suite cases and domain oracles  
- prompt policies and tool schemas  
- optional stage implementations callable via `run_stage`  

Core never imports a concrete domain’s rules. Packs register through an explicit registry pattern.

### 7.16 Skills

Short markdown playbooks under `docs/skills/` teaching agents which `agent_api` calls implement common overseer intents (elicit, save a MissionBrief, freeze, admit, smoke, scale, measure, decide, canary). Package-local copies may be shipped into the operator image. Skills are documentation loaded by operators/agents—not a second runtime and not a substitute for enforced `govern` checks.

The canonical `elicit` skill defines the required brief outline and question/research handoff, but deliberately does not prescribe one fixed decision tree. The operator chooses follow-ups and research depth; `save_mission_brief` and `freeze_objective` enforce completeness and provenance.

### 7.17 Recipes

**Job:** preserve and reuse proven ways to create named effects without rediscovering their ingredients, tradeoffs, or proof plan.

Recipes are not skills. A skill teaches the operator **how to use facktry**; a recipe specifies **how to create an effect in the model stack**. A recipe may be discovered by research, but research output is only a `RecipeProposal` until curated and reviewed.

Requirements:

- Load canonical `docs/recipes/<recipe-id>/RECIPE.md` files into a versioned, content-hashed catalog; `_template/RECIPE.md` is authoring guidance, not a recipe.
- Require structured front matter and sections for effect, mechanism, data/training/interface/serving ingredients, procedure, compatibility, tradeoffs, validation, evidence, provenance, and `## Recipe Notes`.
- Permit ingredients across data, weights, prompts, tool schemas, decoding, guards, and evaluation. Every ingredient must lower to existing governed operations; a recipe is not a second workflow engine.
- Expose `list_recipes`, `show_recipe`, `recommend_recipes`, and `compose_recipe_stack`. `recommend_recipes` ranks candidates from the target effect, Objective constraints, open defects, recipe notes, and prior outcomes; it is a read-only proposal. Composition resolves exact versions, ordering, overrides, mixture allocation, conflicts, and validation suites into an immutable `RecipeStack`.
- Validate recipe applicability and stack constraints against the frozen Objective, budget, interface pins, and domain pack. A stack may add proposed checks but may not remove or weaken Objective hard gates.
- Record the exact stack hash on every affected run, `TrainCard`, candidate `ReleaseTuple`, scorecard/Decision dossier, and yielded release.
- Encourage recipe retrieval before an intervention, during training/correction planning, and after human-inbox answers change the target or tradeoffs. Append a structured use note after the run has evidence, including failures and non-promotions.
- Require ordinary admit → smoke → scale → paired sealed measure → decide flow. A recipe's claimed effect is not evidence until measured against pinned baselines.
- Keep `## Recipe Notes` append-only. Each note records subsequent-use context, adaptation, observed effect, regressions, evidence refs, recommendation, and confidence. Notes inform future planning but cannot satisfy gates alone.
- Treat instruction changes as new recipe versions. Appending notes must not silently alter the operational meaning of the referenced recipe version.
- Reject secrets, raw private examples, and identifying data in recipe text or notes.

---

## 8. Control loop (normative)

Every experiment or objective run, including a data-only investigation, is preceded by a saved MissionBrief. Before an Objective is frozen, the operator completes the pre-loop elicitation below. Skipping it is a bug.

0. **`elicit`** — adaptive questions, research, and recipe retrieval between or during volleys; individual human approval of every proposed hard gate; save one complete immutable `MissionBrief` version at the end.
0.5. **`compose_recipe_stack` (optional)** — after the brief exists and before freeze when the mission calls for a known effect; resolve recipe compatibility, surface material tradeoffs, and include the stack policy or pin in the Objective.

After an objective is frozen, each autonomous iteration follows this order:

1. **`govern.preflight`** — including GPU exclusivity and disk/path checks.  
2. **`pin_suites`** — sealed (and dev) content hashes frozen for this iteration before new train corpus generation.  
3. **Plan** — agent reads open defects, last decision, and relevant recipe recommendations/notes (facktry provides retrieval; planning reasoning is the agent’s).
4. **Data path** — construct/validate → generate or harvest → deterministic filter → label/stratify/mix as required → **`admit` after every persist** → `AdmissionReport`.  
5. **`train_smoke`** — parent base/ancestor; mini sealed probe callbacks; smoke `Decision`; retrieve relevant recipe notes when interpreting early metrics or choosing a correction.
6. **`train_scale`** — only if smoke Decision allows and govern passes; keep best gated checkpoint; recipe-guided adjustments remain new, governed runs.
7. **`select_checkpoint`** — hard-constrained winner → candidate `ReleaseTuple`.  
8. **`measure` / `compare`** — sealed + dev; base/ancestor/candidate/wrapper; raw and guarded; multi-turn if dialogue.  
9. **`decide`** — dossier written.  
10. **Branch:**  
    - `correct` → retrieve relevant recipes and prior use notes; record/update defects; **new runs only**; mutate data/rubric/hparams/interface under policy; no ancestor overwrite; no specialist self-distill by default. Append the outcome to each used recipe after evidence exists.
    - `ask_human` → inbox items; agent waits or works elsewhere per policy; human answers via CLI; ingest; resume. Reconsider recipe selection when the human clarifies the target, tradeoff, or hard gate; record the resulting use context.
    - `hold` / `abort` → dossier; stop mutation.  
    - `promote` → human final when `human_promote` (default true); `yield_release` pins tuple; optional canary.  
11. **Yield** — pinned tuple + dossier + non-sensitive lesson export only. Include the exact `RecipeStack` hash when a recipe was applied.

**Data-only objectives** still require a saved MissionBrief and frozen Objective, then skip train/select/serve but still pin suites, admit, measure, decide.

**Finetune shape:**

```text
prompts/scenarios → trajectories → labels/strata → admitted mixture
  → smoke train → scale train → select → paired sealed measure
  → Decision → pinned ReleaseTuple
```

---

## 9. Gate catalog (normative minimum)

Objectives may add gates. They may not remove the hard floors below when the corresponding feature is in use.

### 9.0 Mission / objective (hard)

- Every objective and experiment, including data investigations, references a complete saved MissionBrief version/hash.
- Any applied `RecipeStack` references existing, hash-verified recipe versions and satisfies the Objective's recipe policy; a stack cannot weaken an Objective hard gate.
- Universal brief sections and any domain-pack-required sections are complete.
- Every proposed hard gate has individual human approval recorded before freeze.
- Research notes are proposal evidence and do not satisfy measured gates.
- `freeze_objective` refuses a missing, incomplete, or mismatched brief.

### 9.1 Admit (hard)

- Schema/role structure valid at construction and post-filter  
- Dependence-key disjointness train/eval/seal  
- Attribution integrity  
- Controlled vocab compliance when declared  
- Reject-reason histogram present; coverage floors when synth  
- Keep-rate and min-N bounds when configured  
- Teacher identity base/ancestor unless waived  
- No raw private bytes in artifacts  
- Sealed suite already frozen for this iteration  

### 9.2 Train (hard)

- Passing `AdmissionReport` hash in inputs  
- Smoke Decision allows scale before scale  
- No unresolved nonfinite/collapse  
- Interface hashes match objective pins  
- `TrainCard` complete including repeat exposure  
- Checkpoints hashed; parent ancestor hash-unchanged  

### 9.3 Model measure (hard)

- Sealed task/action floors  
- Unsupported-claim / hallucinated-state ceilings  
- Retention/OOD no-worse-than margins vs base/ancestor  
- Privacy/canary zero-tolerance when configured  
- Tool honesty / unsupported-action floors when tools in scope  
- `compat_check` train↔eval↔serve  
- Multi-turn suites run for dialogue objectives  
- Preference runs still pass non-preference hard suites  
- Raw and guarded both reported  

### 9.4 Soft (examples)

Preference margin/accuracy; style/diversity; calibrated judge scores; length vs target shape; abstention quality; robustness cells.

### 9.5 Human

Research fit; taste; borderline adjudication; recipe curation and material tradeoffs; final promote.

### 9.6 Diagnostic only (never sole promote/select basis)

Train CE; val CE alone; uncalibrated judge averages; unconditional distributional drift meters without task linkage.

---

## 10. Human loop

- Before freeze, `elicit` uses structured questions and research between volleys to assemble the MissionBrief. The operator may retrieve recipe candidates when they clarify the desired effect or tradeoff.
- During human-interactive reasoning, the operator should use the human's answers to refine recipe retrieval and stack composition rather than silently inventing a new intervention.
- Human approval of proposed hard gates is collected individually during elicitation; it is not a measured gate result or a replacement for the inbox.  
- `save_mission_brief` persists the complete dossier once at the end of elicitation; freeze requires its version/hash.  
- Inbox items reference objective, gate, blinded payload, response schema.  
- Ingest validates schema; writes gold fixtures or waivers with reviewer identity + timestamp.  
- Default `human_promote=true` for model deliverables.  
- Live CLI shows inbox pressure always; `facktry inbox` is for working the queue.  
- Agents may not mark human gates passed without an ingested response artifact.
- After a governed attempt, the operator appends a structured recipe-use note for each applied recipe, including measured outcome or failure evidence; notes do not themselves pass gates.

---

## 11. Provenance

Every run records at minimum:

- code/source hash  
- input artifact hashes + source-class breakdown  
- env freeze (offline/local assets when privacy or repro requires)  
- hardware snapshot  
- output artifact hashes  
- parent runs  
- objective id + linked MissionBrief version/hash + suite hashes used in any Decision
- applied `RecipeStack` ref/hash, recipe-specific adaptations, and any recipe-note refs used for planning
- transformation policy + seeds for data jobs
- teacher/reference identities for synth and preference  

Decisions cite evidence by artifact hash. **If it is not hashed, it did not happen.**

Privacy: aggregates, hashes, policy descriptions on disk—never raw private examples in artifacts, logs, preference files, or remote requests. Exported lessons are durable and non-sensitive.

---

## 12. Out of scope (do not build into core)

These are excluded from core until a Decision dossier on a real objective proves they must be harness-native. Exclusion means “not required in core,” not “ship a broken half-substitute.”

- Full red-team product integration as a default dependency  
- Multi-judge panels as a mandatory path (single calibrated judge + deterministic oracles is the design)  
- Hyperparameter study platforms (Optuna-style) as a core subsystem  
- Remote orchestrator (Vast/Flyte) inside core—may later be a backend behind `train`/`govern` without API break  
- Per-domain dashboard JSON authoring as a prerequisite to monitoring  
- CLI as the primary author of multi-stage science (agent_api is)  
- Automatic production flip without policy + human when `human_promote` is true  

---

## 13. Engineering standards for implementers

This section exists because the implementing agent will not have the design conversation. Follow it.

### 13.1 Completeness

Implement the module contracts in §7 as real fail-closed behavior, not facades that log “TODO.” A function named `train_scale` that does not call `govern.smoke_then_scale` is a defect. A `Decision` that ignores hard gates is a defect. A sealed suite that returns case text to the planner is a defect.

Do not land a parallel “simple mode” that bypasses admit, smoke, or measure. Do not ship stub gates that always pass.

### 13.2 Recommended build order (integration order, not reduced scope)

Build in dependency order so each slice is **fully correct** for the contracts it claims:

1. `store`, types, hashing, workspace discovery  
2. `elicit`/MissionBrief save + `objective` freeze/lint + `govern.preflight` + `govern.policy/budget` skeletons wired for real denial  
3. `admit` + `AdmissionReport` + attribution/leakage tests  
4. `verify` core oracles + `suite` registry/runner/`compare` + sealed custody boundary  
5. `decide` aggregation + dossier + defects  
6. `agent_api` complete surface on top of the above  
7. `watch` CLI auto-focus + status + show + ls (wired to real store)  
8. `train` SFT + callbacks + `TrainCard` + `select` + smoke/scale govern  
9. preference path obeying §7.8 contract  
10. `play` + `World` + judge calibration  
11. `serve` + canary + rollback  
12. domain pack registration when a real objective exists  

“Order” means dependency layering. It does not mean shipping lasting public APIs that omit govern checks.

### 13.3 Testing (mandatory categories)

Automated tests must cover:

- admit leakage at dependence keys  
- attribution/hidden-context rejection  
- role/structure construction failure before generate  
- claim≠execute and unsupported-action oracles  
- smoke_then_scale denial without passing smoke  
- scale denial on admission hash mismatch  
- select does not pick last step when hard probes prefer earlier  
- decide refuses promote on any hard fail  
- decide routes human gates to `ask_human`  
- sealed runner does not expose case text via planner-facing API  
- suite pin required before admit-for-train  
- preference pairs rejected if inputs differ  
- preference train still fails decide when task hard gates drop  
- compat_check catches template/tokenizer drift  
- CLI auto-focus ordering and empty state  
- rollback restores previous pinned tuple  
- private raw bytes refused on artifact write paths  
- MissionBrief save creates immutable versions and preserves question history, success case, one-line research notes, and references  
- freeze and every experiment path refuse a missing, incomplete, or mismatched MissionBrief  
- individual hard-gate approvals are required before freeze  
- MissionBrief/Objective/run lineage is visible through `show` and shared CLI/agent queries  

### 13.4 Code quality

- Typed public surfaces; explicit error types for govern denials.  
- Deterministic hashing (stable canonical JSON where relevant).  
- No secret values in manifests or logs.  
- Metrics append-only; safe for concurrent tail.  
- Concurrency: document process model; do not corrupt sqlite/manifests on concurrent agent + CLI read.  
- Package install provides `facktry` console entrypoint.

### 13.5 Independence

- No runtime dependency on prior experiment implementations or registries.  
- No hardcoded voice, SMS, or host GPU index policy in core.  
- No dependency on this chat transcript—only this ADR, `IMPLEMENTATION_CHECKLIST.md`, `docs/skills/`, `docs/recipes/`, and the repo.

### 13.6 Progress file discipline

- Treat `IMPLEMENTATION_CHECKLIST.md` as durable memory across sessions and context compactions.  
- Mark items `[~]` when started, `[x]` when behavior matches this ADR and required tests pass, `[-]` only with a written waiver reason.  
- Refresh the Progress summary table on every checklist edit.  
- Do not delete checklist rows to hide unfinished work.

---

## 14. Success criteria

Facktry is complete for its stated purpose when all of the following hold:

1. An overseer can express a mission; an agent can elicit and save a hashed `MissionBrief`, then freeze a hashed `Objective` with gates, budget, baselines, and suites.
2. The agent can iterate data and training under budget without per-step human ops.  
3. Hard gates are machine-enforced; soft gates cannot promote alone; diagnostic metrics cannot select.  
4. Sealed measure is blind to the planner; paired compares include base/ancestor/candidate as applicable.  
5. The system stops for human-only judgments via inbox; CLI surfaces pressure.  
6. A successful model objective yields a pinned `ReleaseTuple` + dossier with reproducible hashed evidence.
7. A human typing only `facktry` during active work sees objective, loop phase, active run, failing gates, defects, and inbox without passing run ids or registry paths.
8. Curated recipes can be discovered, composed into a hashed `RecipeStack`, evaluated through the normal governed loop, and extended with append-only subsequent-use notes.
9. Ancestor weights and prior pins remain hash-unchanged after corrective trains.
10. The test categories in §13.3 pass.
11. Every objective and experiment, including data investigations, can be traced back to the immutable MissionBrief version containing the user’s intent, success case, research pointers, and hard-gate approvals.

---

## 15. Consequences

**Positive:** Closed autonomy loop; objective measurement; model-out as first-class product; agent-native mutation; human-native monitor; compounding recipe memory that makes intervention selection improve over time; domain extensibility without core rot; private-data discipline; anti-self-distillation defaults.

**Negative:** Sealed custody, interface locking, and fail-closed govern add real implementation work. Agents cannot “just train.” Humans must freeze gates carefully or the loop will correctly optimize the wrong contract. Monitor layout is opinionated.

**Neutral:** Smaller conceptual surface than a general ML platform. CLI is for watching and narrow response, not for rebuilding a stage-taxonomy cockpit.

---

## 16. Appendix A — Operator intent → modules

| Operator intent | Modules |
|---|---|
| Understand and specify mission | `elicit`, `questions`, `research`, `recommend_recipes`, `save_mission_brief` |
| Freeze mission | `objective`, `govern` |
| Harvest/filter/stratify data | domain stages, `admit`, `play` |
| Words in, model out | `train`, `select`, `suite.compare`, `decide`, `serve` |
| Unsupervised iteration under budget | `govern` budget, `decide` loop, `store` defects |
| Human evals that cannot be automated | `decide` → inbox; `watch` inbox |
| “What is it doing?” | `watch` via bare `facktry` |
| Anti self-distillation | `train` parent pins, `admit` teacher pins |
| Reuse a proven behavioral effect | Curated `Recipe`, `recommend_recipes`, `RecipeStack`, governed application, paired measure, append-only recipe notes |
| Compound model-development knowledge | Recipe retrieval during planning/correction/human reasoning; measured outcomes feed later recommendations |
| Hidden-context / grounding | `admit` attribution, `verify` oracles |
| Privacy-safe artifacts | `store`/`admit` source classes |
| Pref style without tanking facts | preference contract + full re-measure |
| Schema botch before GPU burn | construction-time checks in `generate_and_admit` |
| Final yield | `yield_release` + dossier artifacts |

---

## 17. Appendix B — Engineering invariants → enforcement

| Invariant | Enforcement |
|---|---|
| Intent provenance | `elicit` + `save_mission_brief`; Objective and every experiment cite the immutable brief version |
| Success ≠ min val loss | `select` + `decide` hard gates; loss diagnostic |
| Evidence-only answers | Attribution admit + verify oracles |
| Abstain when unknown | Suite dimensions + verify detectors; natural targets |
| Retain OOD capability | Replay mixture + retention probes in `compare` |
| Consistency across decode/prompt | Pinned decode; robustness cells; `compat_check` |
| No consequential fabrication | Claim≠execute; unsupported-action; sealed floors |
| Self-distillation collapse | Teacher/parent defaults; new run dirs |
| Split leakage | Dependence-key admit |
| Metrics must filter | Diagnostic severity ignored for select/promote |
| Interface entanglement | `ReleaseTuple` + `compat_check` |
| Over-specialization | `TargetShape` + replay quotas |
| Safety–style conflation | Guards in verify/serve; short safety prompt text |
| Private data hygiene | No raw private artifacts |
| Synth is coverage | `generate_and_admit` + sealed measure |
| Pref pair discipline | §7.8 contract |
| Freeze eval before data | Control loop step 2 |
| Raw vs guarded | Scorecard channels + serve logging |
| Trajectory validation | `play` + `verify` + `judge` + `suite` |
| Ops preflight / GPU exclusion | `govern.preflight` |
| Multi-turn matters | Suite + play requirements for dialogue |

---

## 18. Closing rule

When uncertain, preserve **fail-closed gates** and the **control loop**. Do not start an experiment without a saved MissionBrief. Do not add modules that do not change a `Decision`. Do not remove gates to make a demo green. Do not re-litigate invariants in Appendix B—implement them.

This ADR is the implementation reference. Build facktry to it.
