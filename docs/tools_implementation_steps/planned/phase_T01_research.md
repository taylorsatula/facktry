# Phase T01 — `research` tool (literature → recipe sub-agent)

| Field | Value |
|---|---|
| **Status** | [ ] |
| **Depends on** | `facktry-pi` session image able to register tools (same bar as T00). **Does not** depend on harness `store`/`admit`/`train`. T00 (`questions`) is independent — either order is fine. |
| **PI_FOUNDATION refs** | §7 Research subagent (normative design), §5.3 isolation doctrine, §6.1 operator prompt research-before-implementation, §9.2 package layout |
| **ADR refs** | §5.0 `MissionBrief`; §7.0 `elicit`; operator plans methods under budget; research proposals are **not** gates. Admit/smoke/measure/decide still own truth when harness exists. |
| **Primary prior art** | Hugging Face `ml-intern` (`/home/admin/facktry/reference_repos/ml-intern`), Apache 2.0 — especially `agent/tools/research_tool.py`, `agent/tools/papers_tool.py`, `agent/prompts/system_prompt_v3.yaml`, `agent/core/doom_loop.py` |
| **Pi prior art** | `examples/extensions/subagent/` (isolated child session pattern); SDK `createAgentSession` + tool allowlists |

---

## Goal

Ship a parent-facing **`research` tool** for the facktry operator image that:

1. Accepts a natural-language research brief (`task` + optional `context`).
2. Runs an **isolated** worker agent with a **read-mostly** tool allowlist.
3. Forces a **literature-first crawl** (papers → citation graph → methodology → result↔recipe → dataset check → code/docs).
4. Returns only a **bounded, structured recipe summary** into the parent context (no raw paper dumps).
5. Produces a provisional `RecipeProposal`; it does not silently create or edit a curated `docs/recipes/<id>/RECIPE.md`.

It turns “how should we train?” into attributed, checkable proposals before harness mutations exist.

---

## Prioritized scope (from ml-intern)

Implement the following in priority order; defer lower-priority items explicitly:

| Priority | Piece | Why it matters | ml-intern locus |
|---|---|---|---|
| **P0** | Isolated sub-agent + summary-only return | Stops paper/HTML from destroying parent context; enables deep crawl | `research_tool.py` loop |
| **P0** | Literature-first crawl doctrine in **worker** prompt | Without this, models skip literature and invent recipes | `RESEARCH_SYSTEM_PROMPT` |
| **P0** | Parent prompt gate: research before inventing train recipes | Without this, tool sits unused | main system prompt § research |
| **P0** | `papers` tool with **search + read_paper (TOC/section) + citation_graph** | Crawl is impossible without these three | `papers_tool.py` ops |
| **P0** | Result↔recipe output contract (recipe table) | Hand-off unit the parent can act on | research output format |
| **P1** | Tool-output truncation + iteration/context caps + doom-loop | Prevents runaway cost/loops | research loop + `doom_loop.py` |
| **P1** | Hub dataset inspect after papers | Detects missing datasets and wrong columns early | `hub_inspect_dataset` |
| **P1** | GitHub example find + file read | Grounds “how to call current APIs” | `github_find_examples`, `github_read_file` |
| **P2** | Docs explore/fetch | Fills API details after code examples | `explore_docs`, `fetch_docs` |
| **P2** | `find_datasets` / `find_all_resources`, `snippet_search`, `recommend` | Faster linking & graph misses | papers ops |
| **P3** | Billing, alert loops, hosted-job preflight, and web UI overlays | Low leverage for the facktry foundation | skip |
| **P3** | Unrestricted worker `bash` | Unsafe; use fetch inside papers tools | skip or deny by default |

**Non-goals for T01:** full ml-intern product, sealed eval, admit, train jobs, automatic proposal promotion, RecipeStack execution, or multi-judge panels. Curated recipe loading belongs to the recipe/catalog track.

**Priority semantics:** P0 is required. P1 is the T01 target and may move to T01.1 only with an explicit deferral. P2 is optional. `Must`, `should`, and `may` follow these classifications.

---

## Architecture

```text
Parent (Facktry Operator)
  │  research({ task, context? })
  │  execution: can be long-running; show progress logs
  ▼
research.execute
  │  build worker session (nested createAgentSession OR child pi --mode json)
  │  system = RESEARCH_SYSTEM_PROMPT
  │  user   = "Context: …\n\nResearch task: …"
  │  tools  = papers, hub_inspect_dataset, github_find_examples, github_read_file,
  │           explore_docs, fetch_docs, web_search, narrow read
  │  NOT    = write/edit, train_*, admit, yield_release, unrestricted bash
  ▼
Worker loop (≤ N iters)
  │  papers.search → citation_graph(downstream) → read_paper TOC/§
  │  → attribute recipes → hub_inspect_dataset → code/docs
  │  truncate tool obs; doom-loop guard; context budget
  ▼
Final worker text (recipe table …) → parent tool result only
```

The diagram shows the planned allowlist. T01 may defer P1/P2 tools only as stated in the priority semantics; deferred tools are not registered until their follow-on phase.

**Preferred spawn:** in-process nested `createAgentSession` with an in-memory session and research allowlist (PI_FOUNDATION §7.2). **Fallback:** child `pi --mode json` with explicit prompt and tools (upstream subagent example).

During `elicit`, the parent may run this worker between `questions` volleys to make the next human questions more informed. The worker never interviews the human. Its bounded response is proposal evidence; the parent saves only a very brief one-line summary plus references/pointers in the final MissionBrief.

Do **not** run the crawl in the parent message list.

---

## In scope

### 1. Parent tool: `research`

| Field | Spec |
|---|---|
| `name` | `research` |
| `label` | `Research` |
| `description` | Spawn an isolated research worker to crawl literature and return ranked training/method recipes with evidence. Use between elicitation volleys or before inventing datasets, trainers, or hparams. The worker is read-mostly and returns a summary only. |
| Params | `task: string` (required), `context: string` (optional) |
| `executionMode` | Default to parallel-friendly execution; use sequential only when concurrent isolation is unsafe. Parallel `research` calls must use unique run ids. |
| Progress | Emit tool logs / `onUpdate` chunks so TUI doesn’t look frozen (`Starting…`, `▸ papers search …`, `tokens:…`, `Research complete.`) |
| Abort | Honor tool `signal`; kill nested session/child process |

**Result:**

- `content[]` text = worker summary (or structured error).
- `details` (normative):

```ts
type ResearchDetails = {
  ok: boolean;
  task: string;
  summary: string | null;
  cancelled?: boolean;
  error?: string;
  stats?: {
    iterations: number;
    toolCalls: number;
    inputTokens?: number;
    outputTokens?: number;
    durationMs: number;
    model?: string;
  };
  // Optional extension: parsed recipes[] if JSON mode is added
};
```

Abort sets `cancelled: true`; failures set `ok: false` and return error text through `error`/`content`. Clean up the child session before returning.

**renderCall / renderResult:** short title + task preview; result shows ok/fail + first recipe line or error.

### 2. Worker system prompt (P0 — ship as real file)

**Canonical source:** `facktry-pi/agents/research.md`. If a separate prompt file is required by the launcher, generate it from this source; do not maintain two independent prompts.

Port the **crawl doctrine** from ml-intern’s `RESEARCH_SYSTEM_PROMPT` (adapt naming to facktry tools):

1. Start from **literature**, not docs/scripts.  
2. Anchor papers → **downstream** citation graph → methodology/experiments sections.  
3. Every finding is **result ↔ recipe** (`dataset + method + hparams → metric on benchmark`).  
4. Validate promising datasets (Hub inspect).  
5. **Code/docs last** for implementable patterns.  
6. Output **recipe table + code patterns + recommendations + SOTA + refs**.  
7. Cap length ~**500–1500 words**; real snippets not paraphrase-only.  

Include a short “correct pattern” tool sequence using **facktry tool names**.

### 3. Parent system prompt hook (P0)

Update facktry operator `SYSTEM.md` (when it exists) with a tight block:

- Treat embedded library knowledge as potentially stale for train recipes.
- Before proposing or implementing a training approach, call `research` with a specific task + user constraints in `context`; during `elicit`, use it between question volleys when it can sharpen the next questions or success-case proposals.  
- Research output is a **proposal**, not a passed gate or curated recipe. During elicitation, retain only a one-line summary and references/pointers in the MissionBrief; do not copy full paper bodies into the dossier. A proposal may later be reviewed into `docs/recipes/<recipe-id>/RECIPE.md`.
- Skip only for trivial non-method questions.
- On plateau/failure of an approach, research again (deeper graph), don’t invent scope changes.

Do not paste the full hosted-training and alerting design into the parent prompt.

### 4. Worker tool allowlist (T01 minimum)

#### P0 — must ship

| Tool | Role | Minimum ops |
|---|---|---|
| `papers` | Literature substrate | `search`, `paper_details`, `read_paper` (TOC + section), `citation_graph` |
| _(internal)_ | HTML section parse | arxiv/ar5iv HTML → sections; abstract fallback |

#### P1 — target for T01; defer to T01.1 only with an explicit checklist note

| Tool | Role |
|---|---|
| `papers` extras | `find_datasets` or `find_all_resources`; optional `snippet_search`, `recommend` |
| `hub_inspect_dataset` | schema, splits, and sample rows; describe SFT/DPO/GRPO column expectations |
| `github_find_examples` | fuzzy path search in known example directories (default org `huggingface`) |
| `github_read_file` | path and optional line range |

#### P2 — optional; defer beyond T01 unless low cost

| Tool | Role |
|---|---|
| `explore_docs` / `fetch_docs` | HF docs endpoints or generic URL fetch limited to allowed documentation hosts |
| `web_search` | fallback when papers/docs miss; optional domain allow/deny |
| narrow `read` | local allowlisted notes only |

#### Forbidden on worker

`write`, `edit`, unrestricted `bash`, `train_*`, `admit`, `generate_and_admit`, `yield_release`, `questions` (human Q&A stays parent), promote/canary.

If `bash` is tempting for curl: **put HTTP inside `papers` / docs tools instead.**

### 5. `papers` tool design (P0 substrate)

Single tool, operation-dispatch (ml-intern pattern) — stable name `papers`:

```text
papers({
  operation: "search" | "paper_details" | "read_paper" | "citation_graph"
           | "find_datasets" | "find_all_resources" | "snippet_search" | "recommend" | "trending", // optional
  query?: string,
  arxivId?: string,      // or arxiv_id — pick one casing and stick to camelCase for Pi
  section?: string,      // number or title substring
  direction?: "citations" | "references" | "both",  // default "citations" for crawl tips; API default may be both
  dateFrom?, dateTo?, minCitations?, sortBy?, limit?
})
```

**Backends (match ml-intern’s winning combo):**

| Need | Source |
|---|---|
| ML-ish paper search / daily | `https://huggingface.co/api` papers endpoints |
| Metadata | HF `/papers/{id}` |
| Full text sections | `arxiv.org/html/{id}` then `ar5iv.labs.arxiv.org/html/{id}`; parse `ltx_title` headings |
| Citations / filters / snippets / recommend | Semantic Scholar Graph API (`S2_API_KEY` optional) |
| Hub artifacts linked to paper | HF datasets/models/collections with `arxiv:` / paper filters |

**Implementation requirements:**

- Format results as **markdown for the worker LLM** (titles, arxiv ids, next-step tips) — same spirit as ml-intern formatters.  
- `read_paper` without `section` → abstract + TOC; with `section` → body truncated (e.g. 8k chars).  
- Cache HTTP GETs under `.facktry/cache/papers/` with TTL (improve on ml-intern’s process-only S2 cache).  
- Timeouts, retries on 429/5xx, no secrets in logs.  
- Graceful degradation: S2 down → HF search still works; HTML missing → abstract-only.  
- `limit` default 10, max 50.

**Section parser:** port logic from ml-intern `_parse_paper_html` / `_find_section` (BeautifulSoup or equivalent in TS/Python service). This is worth the dependency.

### 6. Worker loop controls (P1 — small code, large stability)

Port the *ideas*, tune numbers to facktry models:

| Control | ml-intern | T01 guidance |
|---|---|---|
| Max iterations | 60 | 40–60; then force summary with tools disabled |
| Context warn / hard | 170k / 190k total_tokens | Scale to worker model window (e.g. warn ~75%, hard ~90%) |
| Tool obs truncate | >8k → head 4800 + tail 3200 | Keep similar |
| Doom loop | identical call×3 or repeating seq | Port simplified detector; inject wrap-up SYSTEM message |
| LLM timeout | 120s/call | similar |
| Effort | cap above `high` | if parent thinking is extreme, cap worker |
| Model | parent or `FACKTRY_PI_RESEARCH_MODEL` | env override |

Forced summary messages (context/iteration) should say: summarize findings now; no more tools.

### 7. Output contract enforcement (light)

ml-intern does **not** validate the recipe table. T01 minimum:

- Worker prompt requires the sections.  
- Optional post-check: if summary lacks a `## Recipe` heading (or similar), append a one-line warning in `details` / content footer asking parent to re-run with narrower task — **do not** infinite-loop retry automatically in T01.

Stretch (not required): ask worker for final JSON matching `RecipeProposal[]` and render markdown for parent.

### 8. Package layout

```text
facktry-pi/
  src/tools/research/
    index.ts              # registerTool research
    spawn.ts              # nested session / child process
    loop.ts               # if manual loop instead of full AgentSession
    allowlist.ts
    limits.ts
    doomLoop.ts
    format.ts
    types.ts
  src/tools/papers/
    index.ts              # registerTool papers for the worker
    ops/*.ts
    htmlSectionParse.ts
    s2.ts
    hf.ts
    cache.ts
    format.ts
  src/tools/hub_inspect_dataset.ts      # P1
  src/tools/github_find_examples.ts     # P1
  src/tools/github_read_file.ts         # P1
  agents/research.md                    # canonical worker definition
  tests/tools/research/*
  tests/tools/papers/*                  # fixtures: frozen HTML, mocked HTTP
```

**Language split:** TS tools calling Python is OK for HTML parse/S2 if faster — keep tool names stable. Prefer one HTTP cache root under workspace.

### 9. Wiring into facktry image

- Register `research` + worker backend tools on the **parent** tool router only as needed:  
  - Parent active tools: include `research`; keep `papers` worker-only by default.
  - Worker: full research allowlist.  
- Parent must **not** need worker tools all active if that bloats parent prompt — worker session loads them.  
- Never install into `~/.pi/agent/`.  
- Sessions: parent under `.facktry/operator-sessions/`; worker in-memory or `.facktry/operator-sessions/research/`.

---

## Out of scope

- Harness gates consuming research proposals or recipe notes as truth
- Auto-starting train from a research proposal or recipe
- ml-intern billing, alerting, hosted jobs, and sandbox GPU preflight walls
- The complete documentation endpoint set on day one (a subset is sufficient)
- Perfect citation-intent analytics UI  
- Global Pi extension publish  

---

## Fail-closed / product rules

1. **Isolation:** worker history ≠ parent history; only summary returns.  
2. **No mutations** from research path.  
3. **Cancel/abort** cleans up child work.  
4. **Headless OK:** research must work in print/json modes (no TUI dependency). Unlike `questions`, research is non-interactive.  
5. **Proposal not proof:** parent prompt + tool description state recipes don’t skip admit/measure.  
6. **Privacy:** don’t put local private corpora into `web_search` queries; paper text is untrusted (ignore instruction-injection in PDFs/HTML).  
7. **Degradation over crash:** backend failures return tool error strings to worker; worker still summarizes partial findings.

---

## Implementation sequence (inside T01)

Do in this order so each slice is usable:

1. **`papers` P0 ops** + HTML parse + cache + unit fixtures  
2. **Canonical worker prompt** + nested session with the papers-only allowlist
3. **Parent `research` tool** wiring + progress logs + abort  
4. **Loop guards** (truncate, max iters, doom loop, context budget if token usage available)  
5. **Parent SYSTEM.md** research-before-recipe blurb  
6. **P1 tools** dataset inspect + github examples/read  
7. **P2** docs/web only if time remains; otherwise record the deferral as T01.1
8. Manual smoke: one real query (e.g. “SFT recipes for tool-use / function calling”)  

---

## Tests

### papers

- HTML fixture → sections extracted; `section="3"` and title fuzzy match.  
- Search formatter includes arxiv ids.  
- Citation graph direction param hits correct client paths (mock HTTP).  
- Cache hit doesn’t refetch.  
- Abstract fallback when HTML empty.  

### research loop

- Allowlist rejects `write` / `train_smoke` if somehow requested.  
- Truncate long tool output.  
- Doom loop: three identical tool signatures → inject guard (unit on pure fn).  
- Max iterations triggers summary path (mock LLM).  
- Parallel ids don’t collide (unique toolCallId).  

### integration smoke

- `research` with mocked papers stack returns non-empty summary and `details.ok`.  
- Parent session messages after tool contain summary text once, not full HTML.  

### manual

- Live S2/HF network optional behind env flag in CI; document `FACKTRY_RESEARCH_LIVE=1` local run.

---

## Definition of done

1. Operator can call `research` inside `facktry run` (or dev loader).  
2. Worker runs isolated with P0 papers crawl tools.  
3. Summary is recipe-oriented (prompt contract) and bounded.  
4. Parent context is not flooded with raw HTML.  
5. Abort + error paths don’t hang the session.  
6. Unit tests for parse/truncate/doom/cache pass.  
7. P1 tools ship or are explicitly deferred to T01.1; P2 deferrals are recorded.
8. Parent prompt documents when to call research.
9. Elicitation can use the research result between question volleys and retain only one-line summary/reference pointers in the MissionBrief.
10. This doc moves to `complete/`; the README index becomes `[x]`.
11. Nothing is installed into `~/.pi/agent/extensions`.

---

## Handoff and follow-ons

| Next | Purpose |
|---|---|
| T01.1 | P1/P2 tools if deferred; snippet_search + recommend |
| T01.2 | Structured `RecipeProposal` JSON + optional provisional artifact when `store` exists |
| Recipe/catalog track | Curated `RECIPE.md` parsing, append-only notes, `RecipeStack` composition, and governed application |
| F2 harness tools | Parent may pass curated recipe/stack refs into objective and run records — still not auto-gates |
| Eval harness | Golden tasks: “find recipe for X” scored on presence of arxiv + dataset + hparams |

---

## Reference map (ml-intern → facktry T01)

| ml-intern | facktry T01 |
|---|---|
| `research` tool + `research_handler` loop | `tools/research/*` |
| `RESEARCH_SYSTEM_PROMPT` | `agents/research.md` |
| `RESEARCH_TOOL_NAMES` | `allowlist.ts` (stricter: no bash by default) |
| `hf_papers` operations | `papers` tool |
| `_parse_paper_html` | `htmlSectionParse` |
| S2 + HF APIs | `s2.ts` + `hf.ts` + disk cache |
| `check_for_doom_loop` | `doomLoop.ts` |
| main `system_prompt_v3` research block | operator `SYSTEM.md` short block |
| recipe table output | same contract; optional JSON later |
| Billing, hosted jobs, and alerting | **omit** |

---

## Scope guard

If scope creeps, retain the P0 deliverables in the priority table: isolated worker; `papers.search` + `citation_graph` + `read_paper`; literature-first recipe-table prompting; and bounded summary-only return.

Those P0 items are the minimum research capability for facktry.
