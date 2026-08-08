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

Retrieve recipes at substantive interventions, including planning, training correction, and human-inbox reasoning. `recommend_recipes` ranks candidates from the target effect, Objective constraints, defects, notes, and prior outcomes.

Compose compatible candidates into an immutable `RecipeStack` containing exact versions, ordering, overrides, conflicts, and validation. Record its hash on governed runs and releases, then append a structured use note—including failures and non-promotions—for future recommendations. Notes never replace fresh measurement or governance.

## Notes

The `## Recipe Notes` section at the bottom of each recipe is append-only institutional memory. A note records a subsequent use, context, observed effect, regressions, evidence references, and recommendation. Editing the recipe's instructions requires a new recipe version; appending a note does not silently change the recipe's operational meaning.

Do not put secrets, raw private examples, or identifying data in recipe files or notes.
