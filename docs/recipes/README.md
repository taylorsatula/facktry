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

`_template/` is not a catalog entry. Each `RECIPE.md` is human-readable source parsed into a `Recipe` artifact. Instruction content—front matter and instructional sections—has an immutable instruction hash; notes are separately hashed append-only events.

## Research versus recipes

The isolated `research` worker produces a `RecipeProposal`: bounded evidence and candidate approaches. It never creates or modifies a curated recipe. A human curator may review a proposal into a versioned `RECIPE.md`, preserving its references and limitations.

## Retrieval and composition

Retrieve recipes at substantive interventions, including planning, training correction, and human-inbox reasoning. `recommend_recipes` ranks candidates from the target effect, Objective constraints, defects, notes, and prior outcomes.

Compose compatible candidates into an immutable `RecipeStack` containing exact recipe versions and hashes, ordering, resolved overrides, conflict decisions, allocation, and validation requirements. Record its hash on governed runs and releases, then append a structured use note—including failures and non-promotions—for future recommendations. Notes never replace fresh measurement or governance.

## Notes

`## Recipe Notes` is an append-only subsequent-use record. Each note records context, observed effect, regressions, evidence references, and recommendation. Changing instruction content requires a new recipe version; appending a note leaves the instruction hash and prior version's operational meaning unchanged.

Do not include secrets, private data—including raw examples or prompts—or identifying information in recipe files or notes.
