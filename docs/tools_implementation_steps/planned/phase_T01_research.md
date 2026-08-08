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

This is the highest-leverage operator capability before harness mutations exist: it turns “how should we train?” into attributed, checkable proposals.

---

## Ground-effect prioritization (what to steal from ml-intern)

ml-intern is large. **Implement only what moves quality the most.** Ranked by ground effect:

| Priority | Piece | Why it matters | ml-intern locus |
|---|---|---|---|
| **P0** | Isolated sub-agent + summary-only return | Stops paper/HTML from destroying parent context; enables deep crawl | `research_tool.py` loop |
| **P0** | Literature-first crawl doctrine in **worker** prompt | Without this, models skip to vibes/docs and invent recipes | `RESEARCH_SYSTEM_PROMPT` |
| **P0** | Parent prompt gate: research before inventing train recipes | Without this, tool sits unused | main system prompt § research |
| **P0** | `papers` tool with **search + read_paper (TOC/section) + citation_graph** | Crawl is impossible without these three | `papers_tool.py` ops |
| **P0** | Result↔recipe output contract (recipe table) | Hand-off unit the parent can act on | research output format |
| **P1** | Tool-output truncation + iteration/context caps + doom-loop | Prevents runaway cost/loops | research loop + `doom_loop.py` |
| **P1** | Hub dataset inspect after papers | Catches “paper dataset doesn’t exist / wrong columns” early | `hf_inspect_dataset` |
| **P1** | GitHub example find + file read | Grounds “how to call current APIs” | `github_find_examples`, `github_read_file` |
| **P2** | Docs explore/fetch | Fills API details after code examples | `explore_hf_docs`, `fetch_hf_docs` |
| **P2** | `find_datasets` / `find_all_resources`, `snippet_search`, `recommend` | Faster linking & graph misses | papers ops |
| **P3** | YOLO billing, Trackio-alert loops, HF Jobs preflight essays, web UI research overlays | Low leverage for facktry foundation | skip |
| **P3** | Unrestricted worker `bash` | Foot-gun; prefer fetch inside papers tool | skip or deny by default |

**Non-goals for T01:** full ml-intern product, sealed eval, admit, train jobs, automatic proposal promotion, recipe-stack execution, multi-judge panels. Curated recipe loading belongs to the recipe/catalog track.

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
  │  tools  = papers, dataset_inspect, github_*, docs_*, web_search?, read?
  │  NOT    = write/edit, train_*, admit, yield_release, unrestricted bash
  ▼
Worker loop (≤ N iters)
  │  papers.search → citation_graph(downstream) → read_paper TOC/§
  │  → attribute recipes → dataset_inspect → code/docs
  │  truncate tool obs; doom-loop guard; context budget
  ▼
Final worker text (recipe table …) → parent tool result only
```

**Preferred spawn:** in-process nested `createAgentSession` with in-memory session + research allowlist (PI_FOUNDATION §7.2).  
**Fallback:** child `pi --mode json` with explicit prompt/tools (upstream subagent example).

During `elicit`, the parent may run this worker between `questions` volleys to make the next human questions more informed. The worker never interviews the human. Its bounded response is proposal evidence; the parent saves only a very brief one-line summary plus references/pointers in the final MissionBrief.

Do **not** run the crawl in the parent message list.

---

## In scope

### 1. Parent tool: `research`

| Field | Spec |
|---|---|
| `name` | `research` |
| `label` | `Research` |
| `description` | Spawn an isolated research worker to crawl literature and return ranked training/method recipes with evidence. Use between elicitation question volleys or before inventing datasets, trainers, or hparams for non-trivial ML work. Worker is read-mostly; returns summary only. |
| Params | `task: string` (required), `context: string` (optional) |
| `executionMode` | Prefer default parallel-friendly **unless** implementation cannot isolate concurrent workers cleanly; then sequential. Multiple parallel `research` calls **should** work (unique run ids). |
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
  // Optional stretch: parsed recipes[] if JSON mode added
};
```

**renderCall / renderResult:** short title + task preview; result shows ok/fail + first recipe line or error.

### 2. Worker system prompt (P0 — ship as real file)

**Path:** `facktry-pi/agents/research.md` and/or `facktry-pi/prompts/RESEARCH_SYSTEM.md`

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

- Treat baked-in library knowledge as stale for train recipes.  
- Before proposing or implementing a training approach, call `research` with a specific task + user constraints in `context`; during `elicit`, use it between question volleys when it can sharpen the next questions or success-case proposals.  
- Research output is a **proposal**, not a passed gate or curated recipe. During elicitation, retain only a one-line summary and references/pointers in the MissionBrief; do not copy full paper bodies into the dossier. A proposal may later be reviewed into `docs/recipes/<recipe-id>/RECIPE.md`.
- Skip only for trivial non-method questions.
- On plateau/failure of an approach, research again (deeper graph), don’t invent scope changes.

Do not paste the entire ml-intern Trackio/Jobs essay into the parent prompt.

### 4. Worker tool allowlist (T01 minimum)

#### P0 — must ship

| Tool | Role | Minimum ops |
|---|---|---|
| `papers` | Literature substrate | `search`, `paper_details`, `read_paper` (TOC + section), `citation_graph` |
| _(internal)_ | HTML section parse | arxiv/ar5iv HTML → sections; abstract fallback |

#### P1 — should ship in same phase if feasible; else T01.1 immediately after

| Tool | Role |
|---|---|
| `papers` extras | `find_datasets` or `find_all_resources`; optional `snippet_search`, `recommend` |
| `hub_inspect_dataset` | schema/splits/sample rows; note SFT/DPO/GRPO column expectations in tool description |
| `github_find_examples` | fuzzy path search in known example dirs (default org `huggingface`) |
| `github_read_file` | path + optional line range |

#### P2 — include if cheap; otherwise later

| Tool | Role |
|---|---|
| `explore_docs` / `fetch_docs` | HF docs endpoints or generic URL fetch allowlisted to docs hosts |
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
           | "find_datasets" | "find_all_resources" | "snippet_search" | "recommend" | "trending?",
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
    index.ts              # registerTool papers (also usable by parent later)
    ops/*.ts
    htmlSectionParse.ts
    s2.ts
    hf.ts
    cache.ts
    format.ts
  src/tools/hub_inspect_dataset.ts      # P1
  src/tools/github_find_examples.ts     # P1
  src/tools/github_read_file.ts         # P1
  prompts/RESEARCH_SYSTEM.md
  agents/research.md                    # frontmatter name/tools/model if using agent defs
  tests/tools/research/*
  tests/tools/papers/*                  # fixtures: frozen HTML, mocked HTTP
```

**Language split:** TS tools calling Python is OK for HTML parse/S2 if faster — keep tool names stable. Prefer one HTTP cache root under workspace.

### 9. Wiring into facktry image

- Register `research` + worker backend tools on the **parent** tool router only as needed:  
  - Parent active tools: include `research` (and maybe `papers` for quick lookups).  
  - Worker: full research allowlist.  
- Parent must **not** need worker tools all active if that bloats parent prompt — worker session loads them.  
- Never install into `~/.pi/agent/`.  
- Sessions: parent under `.facktry/operator-sessions/`; worker in-memory or `.facktry/operator-sessions/research/`.

---

## Out of scope

- Harness gates consuming research proposals or recipe notes as truth
- Auto-starting train from a research proposal or recipe
- ml-intern YOLO, Trackio, Jobs, sandbox GPU preflight walls  
- Full docs endpoint zoo on day one (subset is enough)  
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
2. **Worker prompt file** + spawn nested session with papers-only allowlist  
3. **Parent `research` tool** wiring + progress logs + abort  
4. **Loop guards** (truncate, max iters, doom loop, context budget if token usage available)  
5. **Parent SYSTEM.md** research-before-recipe blurb  
6. **P1 tools** dataset inspect + github examples/read  
7. **P2** docs/web as time allows  
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
7. Parent prompt documents when to call research.  
8. Elicitation can use the research result between question volleys and retain only one-line summary/reference pointers in the MissionBrief.  
8. This doc → `complete/`; README index `[x]`.  
9. Still nothing installed into `~/.pi/agent/extensions`.

---

## Handoff / follow-ons

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
| `RESEARCH_SYSTEM_PROMPT` | `prompts/RESEARCH_SYSTEM.md` |
| `RESEARCH_TOOL_NAMES` | `allowlist.ts` (stricter: no bash by default) |
| `hf_papers` operations | `papers` tool |
| `_parse_paper_html` | `htmlSectionParse` |
| S2 + HF APIs | `s2.ts` + `hf.ts` + disk cache |
| `check_for_doom_loop` | `doomLoop.ts` |
| main `system_prompt_v3` research block | operator `SYSTEM.md` short block |
| recipe table output | same contract; optional JSON later |
| YOLO / Jobs / Trackio walls | **omit** |

---

## Closing rule

If scope creeps, keep these four and cut everything else:

1. **Isolated worker**  
2. **papers: search + citation_graph + read_paper**  
3. **Literature-first + recipe-table prompts**  
4. **Summary-only return with truncation/limits**  

That set is the ground-effect core of ml-intern’s research pipeline.
