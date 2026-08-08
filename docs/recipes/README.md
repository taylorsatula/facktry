# Facktry recipes

A recipe is a versioned, evidence-backed specification for creating a named behavioral effect in a model stack. A recipe may combine data, training, prompt/interface, serving, and evaluation changes. It is not a guarantee, a prompt fragment, or a bypass around `govern`.

## Layout

Each curated recipe lives in its own directory:

```text
recipes/
├── README.md
├── _template/
│   └── RECIPE.md
└── <recipe-id>/
    └── RECIPE.md
```

`_template/` is not a catalog entry. The `RECIPE.md` file is human-readable source; the facktry parses it into a `Recipe` artifact when the catalog is available. The instructional body has a stable hash; notes are a separately hashed append-only stream.

## Research versus recipes

The isolated `research` worker produces a `RecipeProposal`: bounded evidence and candidate approaches. It does not automatically create or modify a curated recipe. A human or operator may promote a proposal into a reviewed `RECIPE.md`, preserving its references and limitations.

## Composition and compounding use

The operator is encouraged to retrieve recipes before every substantive intervention: initial planning, training-method selection, correction after a failed gate, and reasoning around human-inbox answers. `recommend_recipes` ranks candidates using the target effect, Objective constraints, open defects, notes, and prior outcomes.

The operator may select several compatible recipes into an immutable `RecipeStack`. The stack records exact recipe versions, ordering, parameter overrides, conflicts, and the resulting validation plan. Each governed run and resulting release records the stack hash.

After the run, the operator should append a structured use note—even for a failure or non-promotion—so later iterations inherit the experience. This creates compounding development memory: the facktry becomes better at selecting interventions without silently changing model weights or skipping fresh evaluation.

Recipes and stacks never skip mission elicitation, admission, smoke training, sealed measurement, decisions, or human promotion. Notes can influence future selection, but only cited measured evidence can satisfy gates.

## Notes

The `## Recipe Notes` section at the bottom of each recipe is append-only institutional memory. A note records a subsequent use, context, observed effect, regressions, evidence references, and recommendation. Editing the recipe's instructions requires a new recipe version; appending a note does not silently change the recipe's operational meaning.

Do not put secrets, raw private examples, or identifying data in recipe files or notes.
