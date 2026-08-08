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

> **Definition:** A recipe is a versioned, evidence-backed specification for creating a named behavioral effect in a model stack.

## Effect

Describe the desired observable behavior. State what success looks like and what this recipe does **not** promise.

## Mechanism

Explain why the ingredients should create the effect. Identify whether the leverage is expected to come from data, training, prompt/interface, serving, or their combination.

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

Describe the ordered, governed steps for instantiating this recipe. This is a plan for existing facktry operations, not permission to bypass them.

0. Retrieve related recipes, defects, and prior use notes; record why this recipe or stack fits the target.
1. Prepare or generate ingredients.
2. Admit every persisted training artifact.
3. Run smoke training and its checks.
4. Run scale training only when govern allows it.
5. Measure the intended effect and regressions against pinned baselines.
6. Decide whether to keep, correct, hold, or retire the recipe use.

## Tradeoffs and failure modes

List likely regressions, style bleed, incompatibilities, diminishing returns, and known failure signatures. Link each important claim to evidence where possible.

## Evidence and tested uses

- Source papers, docs, code, or prior runs:
- Tested base models and interface hashes:
- Known successful configurations:
- Known unsuccessful configurations:

## Recipe interactions

Describe recipes this combines well with, conflicts with, or must follow. Explain how overlap is resolved when ingredients target the same behavior.

## Provenance

- Author / curator:
- Created:
- Last instruction change:
- Research proposal refs:
- Related artifact and run refs:

## Recipe Notes

Append notes; do not rewrite or delete earlier entries. Notes record experience using the recipe and do not change its instructions. Do not include secrets, raw private examples, or identifying data.

### <YYYY-MM-DD> — <run-id> — <short outcome>

- **Context:** Objective, base model, human decisions, and surrounding recipe stack.
- **Change:** Parameters or adaptations used.
- **Observed effect:** Measured result for the target effect.
- **Regression / failure:** What worsened or failed, if anything.
- **Evidence:** Scorecard, decision, or artifact refs.
- **Recommendation:** Keep, alter, avoid, or investigate.
- **Confidence:** low | medium | high
