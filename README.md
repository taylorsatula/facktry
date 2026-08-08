# Facktry

**Facktry is an autonomous, governed model-development harness.**

It turns a human-defined mission into a reproducible model or dataset release by giving an AI operator a controlled loop for elicitation, research, recipe selection, data construction, self-play, training, evaluation, correction, and release. The operator can work autonomously within explicit policy and budget; a human overseer remains responsible for irreducibly human judgments and final promotion.

Facktry is built for teams that want more than a training script and more than an experiment tracker. It treats **data, weights, prompts, interfaces, evaluation, and serving guards as one release** and requires every consequential change to produce inspectable, hashed evidence.

## The control loop

A Facktry objective follows a deliberate, fail-closed sequence:

```text
human mission
  → adaptive elicitation and research
  → immutable MissionBrief
  → frozen Objective
  → pinned dev and sealed suites
  → data construction, self-play, and harvesting
  → deterministic filtering and admission
  → smoke training
  → scale training
  → gate-constrained checkpoint selection
  → paired sealed measurement
  → Decision and dossier
  → correct, hold, abort, or human-authorized release
```

The harness enforces the important arrows rather than merely documenting them:

- **MissionBrief before mutation** — natural-language intent is not an executable objective.
- **Admit before train** — every training corpus passes structure, attribution, leakage, diversity, mixture, teacher, vocabulary, and privacy checks.
- **Smoke before scale** — scale training requires a completed, successful, compatible smoke run.
- **Measure before promote** — candidates are measured against pinned baselines using the same suite, seeds, decode configuration, and interface.
- **Human at the boundary** — taste, research fit, borderline judgments, policy exceptions, and final promotion flow through explicit human gates.

## What Facktry produces

For a model objective, the deliverable is a content-addressed **`ReleaseTuple`**: the complete shippable stack, not just an adapter or checkpoint:

- base weights
- adapter, when present
- tokenizer
- chat template
- prompt policy
- tool and state schema
- decode configuration
- guard policy
- exact applied recipe stack, when applicable

A successful iteration also produces a reproducible `Decision` dossier whose hard-gate evidence can be rebuilt from hashed artifacts. Data-only objectives produce admitted corpus artifacts and an auditable Decision without pretending that a dataset is a model release.

## Recipes: institutional memory for model development

Recipes are a defining part of Facktry. They are not prompt snippets, hyperparameter dumps, or unverified research recommendations. A recipe is a versioned, evidence-backed specification for creating a named behavioral effect in a model stack.

A recipe may describe coordinated changes across:

- data sources, transformations, and mixture targets
- training method, parent/reference model, and safe parameter ranges
- prompts, tool schemas, and interface policies
- serving guards and decoding
- evaluation suites, baselines, and validation requirements
- expected tradeoffs, regressions, and failure signatures

The operator can discover recipes, recommend candidates from the current objective and defect history, and compose compatible recipes into an immutable **`RecipeStack`** with exact versions, ordering, overrides, allocations, conflicts, and a validation plan.

Recipe use never bypasses the ordinary loop. A recipe cannot weaken hard gates, replace sealed measurement, or turn a claim into evidence. After every governed use—including a failed or non-promoted attempt—Facktry records an append-only, structured outcome note containing the adaptation, observed effects, regressions, evidence references, recommendation, and confidence. Instruction hashes remain stable while notes accumulate, allowing successful model-development knowledge to compound without corrupting history.

## Self-play, partner-play, and trajectory generation

Facktry supports self-play and simulated-partner workflows for producing training data and exercising multi-turn behavior. A domain supplies a deterministic or model-backed **World** with a reset/step protocol, authorized actions, private oracle state, and transcript export.

The episode runner provides:

- subject↔partner interaction loops with a hard runner-side turn cap
- deterministic seeds and reproducible scenarios
- tool/action validation before world transitions
- visible transcripts containing turns and tool records
- strict separation of private world state from subject prompts and open artifacts
- deterministic analysis of repetition, unresolved requests, tool errors, turn counts, and termination
- a separate simulator-realism scorecard when the partner is model-driven

Generated trajectories can feed deterministic filters and the admission gate, become preference pairs, or execute as multi-turn and tool-episode suite cases. Stop tokens are advisory; the runner always enforces the cap. Self-play is a coverage and interaction mechanism—not proof of quality. Quality is established by held-out, sealed, and human-relevant measurement.

## Evaluation and decision integrity

Facktry keeps planning blind to sealed cases. Sealed suites hold their case text and private state inside runner custody and expose only scorecards, aggregates, and gate results. Paired comparison runs the same frozen evaluation against the required baselines: base, ancestor when present, candidate, and production tuple when applicable.

Deterministic verification owns hard checks such as:

- schema and grammar validity
- privacy and canary detection
- state-transition consistency
- claim-versus-execution honesty
- unsupported actions
- evidence entailment
- injected execution checks
- abstention when verified state is insufficient

An optional calibrated LLM judge can contribute soft evidence, but it can never own a hard gate. Uncalibrated judgment is diagnostic only.

Checkpoint selection maximizes configured, gate-backed soft objectives subject to hard constraints. It cannot select by last step, training loss, or validation loss alone. Decisions apply hard, human, soft, and diagnostic results in a fixed order; missing evidence fails closed.

## Governed autonomy

The Python `agent_api` is the single mutation surface for the operator. It governs:

- policy capabilities and human authority
- budget ledgers and atomic charges
- preflight, disk, hardware, and GPU-exclusivity checks
- suite pins and interface compatibility
- MissionBrief and Objective provenance
- admission and training prerequisites
- smoke-to-scale transitions
- checkpoint selection, measurement, and decisions
- human inbox responses and release pinning

Every refusal is typed and structured. There is no “admit anyway,” silent fallback, or prompt-only version of governance.

## Privacy and preservation

Facktry is designed for sensitive model-development workflows:

- raw private sources are never artifacts
- logs and manifests contain hashes, summaries, counts, and policy metadata—not private payloads
- remote calls require explicit policy and use redaction where applicable
- sealed state remains in runner custody
- every training attempt gets a new run directory
- base models, ancestor adapters, and prior production pins are never overwritten
- all artifacts, manifests, suites, tuples, decisions, and recipe versions are hash-verified

## Operator surfaces

Facktry deliberately separates autonomous operation from human oversight:

### `facktry run`

Starts the isolated Pi-based **Facktry Operator**. It provides the operator prompt, Facktry skills, research worker, recipe catalog, and governed tools without loading ambient user extensions or agents from a normal Pi installation.

### `facktry` / `facktry watch`

Opens the human read-only monitor. Bare invocation auto-focuses the most important state: pending inbox work, active or guarded runs, unsaved mission provenance, open objectives, and the latest decision or production pin.

### Other human commands

- `facktry status` — one-shot situational snapshot
- `facktry inbox` — inspect and answer explicit human gates
- `facktry show <id>` — inspect a mission brief, objective, run, decision, tuple, or inbox item
- `facktry ls` — recent objectives, runs, and decisions

The normal `pi` command remains a stock coding environment and does not load Facktry resources.

## Quick start

```bash
pip install facktry

# Initialize or discover the local .facktry workspace and view status
facktry status

# Start the Facktry Operator
facktry run
```

Workspace discovery is shared by the agent and human surfaces: `FACKTRY_HOME` takes precedence, then Facktry walks the current directory and its parents for `.facktry/`, and otherwise creates `.facktry/` in the current directory. Persistent state includes runs, metrics, content-addressed artifacts, immutable briefs and objectives, suites, decisions, defects, inbox items, budgets, recipe stacks, and operator sessions.

## Core design principles

1. **Intent before invention.** Elicit the mission, record the success case and anti-goals, approve hard gates individually, and save the complete brief.
2. **Hard gates are code.** Safety, privacy, split integrity, schema validity, attribution, and tool honesty do not belong solely to an LLM judge.
3. **Scores must have meaning.** Soft scores influence correction; diagnostic metrics cannot select or promote.
4. **Optimize the stack.** Weights, data, prompts, interfaces, decode, guards, and evaluation are one release identity.
5. **Synthetic data is coverage, not proof.** Self-play and generation must pass admission and then face independent sealed measurement.
6. **Paired evidence wins.** Candidate behavior is compared with frozen baselines under identical evaluation conditions.
7. **Preserve ancestors.** Corrective work creates new runs from declared parents; it never overwrites history.
8. **Human authority is explicit.** The agent may request human judgment, but it cannot manufacture an approval or silently flip production.
9. **Domain logic stays modular.** Task-specific generators, worlds, suites, tools, and oracles live in domain packs rather than contaminating the core.
10. **If it is not hashed, it did not happen.** Decisions cite immutable artifacts, code, environment, inputs, outputs, and interface identities.

## Documentation

- [`docs/ADR.md`](docs/ADR.md) — authoritative product and architecture specification
- [`docs/PI_FOUNDATION.md`](docs/PI_FOUNDATION.md) — isolated Pi operator runtime foundation
- [`docs/PI_RUNTIME.md`](docs/PI_RUNTIME.md) — Pi integration boundary and runtime architecture
- [`docs/skills/`](docs/skills/) — operator playbooks
- [`docs/recipes/`](docs/recipes/) — curated effect recipes and append-only recipe notes
- [`docs/codebase_implementation_steps/`](docs/codebase_implementation_steps/) — Python harness implementation contracts
- [`docs/tools_implementation_steps/`](docs/tools_implementation_steps/) — Pi tool implementation contracts

## Project structure

```text
facktry/                 Python harness, store, governance, evaluation, training, and agent API
facktry-pi/              Isolated Pi operator runtime
 docs/                   Architecture, skills, recipes, and implementation guidance
tests/                   Contract, privacy, custody, and end-to-end tests
```

## License

See the repository license file for usage and distribution terms.
