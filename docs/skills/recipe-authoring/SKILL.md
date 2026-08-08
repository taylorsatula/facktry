---
name: recipe-authoring
description: Create curated model-effect recipes from the canonical template and append structured, evidence-backed notes after recipe uses. Keep recipe instructions versioned, notes append-only, and all claims subject to ordinary facktry governance and measurement.
---

# Recipe authoring

Use this skill when creating a new `RECIPE.md` or recording a subsequent use of an existing recipe.

A recipe is a versioned, evidence-backed specification for creating a named behavioral effect in a model stack. It may combine data, training, prompt/interface, serving, and evaluation changes. It is not a prompt fragment, an unverified research proposal, a guarantee, or a bypass around `govern`.

## Canonical locations

- Recipe catalog: `docs/recipes/`
- Authoring template: `docs/recipes/_template/RECIPE.md`
- New recipe: `docs/recipes/<recipe-id>/RECIPE.md`
- Catalog rules: `docs/recipes/README.md`
- Product contract: `docs/ADR.md` §5.14 and §7.17

Package-local copies may be generated later. Do not create a competing recipe source elsewhere.

## Non-negotiable rules

- Never promote a `RecipeProposal` from research directly into the catalog without curation.
- State an observable target effect and how it will be measured.
- Record mechanism, ingredients, applicability, conflicts, tradeoffs, failure modes, and evidence.
- Recipes may add validation checks but may not weaken Objective hard gates.
- Recipe application always uses the ordinary path: MissionBrief → Objective → admit → smoke → scale → measure → decide.
- Never treat recipe notes, research claims, or anecdotal success as a passed gate.
- Recipe instructions are versioned. Changing instructions requires a new recipe version.
- `## Recipe Notes` is append-only. Do not rewrite, reorder, or delete prior notes.
- Do not put secrets, raw private examples, identifying data, or private prompts in recipes or notes.

## When to retrieve recipes

Before inventing an intervention, retrieve relevant recipes and notes. Do this during:

- mission elicitation when clarifying the desired effect or tradeoffs
- training-method, data-mixture, interface, or serving selection
- smoke/scale interpretation and correction planning
- human-inbox reasoning after the human changes the target, constraints, or priorities
- post-run analysis, including failed and non-promoted attempts

When the facktry API exists, prefer:

1. `list_recipes` / `show_recipe`
2. `recommend_recipes` with the target effect, Objective context, open defects, and relevant constraints
3. `compose_recipe_stack` after reviewing conflicts, ordering, and validation requirements

Recommendations are read-only proposals. Record the selected and rejected candidates, material tradeoffs, and human decisions in MissionBrief or run provenance where applicable.

## Create a recipe

### 1. Establish the effect

Write the desired behavior as an observable effect, not a vague aspiration.

Good:

- “Increase warm, natural multi-turn dialogue while preserving factuality and refusal behavior.”
- “Improve agentic search query decomposition and evidence-grounded tool use without increasing unsupported claims.”

Also state what the recipe does not promise and which regressions are unacceptable.

### 2. Inspect prior knowledge

Before writing, inspect:

- the template and catalog rules
- related recipes and their notes
- open defects and recent Decisions
- research proposals and stable references
- the target Objective, baselines, budget, and interface pins

Do not duplicate an existing recipe. If the desired effect is a variation, create a new version or a clearly justified separate recipe.

### 3. Copy the template

Create the recipe directory and copy the template:

```text
mkdir -p docs/recipes/<recipe-id>
cp docs/recipes/_template/RECIPE.md docs/recipes/<recipe-id>/RECIPE.md
```

Use a stable lowercase kebab-case id. Set a real semantic version and use `draft` until the recipe has been reviewed. Do not mark a recipe `accepted` merely because it is complete; acceptance requires curation and evidence appropriate to the claimed effect.

### 4. Complete every section

Fill the template rather than deleting sections. At minimum, provide:

- **Front matter:** id, version, title, status, effects, observable measures, scope, requirements, conflicts
- **Effect:** success case, non-goals, and unacceptable regressions
- **Mechanism:** why the ingredients should create the effect
- **Ingredients:** data/source classes, mixture constraints, training method and safe ranges, parent/reference requirements, interface/serving changes, and evaluation suites
- **Procedure:** ordered existing facktry operations; include retrieval of related recipes and defects before intervention
- **Tradeoffs and failure modes:** including style bleed, over-specialization, retention drops, interface drift, and diminishing returns where relevant
- **Evidence and tested uses:** sources, runs, scorecards, Decisions, tested bases, and known failures
- **Recipe interactions:** compatible recipes, conflicts, ordering, and overlap resolution
- **Provenance:** curator, dates, proposal refs, artifact refs, and run refs
- **Recipe Notes:** leave the append-only section at the bottom

Use ranges and adaptation knobs where the recipe is portable. Do not present model-specific values as universal defaults.

### 5. Validate before cataloguing

Check that:

- the effect has a measurable target and paired baseline
- every ingredient maps to a governed facktry operation
- private-data and attribution rules are explicit
- the recipe does not assume hidden context or bypass admission
- conflicts and stack interactions are stated
- hard gates and no-regression checks are preserved
- evidence is linked to stable paper, code, artifact, scorecard, or Decision refs
- the file contains no secret or identifying material

A completed draft is still a draft. Ask for human curation when the recipe changes material behavior, gates, budget, privacy posture, or release composition.

## Update recipe notes

Append a note after a governed use, including a failed smoke, failed gate, hold, or non-promotion. Negative results are valuable recipe memory.

### 1. Verify the target version

Confirm the recipe id, instruction version, and instruction hash. Do not append a note to a different version or silently update instructions while recording an outcome.

### 2. Gather evidence

Use the run, Objective, RecipeStack, TrainCard, scorecard, Decision, and relevant defect refs. If no governed run exists, label the entry as an untested observation rather than measured evidence.

### 3. Append one structured entry

Add the entry at the bottom of `RECIPE.md`, after all prior notes:

```markdown
### YYYY-MM-DD — <run-id> — <short outcome>

- **Context:** Objective, base model, human decisions, and surrounding RecipeStack.
- **Change:** Parameters, adaptations, or interaction with other recipes.
- **Observed effect:** Measured target-effect result, or `not measured`.
- **Regression / failure:** What worsened, failed, or remained unknown.
- **Evidence:** Scorecard, Decision, TrainCard, artifact, or defect refs.
- **Recommendation:** Keep, alter, avoid, retire, or investigate.
- **Confidence:** low | medium | high
```

Use one note per meaningful use. Do not replace “failure” with “partial success” unless the evidence supports that interpretation.

### 4. Preserve instruction semantics

Appending a note must not change the recipe’s instructional body or its instruction hash. If the note reveals that the procedure, ingredients, constraints, or expected effect should change, create a new recipe version and link the prior version. Keep the note on the old version as historical evidence.

### 5. Feed the memory forward

After appending, make the outcome discoverable through the recipe catalog/store. Future `recommend_recipes` calls may use the note, but the note cannot satisfy a gate or authorize promotion. The next use must still run fresh paired measurement.

## Completion report

Report:

- recipe path and id/version
- whether this was a new recipe or an append-only note
- instruction hash and, when applicable, notes-head hash
- evidence refs and human-curation status
- any unresolved tradeoff, incompatibility, or missing measurement

Do not claim that a recipe creates its target effect until the cited evaluation demonstrates it.
