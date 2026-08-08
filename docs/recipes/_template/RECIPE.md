---
id: <stable-kebab-case-id>
version: 0.1.0
title: <short effect name>
status: draft # draft | candidate | accepted | retired
effects:
  - id: <observable-effect>
    direction: increase # increase | decrease | preserve
    measure: <metric-or-suite-dimension>
scope:
  model_families: []
  domains: []
  interfaces: []
requires: []
conflicts: []
---

# Recipe: <effect name>

> Use the recipe contract in [`../README.md`](../README.md).

## Effect

Describe the observable target effect, its success measure, non-goals, and unacceptable regressions.

## Mechanism

Explain the mechanism and identify whether leverage comes from data, training, prompt/interface, serving, or a combination.

## Ingredients

### Data

- Sources and source classes:
- Required schemas or trajectory shapes:
- Mixture floors, caps, replay, and OOD quotas:
- Admission checks:

### Training

- Method:
- Parent/reference requirements:
- Default parameters and safe ranges:
- Adaptation knobs:

### Interface and serving

- Prompt policy:
- Tool/state schema:
- Decode profile:
- Guard or fallback changes:

### Evaluation

- Dev suites:
- Sealed suites:
- Paired baselines:
- Hard constraints and no-regression checks:

## Procedure

Describe the ordered, governed steps for instantiating this recipe. This sequence uses existing facktry operations and does not bypass them.

0. Retrieve related recipes, defects, and prior use notes; record why this recipe or stack fits the target.
1. Confirm the saved MissionBrief. Before freeze, resolve any RecipeStack into the Objective; for an existing run, confirm the frozen Objective and selected stack.
2. Prepare or generate ingredients; admit every persisted training artifact.
3. Run smoke training and its checks.
4. Run scale training only when the governed decision allows it.
5. Run paired sealed measurement against pinned baselines.
6. Decide whether to keep, correct, hold, or retire the recipe use.

## Tradeoffs and failure modes

List regressions, style bleed, incompatibilities, diminishing returns, and failure signatures. Link each material claim to a stable evidence reference; label unsupported mechanisms as hypotheses.

## Evidence and tested uses

- Source papers, docs, code, or prior runs:
- Tested base models and interface hashes:
- Measured successful configurations:
- Measured unsuccessful or inconclusive configurations:

## Recipe interactions

Describe compatible recipes, conflicts, required ordering, and overlap resolution when ingredients target the same behavior.

## Provenance

- Curator:
- Created:
- Last instruction change (not note append):
- Research proposal refs:
- Related artifact and run refs:

## Recipe Notes

Append notes below; do not rewrite, reorder, or delete prior entries. Notes do not change instruction content or its instruction hash. Do not include secrets, private data, or identifying information.

### <YYYY-MM-DD> — <run-id> — <short outcome>

- **Context:** Objective, base model, human decisions, and surrounding RecipeStack.
- **Change:** Parameters, adaptations, or interaction with other recipes.
- **Observed effect:** Measured target-effect result, or `not measured`.
- **Regression / failure:** What worsened, failed, or remained unknown.
- **Evidence:** Scorecard, Decision, TrainCard, artifact, or defect refs.
- **Recommendation:** Keep, alter, avoid, retire, or investigate.
- **Confidence:** low | medium | high
