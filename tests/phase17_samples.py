"""Non-sensitive Phase 17 Markdown and domain-pack fixtures."""

VALID_RECIPE = """---
id: grounded-responses
version: 1.0.0
title: Grounded responses
status: draft
effects:
  - id: grounding
    direction: increase
    measure: grounding_rate
scope:
  model_families: [test]
  domains: [test]
  interfaces: [chat]
requires: []
conflicts: []
---

# Recipe: Grounded responses

## Effect
Increase grounded answers measured by grounding_rate. Do not increase unsupported claims.

## Mechanism
Visible evidence constrains target construction through data and verification.

## Ingredients

### Data
- Sources and source classes: synthetic
- Required schemas or trajectory shapes: dialogue rows
- Mixture floors, caps, replay, and OOD quotas: replay floor 1
- Admission checks: schema and attribution

### Training
- Method: sft
- Parent/reference requirements: frozen base
- Default parameters and safe ranges: low learning rate
- Adaptation knobs: mixture allocation

### Interface and serving
- Prompt policy: grounded prompt policy
- Tool/state schema: empty tools
- Decode profile: deterministic
- Guard or fallback changes: claim guard

### Evaluation
- Dev suites: suite-dev
- Sealed suites: suite-seal
- Paired baselines: base
- Hard constraints and no-regression checks: task floor

## Procedure
1. Retrieve relevant recipes and defects.
2. Confirm the MissionBrief and Objective.
3. Admit every persisted ingredient.
4. Run smoke and scale only when governed.
5. Measure against paired sealed baselines.
6. Decide and record the outcome.

## Tradeoffs and failure modes
May reduce unsupported fluency. Failure signature is hidden-context leakage. Evidence: artifact:evidence-1.

## Evidence and tested uses
- Source papers, docs, code, or prior runs: paper:1
- Tested base models and interface hashes: base:1
- Measured successful configurations: scorecard:1
- Measured unsuccessful or inconclusive configurations: none

## Recipe interactions
Compatible with replay. Conflicts with unsupported-claim suppression. Required ordering: admit before train.

## Provenance
- Curator: human-1
- Created: 2026-08-08
- Last instruction change (not note append): 2026-08-08
- Research proposal refs: paper:1
- Related artifact and run refs: artifact:evidence-1

## Recipe Notes

### 2026-08-08 — run-1 — Initial use

- **Context:** Objective objective-valid, base base-1, human decision retained grounding.
- **Change:** Added replay allocation.
- **Observed effect:** grounding_rate increased.
- **Regression / failure:** none observed.
- **Evidence:** scorecard:1.
- **Recommendation:** Keep.
- **Confidence:** medium
"""


def write_recipe(root, content=VALID_RECIPE, recipe_id="grounded-responses"):
    path = root / recipe_id / "RECIPE.md"
    path.parent.mkdir(parents=True)
    path.write_text(content)
    return path


class FixtureDomain:
    name = "fixture"
    elicitation_branches = {"default": ["success_case"]}
    required_brief_sections = ["success_case"]
    schemas = {"label": ["a", "b"]}
    controlled_vocabs = {"label": {"a", "b"}}
    generators = {}
    filters = {}
    labelers = {}
    stratifiers = {}
    suite_case_providers = {}
    oracles = {}
    prompt_policies = {"default": "prompt-1"}
    tool_schemas = {"default": "tools-1"}

    def stages(self):
        return {"fixture_stage": self.run_fixture_stage}

    def run_fixture_stage(self, spec):
        return {"stage": "fixture_stage", "value": spec.get("value", "ok")}
