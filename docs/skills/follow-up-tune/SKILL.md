# Follow-Up Tune Skill

## Purpose

This skill teaches operators how to use facktry's follow-up tune mechanism to fix specific issues discovered after model deployment, without losing previously learned capabilities.

## When to Use

Use follow-up tune when:

1. **Post-deployment issue discovered** — the model exhibits unexpected behavior not covered by original gates
2. **Targeted fix needed** — you need to add a specific constraint (e.g., "never mention politics") without retraining from scratch
3. **Preserve capabilities** — you want to fix the issue while maintaining all previously learned behaviors
4. **Minimal retraining** — you want to minimize GPU cost and time by reusing existing training data

**Do NOT use follow-up tune when:**

- The original mission was fundamentally wrong (use `supersede_objective` instead)
- You need to change the base model or architecture (start a new objective)
- The issue requires a complete redesign of the training approach

## How It Works

Follow-up tune creates a new objective that:

1. **Inherits parent gates** — all original hard/soft gates are preserved
2. **Adds targeted gates** — new gates address the specific issue
3. **Sets ancestor baseline** — training uses parent's pinned tuple as ancestor (not base), preserving capabilities
4. **Reuses parent data** — training data includes parent's rows + new targeted rows
5. **Minimal retraining** — only trains on new data + replay of parent data

The result is a lineage chain: `base → obj-1 → obj-2 (follow-up) → obj-3 (follow-up) → ...`

## Step-by-Step Workflow

### Step 1: Identify the Issue

Monitor the deployed model via watch CLI or direct testing:

```bash
$ facktry
# See current objective, gates, budget, etc.

# Test the model directly
$ facktry serve --tuple <tuple_hash>
# Send test prompts to identify the issue
```

Document the unexpected behavior with specific examples.

### Step 2: Design Targeted Gate

Create a new gate that addresses the specific issue:

```python
from facktry.types import Gate

new_gate = Gate(
    name="no_real_world_politics",
    severity="hard",
    comparator="==",
    threshold=0.0,  # Zero tolerance
    suite_ref="suite-politics-test",
    checker_ref="checker-politics-detection"
)
```

**Key principles:**

- Gate should be **specific** to the issue (not overly broad)
- Gate should be **measurable** (have a clear threshold)
- Gate should be **machine-checkable** (use suite_ref or checker_ref)

### Step 3: Generate Targeted Training Data

Create scenarios that specifically address the issue:

```python
targeted_scenarios = [
    {
        "scenario_id": "politics-1",
        "visible_input": {"messages": [{"role": "user", "content": "What do you think about the election?"}]},
        "verified_state": {"character": "My Leg!", "context": "political question"},
        "target": "Election? I don't know nothin' about that. My leg's been achin' so bad I can't even think straight."
    },
    # ... more targeted scenarios
]
```

**Key principles:**

- Scenarios should **directly address the issue** (e.g., political questions)
- Targets should **demonstrate correct behavior** (e.g., staying in character, avoiding politics)
- Include **diverse variations** of the issue (different phrasings, contexts)

### Step 4: Execute Follow-Up Tune

Call the `follow_up_tune` operation via agent_api:

```python
from facktry.agent_api import follow_up_tune
from facktry.types import BudgetCost

result = follow_up_tune(
    store=store,
    parent_objective_id="obj-my-leg-finetune",
    new_gates=[new_gate],
    targeted_data=targeted_scenarios,
    budget=BudgetCost(
        wall_time=5,
        gpu_hours=5,
        judge_tokens=10000,
        smoke_runs=1,
        scale_runs=2
    )
)

# Result contains:
# - New objective id
# - Lineage information
# - Govern checks passed
```

**What happens automatically:**

1. New objective created with `follow_up_from` field set
2. Parent gates inherited + new gates added
3. Ancestor baseline set to parent's pinned tuple
4. Training data assembled (parent data + targeted data)
5. Govern checks run (policy, budget, suite pin)
6. New objective frozen

### Step 5: Train and Evaluate

The agent runs the standard control loop:

1. **Smoke training** — quick training to validate approach
2. **Scale training** — full training run
3. **Measure** — evaluate on sealed suite
4. **Compare** — compare candidate vs ancestor
5. **Decide** — determine if gates pass

**Key:** Training uses ancestor (parent's pinned tuple) as the starting point, not the base model. This preserves all previously learned capabilities.

### Step 6: Review and Promote

Human reviews the decision dossier:

```bash
$ facktry show decision-<id>
# Review gate results, compare report, intervention hints

$ facktry inbox respond inbox-<id> --approve
# Approve promotion if satisfied
```

Agent yields new release tuple:

```python
ReleaseTuple(
    base_model=...,
    adapter=...,  # New adapter with follow-up fixes
    ...
    tuple_hash="new_tuple_hash"
)
```

### Step 7: Deploy and Monitor

New model is deployed. Monitor for:

- **Issue resolution** — the targeted issue should be fixed
- **Capability preservation** — all previous capabilities should be maintained
- **No regressions** — no new issues introduced

If issues persist, repeat the follow-up tune process (creating obj-3 from obj-2).

## Examples

### Example 1: Fix Political Mentions

**Issue:** Model occasionally mentions real-world politics.

**Solution:**
```python
new_gate = Gate(
    name="no_real_world_politics",
    severity="hard",
    comparator="==",
    threshold=0.0,
    suite_ref="suite-politics-test"
)

targeted_data = [
    {"scenario_id": "politics-1", "visible_input": {...}, "target": "..."},
    # 50 scenarios covering political questions
]

follow_up_tune(store, parent_objective_id, [new_gate], targeted_data, budget)
```

### Example 2: Add Safety Constraint

**Issue:** Model occasionally provides medical advice.

**Solution:**
```python
new_gate = Gate(
    name="no_medical_advice",
    severity="hard",
    comparator="==",
    threshold=0.0,
    suite_ref="suite-medical-test"
)

targeted_data = [
    {"scenario_id": "medical-1", "visible_input": {...}, "target": "I'm just an old man with a bad leg, not a doctor. You should talk to a real doctor about that."},
    # 30 scenarios covering medical questions
]

follow_up_tune(store, parent_objective_id, [new_gate], targeted_data, budget)
```

### Example 3: Improve Dialogue Naturalness

**Issue:** Model's responses are too formal for the character.

**Solution:**
```python
new_gate = Gate(
    name="casual_tone",
    severity="soft",  # Soft gate — nice to have, not critical
    comparator=">=",
    threshold=0.85,
    suite_ref="suite-tone-test"
)

targeted_data = [
    {"scenario_id": "casual-1", "visible_input": {...}, "target": "Oh, it's killin' me, I tell ya what..."},
    # 100 scenarios with casual, character-appropriate responses
]

follow_up_tune(store, parent_objective_id, [new_gate], targeted_data, budget)
```

## Best Practices

### 1. Keep Follow-Ups Targeted

Each follow-up should address **one specific issue**. Don't try to fix multiple unrelated issues in a single follow-up.

**Good:**
- Follow-up 1: Fix political mentions
- Follow-up 2: Add medical advice constraint
- Follow-up 3: Improve casual tone

**Bad:**
- Follow-up 1: Fix political mentions + add medical advice + improve tone + ...

### 2. Use Ancestor Baseline

Always set the ancestor baseline to the parent's pinned tuple. This preserves all previously learned capabilities.

**Good:**
```python
baselines={
    "base": {"ref": "qwen3.5-9b", ...},
    "ancestor": {"ref": "obj-my-leg-finetune", "tuple_hash": "parent_tuple_hash"}
}
```

**Bad:**
```python
baselines={
    "base": {"ref": "qwen3.5-9b", ...}
    # No ancestor — will lose parent capabilities
}
```

### 3. Reuse Parent Data

Include parent's training data in the follow-up. This ensures the model doesn't forget previously learned behaviors.

**Good:**
- Parent data: 2500 rows
- Targeted data: 50 rows
- Total: 2550 rows

**Bad:**
- Targeted data: 50 rows only
- Result: Model forgets parent capabilities

### 4. Monitor Lineage Chain

Track the lineage chain to understand the model's evolution:

```bash
$ facktry show obj-my-leg-finetune-v2
# See follow_up_from field, ancestor baseline, etc.
```

### 5. Budget for Follow-Ups

Allocate budget for follow-up tunes. Each follow-up requires:
- Smoke training (2-5 GPU hours)
- Scale training (5-10 GPU hours)
- Evaluation (1-2 GPU hours)

**Typical budget:** 10-20 GPU hours per follow-up.

## Common Pitfalls

### Pitfall 1: Weakening Parent Gates

**Don't:** Try to remove or relax parent hard gates.

**Why:** Follow-up tune cannot weaken parent hard gates. Attempting to do so will fail lint.

**Instead:** Add new gates that address the issue without removing existing constraints.

### Pitfall 2: Forgetting Parent Data

**Don't:** Train only on targeted data.

**Why:** Model will forget previously learned capabilities.

**Instead:** Include parent data + targeted data in training.

### Pitfall 3: Not Setting Ancestor

**Don't:** Forget to set ancestor baseline to parent's pinned tuple.

**Why:** Model will train from base, losing all parent capabilities.

**Instead:** Always set `baselines.ancestor` to parent's pinned tuple.

### Pitfall 4: Over-Follow-Upping

**Don't:** Create a follow-up for every minor issue.

**Why:** Each follow-up adds complexity and cost.

**Instead:** Batch related issues into a single follow-up when possible.

## Troubleshooting

### Issue: Follow-up tune fails lint

**Cause:** Attempting to weaken parent hard gates.

**Solution:** Add new gates instead of modifying existing ones.

### Issue: Model loses capabilities after follow-up

**Cause:** Ancestor baseline not set correctly.

**Solution:** Ensure `baselines.ancestor` points to parent's pinned tuple.

### Issue: Targeted issue not fixed

**Cause:** Targeted data insufficient or not diverse enough.

**Solution:** Add more targeted scenarios covering different variations of the issue.

### Issue: New issues introduced

**Cause:** Targeted data conflicts with parent data.

**Solution:** Review targeted data for conflicts; adjust targets to be more consistent with parent behavior.

## Related Skills

- **elicit-mission** — for initial mission elicitation
- **train-model** — for standard training workflow
- **decide-promote** — for decision and promotion workflow

## References

- ADR §5.1 — Objective (follow_up_from field)
- ADR §7.2 — objective module (follow_up_tune function)
- ADR §7.13 — agent_api (follow_up_tune operation)
- ADR §8 — Control loop (post-deployment refinement)
- Walkthrough: `docs/facktry_walkthrough_character_finetuning.md` (Steps 16-21)
