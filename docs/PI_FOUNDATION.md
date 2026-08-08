# Facktry Operator Runtime — Pi Session Image Foundation

| Field | Value |
|---|---|
| **Status** | Design accepted — not yet implemented |
| **Date** | 2026-08-06 |
| **Authority** | Companion to `ADR.md`. This document defines the **operator runtime** that hosts the facktry agent. It does not replace the harness contracts in the ADR. |
| **Relationship to ADR** | ADR §3 (`agent_api` + skills) and §7.13–7.17 assume an LLM operator. This document specifies **how that operator is hosted**: a reformed Pi session image launched by `facktry run`, isolated from a normal `pi` coding session. |
| **Relationship to checklist** | Implementation of this foundation is a **prerequisite track** that may start before harness modules land. It must not invent a reduced harness or bypass future `govern` checks. When `agent_api` exists, tools here become thin façades over it. |
| **Operator tools track** | [`tools_implementation_steps/`](tools_implementation_steps/) — phased tool work for the session image (e.g. `questions`). Separate from harness `codebase_implementation_steps/`. |
| **Operator recipes** | [`recipes/`](recipes/) — curated, versioned effect recipes and append-only subsequent-use notes. |
| **Audience** | Implementation agents and human overseers |
| **Code location (target)** | `/home/admin/facktry` (product). Design and pre-actualization notes may live under `/home/admin/facktry` until the facktry tree is the working root. |

---

## 1. Purpose

Facktry’s product has two operator surfaces (ADR §3):

| Surface | Who | Job |
|---|---|---|
| **`agent_api` + skills** | LLM agent | Mutate under policy: freeze, admit, train, measure, decide |
| **`facktry` CLI (`watch`)** | Human | Live truth, inbox, narrow acknowledgements |

This document covers a third, infrastructural piece that the ADR implies but does not specify:

The operator needs a facktry-shaped host process for models, tools, session memory, sub-agents, and prompts—not a generic coding agent configured for facktry.

**Foundation goal:** before, or in parallel with, the early harness modules, ship a **Pi session image** and launcher:

```text
facktry run
  → Pi-based interactive (or headless) session
  → facktry system prompt + facktry tool allowlist + facktry subagents
  → no facktry prompts, tools, agents, extensions, or sessions enter a normal `pi` invocation
```

The image supports research, ADR planning, and scaffolding before harness mutations exist; later modules add governed mutation tools without changing the launch path. Pipeline activity requires adaptive elicitation and a saved `MissionBrief` before freeze or experimentation.

---

## 2. Pi integration boundary

### 2.1 Use Pi

Pi already provides, without fork:

- Agent loop, streaming, sessions (JSONL tree), compaction, model routing  
- Extension API: `registerTool`, `setActiveTools`, lifecycle hooks, commands  
- SDK: `createAgentSession`, custom `ResourceLoader`, `customTools`, tool allowlists  
- Sub-agent pattern (official example): isolated child session/process, summary return  
- Packages: bundle extensions, skills, prompts without global install  
- TUI and headless/RPC modes  

### 2.2 Build an application, do not fork

Facktry ships an **image** on top of Pi:

- Replace system prompt  
- Replace / subset tools  
- Register facktry tools and research subagent  
- Own session directory and settings for the facktry launcher  
- Never require the user to configure `~/.pi/agent` for facktry to work  

### 2.3 Do not put harness law only in prompts

Pi is the **operator host**. Fail-closed training law lives in facktry Python modules (`govern`, `admit`, `decide`, …). Prompts teach the agent *when* to call tools; tools enforce *whether* the call is legal. A clever prompt is not a substitute for `AdmissionReport` or smoke-then-scale.

---

## 3. Doctrine (operator runtime)

These are fail-closed laws for the **session image**. Violating them is a product bug even if the TUI looks fine.

1. **`facktry run` owns the image.** Ambient `pi` must not be required to load facktry extensions, prompts, or agents.
2. **Normal `pi` stays stock.** Facktry tools, subagents, and prompts must not install into `~/.pi/agent/` by default.
3. **Allowlist, do not hope.** Parent session tools are an explicit set. Built-in coding tools are disabled or narrowly gated unless the image deliberately enables them.
4. **Research is isolated.** Literature crawl runs in a child context; only a bounded summary re-enters the parent.
5. **Summaries are structured.** Research return shape is a contract (recipe table + refs + gaps), not free-form chat.
6. **Mutation is facktry-native.** Weight, data, and decision mutations go through facktry tools → (eventually) `agent_api` → `govern`. Direct shell training is not a blessed path.
7. **Harness incomplete ≠ harness bypass.** Until `agent_api` exists, mutation tools are absent or return explicit `not_implemented` / `harness_unavailable`. They must not fake success.
8. **Skills and recipes are documentation with contracts.** Skills teach call order; recipes specify how to create an effect. Neither replaces tool enforcement. Recipe instructions are versioned; recipe notes are append-only memory.
9. **One launcher, two modes.** Interactive operator chat and headless single-shot share the same image factory.
10. **Workspace is facktry’s.** Session files and operator state hang off the facktry workspace (`.facktry/` / `FACKTRY_HOME`), not the global Pi session pile, unless an explicit escape hatch says otherwise.
11. **Subagents are read-mostly by default.** Research workers do not get `train_*`, `yield_release`, or ungoverned filesystem write.
12. **Upstream Pi remains a dependency.** Pin a compatible `@earendil-works/pi-coding-agent` range; do not vendor a permanent hard fork. If Pi lacks a hook, prefer extension/SDK patterns; file upstream issues rather than maintaining a private Pi tree.
13. **MissionBrief before experiment.** The parent may use the `questions` and `research` primitives in an adaptive `elicit` session, but it must save a complete `MissionBrief` through the harness tool before `freeze_objective` or any experiment path. The Pi session is allowed to hold the working draft until the end of elicitation; it must not claim the brief exists before the save succeeds.

---

## 4. Non-goals (this foundation)

- Implementing ADR harness modules (`store`, `admit`, `train`, …) — separate track  
- Becoming a general multi-agent coding product  
- Multi-user SaaS hosting of the operator  
- Replacing `facktry watch` human CLI with the Pi TUI  
- Global installation of facktry as the user’s default Pi config  
- Parity with every ML Intern feature (HF Jobs UI, web frontend, billing, etc.)
- Sealed-suite custody inside the research subagent (sealed eval is harness `suite`, not research)  

---

## 5. Architecture

### 5.1 Processes and packages

```text
┌─────────────────────────────────────────────────────────────┐
│  facktry (Python package)                                      │
│  store · elicit · objective · admit · govern · train · agent_api │
│  CLI: facktry, facktry watch, facktry status, …                      │
└──────────────────────────▲──────────────────────────────────┘
                           │ subprocess / RPC / library bridge
┌──────────────────────────┴──────────────────────────────────┐
│  facktry-pi (Node / TypeScript package)                        │
│  bin: facktry-run  (also exposed as: facktry run)                 │
│                                                             │
│  createAgentSession({                                       │
│    resourceLoader: FacktryResourceLoader,  // no ambient ~/.pi │
│    tools / customTools: parent allowlist,                   │
│    sessionManager: under .facktry/operator-sessions/,          │
│    modelRuntime: host auth (shared or facktry-scoped),         │
│  })                                                         │
│                                                             │
│  extensions:                                                │
│    · parent tools (questions, research, later agent_api)    │
│    · research subagent spawner                              │
│    · optional policy hooks (block raw destructive bash)     │
│  prompts: SYSTEM.md (operator)                              │
│  agents: research.md (and future specialists)               │
│  skills: elicit / freeze / admit / smoke / … (aligned with ADR) │
│  recipes: curated effect specifications + notes                │
└─────────────────────────────────────────────────────────────┘
                           │
           normal `pi` ────┘  does NOT load facktry-pi
```

### 5.2 Dual entrypoints, one image

| Command | Role |
|---|---|
| `facktry run` | Primary. Python CLI dispatches to `facktry-run` (Node) or a single binary wrapper. Builds the facktry image and starts interactive Pi TUI **or** headless prompt. |
| `facktry-run` | Node executable used directly in dev. Same image factory. |
| `facktry watch` / bare `facktry` | Human monitor (ADR §7.14). **Not** the operator agent. Must remain a separate surface. |
| `pi` | Unmodified coding agent. No facktry tools. |

**Dispatch rule:** `facktry run` is part of the facktry CLI taxonomy so humans learn one family of commands. Implementation may be a thin Python wrapper around the Node launcher.

### 5.3 Image factory (normative concept)

All launch paths call one factory, conceptually:

```text
createFacktryOperatorSession(options) -> {
  session,       // AgentSession
  runtime?,      // AgentSessionRuntime if multi-session replace needed
  dispose(),
  meta: { workspace, imageVersion, toolNames, agentNames }
}
```

**Factory responsibilities:**

1. Resolve facktry workspace (`FACKTRY_HOME` / `.facktry/` walk / create policy consistent with ADR store discovery).  
2. Construct a **closed** `ResourceLoader` (or `DefaultResourceLoader` with overrides that **disable ambient discovery** of user global extensions/agents that would pollute the image).  
3. Set **system prompt** to facktry operator prompt (full replace, not append-on-global).  
4. Clear or ignore user `APPEND_SYSTEM.md` from `~/.pi` unless `FACKTRY_PI_INHERIT_USER_APPEND=1` (default off).  
5. Register parent tools; set active tool allowlist.  
6. Discover **only** facktry-shipped subagent definitions (package-local `agents/`), not `~/.pi/agent/agents`, unless explicitly opted in.  
7. Place sessions under `{workspace}/operator-sessions/` (JSONL).  
8. Use settings suitable for long operator work (compaction on; facktry-specific defaults).  
9. Record `image_version` (package version + prompt hash + tool schema hash) into session metadata for repro.

**Reference SDK patterns (upstream examples, not to copy blindly):**

- `examples/sdk/12-full-control.ts` — empty/custom loader, explicit tools  
- `examples/sdk/03-custom-prompt.ts` — `systemPromptOverride` + empty append  
- `examples/sdk/05-tools.ts` — tool allowlists / `noTools`  
- `examples/extensions/subagent/` — isolated child agents + summary return  

### 5.4 Isolation matrix (normative)

| Resource | `facktry run` | Normal `pi` |
|---|---|---|
| System prompt | Facktry operator | Pi default / user |
| Parent tools | Facktry allowlist only | Pi builtins ± user ext |
| Research / facktry subagents | Yes (package agents) | No |
| `agent_api` tools | Yes when harness exists | No |
| Reads `~/.pi/agent/extensions` | **No** (default) | Yes |
| Installs into `~/.pi/agent` | **Never** by default | N/A |
| Session files | `.facktry/operator-sessions/` | `~/.pi/agent/sessions/` |
| Skills | Facktry package skills | User/project skills |

**Forbidden default behaviors:**

- `pi install` of facktry package into user settings as part of `facktry` setup docs without stating the isolation cost  
- Symlinking facktry agents into `~/.pi/agent/agents` in install scripts  
- Documenting “add this to your global extensions” as the primary UX  

**Allowed escape hatches (explicit and documented):**

- `FACKTRY_PI_EXTRA_EXTENSIONS` — additional extensions for development; off by default
- `FACKTRY_PI_ALLOW_USER_AGENTS=1` — merge user agents; off by default and discouraged

`FACKTRY_PI_INHERIT_USER_AUTH=1` is enabled by default to share host auth/model paths. Shared auth does not load user extensions or agents. Prefer `ModelRuntime` with explicit paths.

---

## 6. Session image contents

### 6.1 Parent identity — operator system prompt

**File (shipped):** `facktry-pi/prompts/SYSTEM.md` (name flexible; content is normative).

The parent agent is **Facktry Operator**, not “a coding assistant,” not ML Intern, not the base model vendor.

**Prompt must establish:**

1. **Identity** — Facktry Operator for this workspace; do not claim to be Claude/ChatGPT/etc.  
2. **Surfaces** — You mutate via facktry tools; humans use `facktry watch`; you do not ask humans to type train CLIs.  
3. **Control loop awareness** — elicit → save MissionBrief → freeze objective → pin suites → admit → smoke → scale → select → measure → decide → promote/correct (ADR §8). Even before tools exist, plan in this order.  
4. **Research and recipe memory** — for ML method/recipe choices, call `research` when evidence is missing and retrieve relevant curated recipes, notes, defects, and prior outcomes before inventing an intervention. Revisit recipes during training/correction planning and after human answers change the target or tradeoffs.
5. **Fail-closed stance** — if a tool denies or harness is missing, report blocker; do not pretend gates passed.  
6. **Privacy** — no raw private data in artifacts, logs, or research exports.  
7. **No self-distill / no ancestor overwrite** — restate ADR doctrine at operator level.  
8. **Tool schema is truth** — only call available tools; never simulate tool results in prose.  
9. **Harness growth** — tools appear as modules land; use `facktry_status` / `list_tools` semantics to see what is live.  
10. **Intent before invention** — for every pipeline activity, use the `elicit` skill to understand the human’s intent, ask adaptive structured questions, research between question volleys when useful, obtain individual approval of proposed hard gates, and save the complete MissionBrief before freezing or experimenting. Do not invent missing domain requirements silently.

**Prompt must not:**

- Embed host-specific GPU indices, customer data, or secrets  
- Duplicate the entire ADR (point at workspace `ADR.md` / skills; keep prompt operational)  
- Enable “creative scope change” under OOM (align with research discipline: minimal fix or ask human)  

**Prompt versioning:** content hash recorded in image metadata. Changes to SYSTEM.md bump operator behavior; sessions may continue with old prompt until new session.

### 6.2 Parent tool surface (phased)

Tools are registered in the image from day one as a **stable vocabulary**. Implementations deepen over time.

#### 6.2.1 Phase F0 — foundation (no harness required)

| Tool | Role | Mutation? |
|---|---|---|
| `questions` | Structured human Q&A with multiple choice and optional detail | No |
| `research` | Spawn isolated research subagent; return recipe summary | No (read-only worker) |
| `facktry_workspace` | Show resolved workspace root, image version, session id | No |
| `facktry_help` | Summarize available tools + skill and recipe names + loop diagram | No |
| `read_doc` | Read facktry design docs (ADR, this file, skills, recipes) with path allowlist | No |
| `list_recipes` / `show_recipe` | Discover curated effect recipes and append-only notes | No |
| `recommend_recipes` | Rank relevant recipes for a target effect and current objective context | No |
| Optional narrow `read` | Read within workspace allowlist | No |
| Optional narrow `bash` | **Off by default** in F0; if enabled for dev, extension `tool_call` hook blocks obvious destructive patterns and records audit | Dangerous; prefer off |

**Not in F0 parent allowlist:** `write`, `edit`, unrestricted `bash`, Pi default coding quartet as a set.

**Rationale:** foundation proves image isolation + research pipeline without turning facktry into an unsupervised repo coder. Dev iterations on facktry itself may use a **dev profile** (`facktry run --profile dev`) that adds `read`/`edit`/`write`/`bash` for working on the facktry codebase — still not installed into global `pi`.

#### 6.2.2 Phase F1 — read-only harness façade

When `store` + partial APIs exist:

| Tool | Maps toward |
|---|---|
| `show_objective` / `list_runs` / `list_decisions` | `agent_api` query_* |
| `inbox_list` | inbox read |
| `defects_list` | defects read |
| `facktry_status_snapshot` | same data `facktry status` uses |
| `recommend_recipes` | rank effect recipes using objective, defects, notes, and prior outcomes; no mutation |
| `compose_recipe_stack` | validate and hash a compatible recipe composition; no mutation |

Still no train/admit.

#### 6.2.3 Phase F2 — full operator (ADR complete path)

Tools mirror ADR §7.13 capabilities (names may match `agent_api` 1:1):

`save_mission_brief`, `show_mission_brief`, `list_mission_briefs`, `freeze_objective`, `pin_suites`, `list_recipes`, `show_recipe`, `recommend_recipes`, `compose_recipe_stack`, `admit`, `generate_and_admit`, `train_smoke`, `train_scale`, `select_checkpoint`, `measure`, `compare`, `decide`, `append_recipe_note`, `yield_release`, `inbox_ingest` (usually human), defect close, etc.

Each tool:

- Validates params  
- Invokes Python `agent_api` (subprocess or local RPC)  
- Returns structured JSON text to the model  
- Surfaces `GovernDenial` as structured failure, not stack trace spam  

### 6.3 Active tool management

Use Pi `setActiveTools` when profiles or loop phases need different sets:

| Profile | Active tools (conceptual) |
|---|---|
| `operator` (default) | questions + research + facktry query/mutate as available |
| `research_only` | research + read_doc + workspace |
| `dev` | operator + coding builtins for facktry repo work |

Do not use dynamic tool loading as a substitute for govern. Phase of the **mission** is enforced by harness; phase of the **UI tool set** is UX.

### 6.4 Skills (markdown playbooks)

Author the canonical set under `docs/skills/` as referenced by the ADR. Ship package-local copies under `facktry-pi/skills/` and/or facktry Python resources; copies are operator-facing mirrors or thin wrappers and must not drift.

Minimum skill topics (aligned with ADR §7.16):

- elicit and save MissionBrief  
- freeze objective  
- pin suites and select/compose `RecipeStack`s
- admit / generate_and_admit  
- smoke then scale  
- measure / decide  
- human inbox  
- promote / canary  

Skills describe **tool call sequences**. They must be updated when tool names stabilize.

The `elicit` skill is an adaptive outline, not a fixed questionnaire: it requires the universal brief sections and any domain-pack sections, but lets the session choose follow-ups and research depth. It uses `questions` for human volleys, `research` and recipe retrieval between or during volleys as useful, asks the human to approve each proposed hard gate individually, records recipe considerations and tradeoffs, and calls `save_mission_brief` once at the end. A failed save blocks `freeze_objective` and every experiment path.

### 6.5 Recipes (effect specifications)

Recipes are not an alternate skill format. The canonical source is `docs/recipes/<recipe-id>/RECIPE.md`. The Pi image exposes read-only discovery and recommendation; composition delegates to the Python harness. `recommend_recipes` and `compose_recipe_stack` return proposals/stacks, while applications remain subject to the ordinary governed path.

Recipe retrieval is encouraged during planning, training correction, and human-inbox reasoning. `## Recipe Notes` is append-only: append a structured outcome after each governed use, including failures and non-promotions, without changing the instruction hash. The loader must keep instruction content and notes distinguishable for reproducibility.

### 6.6 Slash commands (extension commands)

| Command | Behavior |
|---|---|
| `/facktry-workspace` | Print workspace + image version |
| `/facktry-tools` | List active vs registered tools |
| `/facktry-loop` | Show control loop + current known harness phase (once store exists) |
| `/research <task>` | Optional sugar: inject a user message that forces a research call |

Commands are human UX sugar; the model still uses tools.

---

## 7. Research subagent (normative design)

This is the native lift of the ML Intern **literature → recipe → code patterns** flow, implemented as a Pi subagent — not a dependency on `ml-intern`.

### 7.1 Role

```text
Parent (Facktry Operator)
  │  research({ task, context })
  ▼
Research worker (isolated session)
  │  papers → citation graph → methodology sections
  │  → result↔recipe attribution
  │  → dataset validation hooks
  │  → current code/docs patterns
  ▼
Bounded structured summary only → parent context
```

### 7.2 Isolation mechanics

**Preferred implementation order:**

1. **In-process nested `createAgentSession`** with:
   - independent `SessionManager.inMemory()` (or separate JSONL under `operator-sessions/research/`)  
   - research system prompt override  
   - research tool allowlist only  
   - no parent message history  
   - abort signal linked to parent tool cancellation  
2. **Fallback:** child `pi --mode json` process with explicit cwd, prompt flags, and extension path — mirrors upstream subagent example; use if nested session proves brittle.

**Do not** run research in the parent context with raw paper dumps (context pollution).

### 7.3 Research tool allowlist

| Tool | Purpose |
|---|---|
| `papers` (or `hf_papers` equivalent) | search, paper_details, citation_graph, read_paper (TOC/section), snippet_search, recommend, find_datasets / find_all_resources |
| `web_search` | when papers/docs insufficient; optional domain allow/deny |
| `docs_search` / `docs_fetch` | up-to-date library docs (HF stack and general as needed) |
| `github_examples` / `github_read` | working code patterns |
| `hub_inspect_dataset` | schema/split/sample validation |
| `hub_repo_files` | model/dataset repo inspection |
| Narrow `read` | only if worker must read local allowlisted notes |
| `bash` | **default off**; enable only for controlled fetch tooling if required by paper HTML fetch implementation |

**Never on research worker:** `train_*`, `admit`, `yield_release`, `write`/`edit` to workspace, promote, unrestricted shell.

### 7.4 Research system prompt — crawl doctrine

Ship as the canonical `facktry-pi/agents/research.md` worker definition (frontmatter: name, description, tools, optional model). Content doctrine (normative):

1. **Start from literature**, not from documentation or unverified assumptions.
2. **Anchor papers** — search; prefer high citation and/or recent strong results.  
3. **Downstream citation graph** — papers that *cite* the anchor (improvements/applications).  
4. **Read methodology/experiments** — TOC first, then sections (typically methods/experiments/results); not abstracts alone.  
5. **Attribute result ↔ recipe** — atomic unit:  
   `dataset + method + key hparams → metric on benchmark`.  
   “They used SFT” is insufficient.  
6. **Validate datasets** — Hub (or declared source) existence + format fitness for method.  
7. **Code last** — examples + current docs for implementable patterns.  
8. **Go deeper** when anchors are old or a downstream result dominates — crawl that paper’s graph; use snippet search for cross-paper claims.  

### 7.5 Research output contract

Worker final message **must** follow this structure:

```markdown
## Recipe table
For each candidate (ranked by result quality / feasibility notes):
- Paper: title | id | date | venue
- Result: metrics + benchmark
- Dataset(s): name | size | source | availability | format_verified
- Method: approach + key hparams
- What made it work: concrete insight

## Code patterns
- Real imports, paths, snippets (not paraphrase-only)

## Recommendations
- First recipe to try and why
- Datasets to use
- Gaps / adaptation needed

## SOTA landscape
- Brief; flag outdated common knowledge

## Essential references
- URLs, file paths, arxiv ids
```

**Bounds:** target ~500–1500 words; truncate tool observations inside the worker (e.g. 8k chars per tool result) so the worker can finish.

**Parent obligation:** treat the summary as **proposal evidence**, not as a passed gate. Recipes do not skip admit, smoke, sealed measure, or decide. During elicitation, persist only a very brief one-line summary plus references/pointers in the MissionBrief; the full worker response need not be copied into that dossier and referenced sources may be fetched again later.

### 7.6 Research runtime limits

| Limit | Guidance |
|---|---|
| Max tool iterations | ~40–60 then force summary |
| Context warn / hard stop | warn ~75%, force summary near model limit |
| Doom-loop / repetition | detect repeated identical tool calls; inject wrap-up |
| Parallel research | allow multiple parent `research` calls; unique ids; do not share worker context |
| Model | default: parent model or cheaper explicit `research_model` setting |
| Cost | optional budget hook later; foundation at least logs tokens |

### 7.7 Papers tool substrate

Implement as facktry-owned tools (TypeScript and/or Python service called from TS):

| Operation | Backend ideas |
|---|---|
| `search` | Hugging Face papers API + Semantic Scholar |
| `paper_details` | HF + S2 metadata |
| `citation_graph` | S2 citations/references + influence flags |
| `read_paper` | arXiv/ar5iv HTML → section parse; TOC vs section |
| `snippet_search` | S2 snippets |
| `recommend` | S2 recommendations |
| `find_datasets` / `find_all_resources` | HF paper↔artifact links |

**Engineering notes:**

- Cache GETs on disk under `.facktry/cache/papers/` with TTLs  
- No API keys in logs  
- Graceful degradation when S2 rate-limits  
- Deterministic formatting into markdown for the worker  

This substrate is the hard part of “up-to-date research”; the prompt only orders its use.

### 7.8 Research proposal artifact

Parse research markdown (or ask worker for JSON mode) into a provisional `RecipeProposal` artifact in the facktry store when store exists:

- content hash
- parent session id / research run id
- structured recipes[]
- evidence and limitations

A proposal is not a curated recipe and cannot directly mutate an Objective. A human curator may add it to `docs/recipes/<recipe-id>/RECIPE.md`, preserving references and limitations.

### 7.9 Curated recipe and stack artifacts

When the store exists, parse curated `RECIPE.md` sources as `Recipe` artifacts with a stable instruction hash over front matter and instructional sections, distinct from separately hashed append-only notes. A full source snapshot may also be registered for audit. Notes can accumulate without changing the meaning of an old recipe version. `compose_recipe_stack` creates an immutable `RecipeStack` artifact containing exact recipe instruction refs, ordering, overrides, conflict decisions, ingredient allocation, and validation plan.

Every run, candidate tuple, scorecard/Decision dossier, and yielded release that uses a recipe records the stack hash. Research notes and recipe use notes are planning evidence; only ordinary measured gates can authorize a release.

---

## 8. Bridge: TypeScript operator ↔ Python harness

### 8.1 Principles

- **Single source of truth for mutations:** Python `agent_api`.  
- **TS tools are adapters:** schema for the LLM + process bridge + result formatting.  
- **No duplicated govern logic in TS.**  

### 8.2 Bridge options (choose in implementation; default below)

| Option | Pros | Cons |
|---|---|---|
| **A. `facktry api-call` CLI** — TS spawns `facktry internal invoke <op> --json` | Simple, debuggable, no daemon | Latency per call; cold start |
| **B. Long-running local RPC** — `facktry rpc` on unix socket under `.facktry/` | Fast multi-tool turns | Lifecycle/health complexity |
| **C. FFI / embedded Python** | Tight | Packaging pain |

**Default for foundation → F2:** **A** until call volume hurts, then **B** without changing tool names.

### 8.3 Invoke contract (conceptual JSON)

Request:

```json
{
  "op": "train_smoke",
  "params": { },
  "workspace": "/path/to/.facktry",
  "operator_session_id": "...",
  "image_version": "..."
}
```

Response:

```json
{
  "ok": true,
  "result": { },
  "artifact_refs": [],
  "error": null
}
```

or

```json
{
  "ok": false,
  "error": {
    "type": "GovernDenial",
    "code": "smoke_required",
    "message": "..."
  }
}
```

Foundation implements the invoke stub with `op=ping` / `op=workspace_info` only.

---

## 9. Workspace and on-disk layout

### 9.1 Facktry workspace additions

```text
{FACKTRY_HOME or .facktry}/
  operator-sessions/          # Pi JSONL sessions for facktry run
  operator-sessions/research/ # optional persisted research traces
  cache/papers/               # paper/doc HTTP cache
  cache/hub/                  # optional
  # ... existing/future harness paths: runs/, index, objectives, ...
```

### 9.2 Package layout (target repo)

```text
facktry/                         # Python harness (ADR)
  pyproject.toml
  src/facktry/ or facktry/
  skills/                     # package copy of canonical docs/skills/
  recipes/                    # loader/catalog copy of canonical docs/recipes/
  ...

facktry-pi/                      # Operator runtime (this document)
  package.json
  tsconfig.json
  src/
    bin/facktry-run.ts           # CLI entry
    session/createFacktrySession.ts
    loader/facktryResourceLoader.ts
    tools/
      research.ts
      workspace.ts
      help.ts
      harness/                 # F1+ façades
    research/
      spawn.ts
      limits.ts
      parseRecipe.ts          # optional
    papers/                   # papers tool impl or client
    bridge/pythonInvoke.ts
  prompts/
    SYSTEM.md                 # parent operator
  agents/
    research.md               # research worker definition
  skills/                     # Pi-visible copies or codegen from ../skills
  recipes/                    # Pi-visible recipe catalog or generated index
  extensions/
    index.ts                  # register tools, commands, hooks
  tests/
```

Monorepo vs dual package: **prefer monorepo** `/home/admin/facktry` with `facktry-pi/` subdirectory and root docs linking ADR + this file. Until the tree is created, this layout is the target shape.

### 9.3 What is *not* laid down

```text
~/.pi/agent/extensions/facktry*     # no
~/.pi/agent/agents/research.md   # no
~/.pi/agent/settings.json packages += facktry  # no by default
```

---

## 10. Launcher UX

### 10.1 Interactive

```bash
facktry run
facktry run --workspace /path/to/project
facktry run --profile dev
facktry run --model <provider/model>
```

- Starts facktry image TUI  
- Shows header: workspace, image version, active profile, active tool count  
- User chats with Facktry Operator  

### 10.2 Headless

```bash
facktry run -p "Research SOTA recipes for tool-use SFT on 8k context"
facktry run --print --json ...
```

- Same factory  
- Exit nonzero on session error  
- stdout: final assistant text and/or JSON event stream (define flag set to match Pi print/json modes where practical)  
- Headless mode is not an elicitation path. If it is ever used for an experiment, it must provide an already-saved MissionBrief; it must not wait for interactive questions or bypass the prerequisite.  

### 10.3 Consistency with human CLI

| Human | Agent host |
|---|---|
| `facktry` / `facktry watch` | live monitor |
| `facktry run` | operator agent |
| `facktry status` | one-shot snapshot |

Do not overload bare `facktry` to mean `facktry run`. ADR assigns bare `facktry` to live truth.

---

## 11. Security and trust

1. **Extensions run with user permissions** (Pi model). Treat facktry-pi as trusted code you wrote.  
2. **Project trust:** if any path uses project `.pi`, follow Pi trust rules; SDK closed loader avoids needing project trust for the default image.  
3. **Research fetch:** outbound HTTP to paper/doc endpoints; respect env proxy; no exfil of local private corpora into web_search queries.  
4. **Prompt injection from papers:** worker treats paper text as untrusted content; forbids following instructions inside papers that ask to exfiltrate secrets or call parent mutation tools (worker has none).  
5. **Child abort:** Ctrl+C / tool abort kills worker session/process.  
6. **Secrets:** bridge must not print tokens; session JSONL redaction policy aligned with ADR privacy doctrine where possible.

---

## 12. Implementation plan (foundation track only)

This track is **orthogonal** to harness phases 00–17 in `codebase_implementation_steps/`. It may start immediately. It must not mark ADR harness checklist items done.

### Phase F0 — Image boots, isolation holds

**Deliverables:**

- `facktry-pi` package builds; `facktry-run` starts  
- Closed resource loader; facktry SYSTEM prompt; no global extension load  
- Parent tools: `questions`, `research`, `facktry_workspace`, `facktry_help`, `read_doc`  
- Research worker with stub or real papers tools enough to demo crawl on one query  
- Sessions under `.facktry/operator-sessions/`  
- Tests: loader isolation (mock), tool allowlist, worker does not see parent tools  
- Docs: README section “Operator runtime”; link this file  
- **No** writes to `~/.pi/agent/extensions` or `agents`  

**Definition of done:**

- With unrelated global Pi extensions installed, `facktry run` still exposes only the facktry allowlist
- `pi` in another directory has zero facktry tools  
- One manual research query returns a structured recipe-shaped summary  

### Phase F0.1 — Papers substrate hardening

- Full papers operations + cache  
- Truncation, iteration limits, doom-loop guard  
- Parallel research safe  
- Golden tests with fixtures (recorded HTTP or frozen HTML)  

### Phase F0.2 — Python bridge stub

- `facktry internal ping` / workspace_info  
- TS invoke helper  
- Tool `harness_ping`  

### Phase F1 — Read-only harness tools

- Depends on store/objective query APIs  
- Operator can inspect objectives/runs without mutation  

### Phase F2 — Mutation tools

- Depends on `agent_api`  
- MissionBrief save/show/list tools available; experiment paths refuse missing briefs  
- Every ADR §7.13 op available as tool  
- Skills rewritten to exact names  
- Govern denials round-trip cleanly  

### Phase F3 — Polish

- Profiles (`operator`, `dev`, `research_only`)  
- Optional recipe JSON artifacts  
- Telemetry: research tokens, tool latency  
- Compaction hooks that preserve objective ids / last decision refs  

---

## 13. Testing strategy

| Layer | What |
|---|---|
| Unit | Resource loader ignores user extensions; allowlists; output truncation; recipe section presence heuristic |
| Unit | Papers parsers on fixture HTML |
| Integration | Nested research session returns summary without parent history leak |
| Integration | Bridge invoke unknown op → structured error |
| Integration | MissionBrief save returns a version/hash; freeze or experiment without one returns a structured denial |
| Smoke | `facktry-run --help`; headless `-p "ping workspace"` |
| Regression | Global Pi pollution test: install a dummy global extension that registers `should_not_appear`; assert absent in facktry image |
| Manual | Real research query on a known task (e.g. small SFT recipe) quarterly |

Harness ADR §13.3 tests remain in Python; do not duplicate them in TS.

---

## 14. Configuration reference (design)

| Variable / flag | Default | Meaning |
|---|---|---|
| `FACKTRY_HOME` | unset → discover `.facktry` | Workspace root |
| `FACKTRY_PI_PROFILE` | `operator` | Tool profile |
| `FACKTRY_PI_RESEARCH_MODEL` | unset → parent model | Worker model id |
| `FACKTRY_PI_INHERIT_USER_AUTH` | `1` | Share auth/models paths |
| `FACKTRY_PI_INHERIT_USER_APPEND` | `0` | Inherit ~/.pi APPEND_SYSTEM |
| `FACKTRY_PI_ALLOW_USER_AGENTS` | `0` | Merge ~/.pi agents |
| `FACKTRY_PI_EXTRA_EXTENSIONS` | empty | Dev-only extra extensions |
| `--workspace` | cwd discovery | Override workspace |
| `--profile` | operator | Profile |
| `-p` / `--print` | off | Headless prompt |
| `--model` | from auth default | Parent model |

---

## 15. Mapping from ML Intern (ideas only)

| ML Intern | Facktry operator foundation |
|---|---|
| Main system prompt research-first | Parent SYSTEM.md |
| `research` tool + isolated loop | Pi nested session / child process |
| `RESEARCH_SYSTEM_PROMPT` crawl order | `agents/research.md` |
| `hf_papers` operations | facktry `papers` tool |
| Recipe table output | Research output contract §7.5 |
| Hosted jobs, billing, and web UI | **Out of scope** |
| Prompt-only smoke-then-scale | **Harness `govern`** when present; prompt reminds only |

No runtime dependency on `ml-intern` or `mlintern-plugin`.

---

## 16. Mapping to ADR

| ADR element | Operator runtime role |
|---|---|
| §3 agent_api | F2 tools call it |
| §5.0 MissionBrief / §7.0 elicit | Parent `questions` + `research` session, then `save_mission_brief` through the Python bridge |
| §3 watch CLI | Separate; not replaced |
| §4 doctrine | Parent prompt + enforced in Python |
| §7.13 agent_api ops | Tool vocabulary |
| §7.16 skills | Shipped to operator image |
| §7.17 recipes | Shipped as read-only effect catalog; recommendation/composition through governed agent_api; notes compound over uses |
| §8 control loop | Prompt + skills + `RecipeStack`s; tools enforce order via govern |
| §13.2 build order | Foundation track parallel; F2 waits for agent_api |

`PI_FOUNDATION.md` governs the operator host; `ADR.md` governs harness behavior. The host uses `questions` and `research` for adaptive elicitation, requires `save_mission_brief` before `freeze_objective` or experimentation, and keeps normal `pi` free of facktry resources.

---

## 17. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Pi upstream API churn | Pin version; thin adapter layer around `createAgentSession` |
| Nested session complexity | Start with child process JSON mode if needed; keep tool UI identical |
| Research quality only prompt-deep | Add recipe schema validation + fixture evals later |
| Operator uses bash to bypass govern | Default deny bash; F2 tools only path; hooks block known train entrypoints |
| Session bloat from research | Isolation + summary-only; compaction; optional drop research traces |
| Auth confusion | Document shared auth vs non-shared extensions |
| Dual language packaging | Clear monorepo scripts; `facktry run` hides Node from casual users |
| Foundation delays harness | Timebox F0; harness phases stay on critical path for product completeness |

---

## 18. Success criteria (foundation)

The foundation is complete enough to build on when:

1. `facktry run` starts a Facktry Operator session with facktry prompt and allowlisted tools only.  
2. A normal `pi` session on the same machine has no facktry tools/subagents.  
3. `research` returns a structured, literature-backed recipe summary via isolated worker.  
4. Sessions persist under the facktry workspace.  
5. No default installation path writes facktry into `~/.pi/agent/extensions` or `agents`.  
6. Bridge stub can ping Python facktry package (once skeleton exists).  
7. Docs tell operators: `facktry run` for agent, `facktry watch` for human, `pi` for generic coding.  
8. An operator can complete adaptive elicitation, save a MissionBrief, and only then reach objective/experiment tools.  
9. When `agent_api` lands, new tools plug into the same image without relaunch redesign.
10. The operator can discover and receive recommendations from curated recipes, inspect append-only use notes, and feed governed outcomes back into the recipe memory without loading ambient user resources.

---

## 19. Open decisions (explicitly deferred)

| Decision | Default until decided |
|---|---|
| In-process nested session vs child `pi` process | Prefer in-process; allow child fallback |
| Papers implementation language | TS caller + Python OK if reuse is easier; keep tool name stable |
| Recipe JSON schema v1 fields | Markdown contract first; schema in F0.1/F3 |
| Dev profile enabled in production installs | Yes, behind `--profile dev` |
| Whether operator sessions are content-hashed into harness lineage | Optional link by session id on Decision dossier later |
| Exact npm package name | `facktry-pi` or `@facktry/operator-runtime` at implementer choice |

---

## 20. Closing rule

When uncertain:

1. **Preserve isolation** from normal `pi`.  
2. **Preserve research isolation** from parent context.  
3. **Do not fake harness mutations.**  
4. **Do not move govern into prompts.**  
5. Prefer a thinner image that boots over a richer image that pollutes global Pi.

This document is the implementation reference for the facktry operator runtime foundation. Build the session image to it; build the training harness to `ADR.md`.
