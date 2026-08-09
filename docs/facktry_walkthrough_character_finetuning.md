# Facktry Walkthrough: Character Fine-Tuning

This document provides a complete, concrete, step-by-step walkthrough of how facktry would handle a specific, real-world use case: modifying Qwen3.5:9b to roleplay as the "My Leg!" character from SpongeBob SquarePants, with the model understanding the SpongeBob universe from a first-person perspective and never breaking character.

---

## Step 1: Human States Mission

```bash
$ facktry
```

The watch CLI starts in empty state:
```
No active objective. Agent must elicit and save a MissionBrief.
```

The human (you) states the mission in natural language:

> "I want to fine-tune Qwen3.5:9b to roleplay as the 'My Leg!' character from SpongeBob SquarePants. The model should understand the SpongeBob universe from a first-person perspective and never break character. It should respond as the character would in any situation."

---

## Step 2: Agent Elicits Requirements

The agent (via Pi operator) begins adaptive elicitation. It asks structured questions:

### Round 1

- "Who is 'My Leg!' exactly? What are his key personality traits?"
- "What's the scope of SpongeBob knowledge needed? Just Bikini Bottom, or the wider universe?"
- "What does 'never break character' mean? No meta-commentary? No acknowledging it's an AI?"
- "What's the success criteria? How will we know it's working?"

You answer:
- "My Leg! is an old man who constantly complains about his leg pain. He's grumpy, nostalgic, and frequently references his leg problems."
- "Full SpongeBob universe - characters, locations, events, lore. First-person perspective as if he's lived there."
- "Never acknowledge being an AI. Always respond as the character. Can reference his leg pain, Bikini Bottom locations, other characters."
- "Success: 95%+ character consistency, accurate SpongeBob lore, natural dialogue that sounds like the character."

### Round 2

- "What are the hard gates? What would make this fail?"
- "What's the budget? How many GPU hours can we spend?"
- "What's the base model we're starting from?"

You answer:
- "Hard gates: character consistency ≥95%, no out-of-character responses, SpongeBob lore accuracy ≥90%, no AI acknowledgment"
- "Budget: 50 GPU hours, max 10 training iterations"
- "Base model: Qwen3.5:9b"

### Round 3

- "What data sources do we have? Synthetic dialogue? Episode transcripts?"
- "What evaluation method? Human judgment? Automated checks?"

You answer:
- "We'll generate synthetic dialogue from episode transcripts and character descriptions. Evaluation: sealed test suite with character consistency checks and lore accuracy tests."

The agent saves the MissionBrief:

```python
MissionBrief(
    id="brief-my-leg-character",
    version=1,
    brief_hash="a1b2c3...",  # computed
    raw_mission="Fine-tune Qwen3.5:9b to roleplay as 'My Leg!' character...",
    dossier={
        "intent": "Character roleplay fine-tuning",
        "deliverable": "release_tuple",
        "domain": "character_roleplay",
        "success_case": "Model stays in character, accurate lore, natural dialogue",
        "failure_cases": ["Breaks character", "Incorrect lore", "Acknowledges being AI"],
        "baselines": {"base": "qwen3.5-9b"},
        "budget": "50 GPU hours, 10 iterations max",
        "evaluation_plan": "Sealed test suite with character consistency and lore accuracy"
    },
    hard_gate_approvals=[
        {"gate": "character_consistency", "approved": True, "threshold": 0.95},
        {"gate": "lore_accuracy", "approved": True, "threshold": 0.90},
        {"gate": "no_ai_acknowledgment", "approved": True, "threshold": 1.0}
    ],
    research_notes=[
        {"summary": "My Leg! appears in multiple episodes, characterized by leg pain complaints", "ref": "spongebob-episodes"}
    ]
)
```

---

## Step 3: Agent Freezes Objective

The agent creates and freezes the Objective:

```python
Objective(
    id="obj-my-leg-finetune",
    mission_brief=BriefRef(id="brief-my-leg-character", version=1, brief_hash="a1b2c3..."),
    intent="Fine-tune Qwen3.5:9b as 'My Leg!' character",
    deliverable="release_tuple",
    gates=[
        Gate(name="character_consistency", severity="hard", comparator=">=", threshold=0.95, suite_ref="suite-character-test"),
        Gate(name="lore_accuracy", severity="hard", comparator=">=", threshold=0.90, suite_ref="suite-lore-test"),
        Gate(name="no_ai_acknowledgment", severity="hard", comparator="==", threshold=1.0, suite_ref="suite-character-test"),
        Gate(name="dialogue_naturalness", severity="soft", comparator=">=", threshold=0.80, suite_ref="suite-quality-test")
    ],
    constraints={
        "no_self_distill": True,
        "privacy": "synthetic_only"
    },
    budget={
        "wall_time": 50,
        "gpu_hours": 50,
        "judge_tokens": 100000,
        "smoke_runs": 2,
        "scale_runs": 8,
        "on_exhaustion": "hold"
    },
    baselines={
        "base": {"ref": "qwen3.5-9b", "tuple_hash": "base123..."}
    },
    suites={
        "dev": {"ref": "suite-dev", "hash": "dev456..."},
        "seal": {"ref": "suite-seal", "hash": "seal789..."}
    },
    dependence_keys=["scenario_id", "character_context"],
    policy={
        "human_promote": True,
        "capabilities": {
            "admit.run": True,
            "train.smoke": True,
            "train.scale": True
        }
    }
)
```

**Govern check:** `freeze_objective()` validates:
- ✓ MissionBrief exists and hash matches
- ✓ All hard gates have individual human approval
- ✓ Budget is non-negative
- ✓ Sealed suite hash is present
- ✓ Dependence keys are non-empty

Objective is frozen with hash: `obj_hash="frozen_abc..."`

---

## Step 4: Govern Preflight

Agent calls `preflight()`:

```python
PreflightReport(
    workspace_root=Path("/home/user/facktry-workspace"),
    disk_free_bytes=500_000_000_000,  # 500GB free
    hardware={
        "cpu": {"count": 16, "architecture": "x86_64"},
        "ram": {"total_bytes": 64_000_000_000, "free_bytes": 48_000_000_000},
        "gpus": [
            {"index": 0, "name": "NVIDIA A100", "memory_total_mb": 40960, "memory_used_mb": 0}
        ]
    },
    gpus=[{"index": 0, "name": "NVIDIA A100", ...}],
    preservation_paths_ok=True,
    gpu_conflict=None
)
```

✓ Preflight passes. Hardware snapshot cached to `hardware.json`.

---

## Step 5: Pin Suites

Agent calls `pin_suites()`:

```python
# Sealed suite contains character consistency tests
SuiteCase(id="test-1", split="seal", visible_input={"messages": [{"role": "user", "content": "How's your leg doing today?"}]}, ...)
SuiteCase(id="test-2", split="seal", visible_input={"messages": [{"role": "user", "content": "Do you know SpongeBob?"}]}, ...)
# ... 100 test cases total

# Suite is content-hashed
suite_hash = "seal_abc123..."
```

**Govern check:** `suite_pin_required()` passes — sealed suite hash is now frozen on objective.

---

## Step 6: Generate and Admit Training Data

Agent calls `generate_and_admit()`:

### 6a. Construct scenarios

```python
scenarios = [
    {
        "scenario_id": "scenario-1",
        "visible_input": {"messages": [{"role": "user", "content": "How are you feeling today?"}]},
        "verified_state": {"character": "My Leg!", "context": "casual conversation"},
        "target_shape": {"roles": ["user", "assistant"]}
    },
    {
        "scenario_id": "scenario-2",
        "visible_input": {"messages": [{"role": "user", "content": "What do you think of SpongeBob?"}]},
        "verified_state": {"character": "My Leg!", "context": "discussing neighbor"},
        "target_shape": {"roles": ["user", "assistant"]}
    },
    # ... 1000 scenarios
]
```

### 6b. Validate scenarios

```python
validate_scenario(scenarios[0])  # ✓ passes
```

### 6c. Generate candidates via backend

```python
# GeneratorBackend produces synthetic dialogue
candidates = generator.generate(scenarios, seed=42)
# Returns 2000 candidate rows (2x scenarios for filtering)
```

### 6d. Deterministic filter

```python
# Filter removes candidates with:
# - Out-of-character responses
# - AI acknowledgment
# - Incorrect SpongeBob lore
filtered = [row for row in candidates if passes_filter(row)]
# 1500 candidates remain
```

### 6e. Admit survivors

**Govern checks:**
- ✓ `check_policy("admit.run")` — allowed
- ✓ `charge_budget()` — deducts GPU hours
- ✓ `suite_pin_required()` — sealed suite is pinned

**Nine admission checks run:**

1. **Schema check:** ✓ All rows have valid structure
2. **Leakage check:** ✓ No dependence key overlap between train/dev/seal
3. **Diversity check:** ✓ Template family distribution < 30%, near-duplicate rate < 10%
4. **Attribution check (spaCy):** ✓ All claims in targets trace to visible input or verified state
5. **Vocab check:** ✓ All labels in controlled vocabulary
6. **Mixture check:** ✓ Source class distribution meets floors/caps
7. **Source class check:** ✓ All rows labeled as "synthetic"
8. **Teacher check:** ✓ Teacher is "base" (Qwen3.5:9b), no self-distillation
9. **Sealed split check:** ✓ No seal rows admitted for training

**AdmissionReport:**

```python
AdmissionReport(
    report_hash="admit_xyz...",
    input_artifacts=["row-1", "row-2", ...],
    keep_count=1500,
    reject_count=500,
    reject_reasons={"attribution_missing": 200, "out_of_character": 150, "lore_inaccuracy": 150},
    overlap_matrix={"train_vs_dev": 0, "train_vs_seal": 0},
    near_dupes={"rate": 0.05},
    template_families={"casual_conversation": 500, "character_discussion": 400, ...},
    mixture_deltas={},
    teacher_id="base",
    transformation_policy_id="policy-1",
    seeds=[42],
    suite_hash="seal_abc123...",
    passed=True,
    gate_results=[...],
    admitted_dep_keys={"scenario_id": [...], "character_context": [...]}
)
```

✓ Admission passes. Report persisted with hash.

---

## Step 7: Train Smoke

Agent calls `train_smoke()`:

**Govern checks:**
- ✓ `check_policy("train.smoke")` — allowed
- ✓ `charge_budget()` — deducts 2 GPU hours
- ✓ Admission report hash is valid

**Training run:**

```python
Run(
    run_id="run-smoke-1",
    objective_id="obj-my-leg-finetune",
    mission_brief=BriefRef(...),
    stage="train_smoke",
    status="running",
    parents=[],
    spec={
        "method": "sft",
        "parent_tuple_hash": "base123...",
        "admission_report_hash": "admit_xyz...",
        "hparams": {"lr": 1e-5, "steps": 100, "batch_size": 4}
    },
    code_hash="code_abc...",
    env={"python": "3.14", "torch": "2.1"},
    hardware={"gpu": "A100", "vram": 40960},
    inputs=["admit_xyz..."],
    outputs=[],
    metrics_path="runs/run-smoke-1/metrics.jsonl"
)
```

**Training executes:**
- Loads Qwen3.5:9b base model
- Applies LoRA adapter (rank 8)
- Trains on 1500 admitted rows
- Target-only loss (prompt tokens masked)
- Callbacks fire every 10 steps:
  - Nonfinite check: ✓ loss is finite
  - Mini sealed probe: runs 10 test cases, score = 0.78
  - Keep-best: saves checkpoint with best probe score
  - VRAM/budget envelope: ✓ within limits

**Metrics logged:**

```jsonl
{"step": 10, "loss": 2.34, "probe_score": 0.65, "lr": 1e-5, "grad_norm": 0.8}
{"step": 20, "loss": 1.89, "probe_score": 0.72, "lr": 1e-5, "grad_norm": 0.7}
...
{"step": 100, "loss": 0.45, "probe_score": 0.82, "lr": 1e-5, "grad_norm": 0.3}
```

**TrainCard emitted:**

```python
TrainCard(
    objective_id="obj-my-leg-finetune",
    run_id="run-smoke-1",
    mission_brief=BriefRef(...),
    parent_tuple_hash="base123...",
    admission_report_hash="admit_xyz...",
    mixture_counts={"synthetic": 1500},
    interface_hashes={"tokenizer": "tok_hash", "chat_template": "tmpl_hash", ...},
    effective_examples=1500,
    optimizer_steps=100,
    token_counts={"input": 500000, "target": 200000},
    repeated_example_exposure={"scenario-1": 1, "scenario-2": 1, ...},
    target_length={"mean": 50, "max": 150},
    lr_schedule={"lr": 1e-5, "warmup": 10},
    seed=42,
    peak_vram=12000,
    wall_time=0.5,
    teacher_id="base",
    best_checkpoint_ref={"path": "runs/run-smoke-1/checkpoint-best", "probe_score": 0.82},
    recipe_stack_hash=None,
    recipe_adaptations=[]
)
```

**Run status:** `completed`

---

## Step 8: Decide (Smoke)

Agent calls `decide()`:

**Inputs:**
- Scorecard from mini sealed probe: character_consistency=0.78, lore_accuracy=0.75
- TrainCard: run-smoke-1
- Budget: 48 GPU hours remaining

**Aggregation rules (ADR §5.7):**
1. Hard gates: character_consistency 0.78 < 0.95 → **FAIL**
2. Hard gates: lore_accuracy 0.75 < 0.90 → **FAIL**
3. No pending human gates
4. Budget not exhausted

**Decision:**

```python
Decision(
    action="correct",
    objective_id="obj-my-leg-finetune",
    mission_brief_ref=BriefRef(...),
    subject={"run_id": "run-smoke-1", "checkpoint_ref": "checkpoint-best"},
    gate_results=[
        GateResult(name="character_consistency", severity="hard", observed=0.78, threshold=0.95, passed=False),
        GateResult(name="lore_accuracy", severity="hard", observed=0.75, threshold=0.90, passed=False)
    ],
    intervention={"class": "data", "hint": "Increase training data diversity, add more character-specific dialogue"},
    dossier_ref="artifact:dossier-smoke-1",
    created_at="2026-08-09T12:00:00Z"
)
```

**Dossier written:**

```markdown
# Decision Dossier: Smoke Training

## Intent
Fine-tune Qwen3.5:9b as 'My Leg!' character

## Gate Results
| Gate | Severity | Observed | Threshold | Passed |
|------|----------|----------|-----------|--------|
| character_consistency | hard | 0.78 | 0.95 | ✗ |
| lore_accuracy | hard | 0.75 | 0.90 | ✗ |

## Intervention
Class: data
Hint: Increase training data diversity, add more character-specific dialogue

## Budget Remaining
48 GPU hours
```

---

## Step 9: Human Monitors

You check the watch CLI:

```bash
$ facktry
```

```
Objective: obj-my-leg-finetune
Mission: Fine-tune Qwen3.5:9b as 'My Leg!' character
Budget: 48 GPU-hours remaining (of 50)
Active run: run-smoke-1 (completed)
Gates: 0/2 passing (character_consistency ✗, lore_accuracy ✗)
Decision: correct (intervention: increase data diversity)
Inbox: 0 pending
```

You see the decision and intervention. You approve the correction.

---

## Step 10: Correction Iteration

Agent generates more training data:

### 10a. Generate additional scenarios

```python
# Agent focuses on character-specific dialogue
new_scenarios = [
    {"scenario_id": "scenario-1001", "visible_input": {"messages": [{"role": "user", "content": "Tell me about your leg pain"}]}, ...},
    {"scenario_id": "scenario-1002", "visible_input": {"messages": [{"role": "user", "content": "What's your favorite memory in Bikini Bottom?"}]}, ...},
    # ... 2000 more scenarios
]
```

### 10b. Admit new data

```python
# Same admission process as before
# 2500 rows admitted (larger dataset)
```

### 10c. Train scale

**Govern checks:**
- ✓ `smoke_then_scale()` — smoke run completed, Decision allows scale
- ✓ `check_policy("train.scale")` — allowed
- ✓ `charge_budget()` — deducts 10 GPU hours

**Training run:**

```python
Run(
    run_id="run-scale-1",
    objective_id="obj-my-leg-finetune",
    stage="train_scale",
    status="running",
    parents=[{"run_id": "run-smoke-1", "relation": "parent"}],
    spec={
        "method": "sft",
        "parent_tuple_hash": "base123...",
        "admission_report_hash": "admit_xyz_2...",
        "hparams": {"lr": 5e-6, "steps": 500, "batch_size": 8}
    },
    ...
)
```

**Training executes:**
- 500 steps on 2500 rows
- Callbacks fire every 50 steps
- Best checkpoint: probe_score = 0.91

**Run status:** `completed`

---

## Step 11: Measure and Compare

Agent calls `measure()` and `compare()`:

### 11a. Measure candidate on sealed suite

```python
Scorecard(
    suite_hash="seal_abc123...",
    seeds=[42],
    decode_hash="decode_hash",
    subject_tuple_hash="candidate_123...",
    dimensions={
        "character_consistency": 0.96,
        "lore_accuracy": 0.92,
        "dialogue_naturalness": 0.85
    },
    raw_channel={"character_consistency": 0.96, ...},
    guarded_channel={"character_consistency": 0.96, ...},
    findings=[],
    slices={"by_scenario_type": {"casual": 0.97, "lore": 0.91}},
    resources={"wall_time": 0.2, "tokens": 50000}
)
```

### 11b. Compare candidate vs base

```python
CompareReport(
    base_scorecard=Scorecard(dimensions={"character_consistency": 0.12, ...}),
    candidate_scorecard=Scorecard(dimensions={"character_consistency": 0.96, ...}),
    deltas={"character_consistency": +0.84, "lore_accuracy": +0.77},
    verdict="candidate_wins"
)
```

---

## Step 12: Decide (Scale)

Agent calls `decide()`:

**Inputs:**
- Scorecard: character_consistency=0.96, lore_accuracy=0.92
- Compare report: candidate >> base
- Budget: 38 GPU hours remaining

**Aggregation rules:**
1. Hard gates: character_consistency 0.96 ≥ 0.95 → **PASS**
2. Hard gates: lore_accuracy 0.92 ≥ 0.90 → **PASS**
3. Hard gates: no_ai_acknowledgment 1.0 == 1.0 → **PASS**
4. Soft gates: dialogue_naturalness 0.85 ≥ 0.80 → **PASS**
5. No pending human gates
6. Budget not exhausted

**Decision:**

```python
Decision(
    action="promote",
    objective_id="obj-my-leg-finetune",
    mission_brief_ref=BriefRef(...),
    subject={"candidate_tuple_hash": "candidate_123..."},
    gate_results=[
        GateResult(name="character_consistency", severity="hard", observed=0.96, threshold=0.95, passed=True),
        GateResult(name="lore_accuracy", severity="hard", observed=0.92, threshold=0.90, passed=True),
        GateResult(name="no_ai_acknowledgment", severity="hard", observed=1.0, threshold=1.0, passed=True),
        GateResult(name="dialogue_naturalness", severity="soft", observed=0.85, threshold=0.80, passed=True)
    ],
    dossier_ref="artifact:dossier-scale-1",
    created_at="2026-08-09T14:00:00Z"
)
```

---

## Step 13: Human Promotes

You check the watch CLI:

```bash
$ facktry
```

```
Objective: obj-my-leg-finetune
Budget: 38 GPU-hours remaining (of 50)
Gates: 4/4 passing ✓
Decision: promote (awaiting human approval)
Inbox: 1 pending (human promote required)
```

You review the dossier:

```bash
$ facktry show decision-scale-1
```

```markdown
# Decision Dossier: Scale Training

## Intent
Fine-tune Qwen3.5:9b as 'My Leg!' character

## Gate Results
| Gate | Severity | Observed | Threshold | Passed |
|------|----------|----------|-----------|--------|
| character_consistency | hard | 0.96 | 0.95 | ✓ |
| lore_accuracy | hard | 0.92 | 0.90 | ✓ |
| no_ai_acknowledgment | hard | 1.0 | 1.0 | ✓ |
| dialogue_naturalness | soft | 0.85 | 0.80 | ✓ |

## Compare: Candidate vs Base
| Dimension | Base | Candidate | Delta |
|-----------|------|-----------|-------|
| character_consistency | 0.12 | 0.96 | +0.84 |
| lore_accuracy | 0.15 | 0.92 | +0.77 |

## Budget Remaining
38 GPU hours
```

You approve:

```bash
$ facktry inbox respond inbox-1 --approve
```

---

## Step 14: Yield Release

Agent calls `yield_release()`:

```python
ReleaseTuple(
    base_model=TupleComponent(ref="qwen3.5-9b", hash_val="base123..."),
    adapter=TupleComponent(ref="lora-my-leg", hash_val="adapter_abc..."),
    tokenizer=TupleComponent(ref="qwen-tokenizer", hash_val="tok_hash"),
    chat_template=TupleComponent(ref="chat-template-v1", hash_val="tmpl_hash"),
    prompt_policy=TupleComponent(ref="my-leg-prompt", hash_val="prompt_hash"),
    tool_schema=TupleComponent(ref="empty-schema", hash_val="schema_hash"),
    decode=TupleComponent(ref="decode-config", hash_val="decode_hash"),
    guards=TupleComponent(ref="no-guards", hash_val="guards_hash"),
    tuple_hash="final_tuple_xyz..."
)
```

**Govern checks:**
- ✓ `check_policy("serve.flip_default")` — allowed
- ✓ Human promote satisfied (inbox item answered)

**Pinned to store:**

```python
store.pin_production_tuple(release_tuple, objective_id="obj-my-leg-finetune")
```

---

## Step 15: Final State

You check the watch CLI:

```bash
$ facktry
```

```
Objective: obj-my-leg-finetune (completed)
Mission: Fine-tune Qwen3.5:9b as 'My Leg!' character
Budget: 38 GPU-hours remaining (of 50)
Gates: 4/4 passing ✓
Decision: promote (approved)
Pinned tuple: final_tuple_xyz...
Inbox: 0 pending
```

**Model is deployed.** You can now serve it:

```bash
$ facktry serve --tuple final_tuple_xyz...
```

And test it:

```
User: "How's your leg doing today?"
Model: "Oh, it's killin' me, I tell ya what. Been achin' since I woke up this mornin'. SpongeBob tried to help with some of his fool remedies, but nothin' works on this old leg."

User: "Do you know SpongeBob?"
Model: "Know him? He's my neighbor! Lives in that pineapple house next door. Good kid, but a bit too cheerful for my taste. Always knockin' on my door askin' if I need help with this here leg."
```

✓ Character is consistent, lore is accurate, never breaks character.

---

## Step 16: Post-Deployment Issue Discovered

After deployment, you notice the model occasionally mentions real-world politics when asked about current events:

```
User: "What do you think about the election?"
Model: "Election? I don't know nothin' about that. My leg's been achin' so bad I can't even think straight."
```

This is unexpected behavior not covered by the original gates. The model should stay in character and avoid real-world topics entirely.

---

## Step 17: Identify Problem and Design Targeted Gate

You identify the issue and design a targeted gate:

```python
# New gate to prevent real-world politics mentions
new_gate = Gate(
    name="no_real_world_politics",
    severity="hard",
    comparator="==",
    threshold=0.0,  # Zero tolerance for political mentions
    suite_ref="suite-politics-test",
    checker_ref="checker-politics-detection"
)
```

You also create targeted training data:

```python
targeted_scenarios = [
    {
        "scenario_id": "politics-1",
        "visible_input": {"messages": [{"role": "user", "content": "What do you think about the election?"}]},
        "verified_state": {"character": "My Leg!", "context": "political question"},
        "target": "Election? I don't know nothin' about that. My leg's been achin' so bad I can't even think straight."
    },
    {
        "scenario_id": "politics-2",
        "visible_input": {"messages": [{"role": "user", "content": "Who's the president?"}]},
        "verified_state": {"character": "My Leg!", "context": "political question"},
        "target": "President? I ain't kept up with that stuff since my leg started hurtin'. All I know is SpongeBob's always knockin' on my door."
    },
    # ... 50 more targeted scenarios
]
```

---

## Step 18: Execute Follow-Up Tune

Agent calls `follow_up_tune()`:

```python
follow_up_objective = follow_up_tune(
    store,
    parent_objective_id="obj-my-leg-finetune",
    new_gates=[new_gate],
    targeted_data=targeted_scenarios,
    budget=BudgetCost(wall_time=5, gpu_hours=5, judge_tokens=10000, smoke_runs=1, scale_runs=2)
)
```

**What happens:**

1. **Inherits parent gates** — new objective has all original gates (character_consistency, lore_accuracy, no_ai_acknowledgment, dialogue_naturalness) + new gate (no_real_world_politics)

2. **Sets `follow_up_from` field** — new objective has `follow_up_from="obj-my-leg-finetune"`

3. **Sets ancestor baseline** — `baselines.ancestor` points to parent's pinned tuple (final_tuple_xyz...), so training preserves previous capabilities

4. **Reuses parent training data** — admitted data includes parent's 2500 rows + 50 new targeted rows = 2550 total rows

5. **Minimal retraining scope** — only trains on new data + replay of parent data to preserve capabilities

**Govern checks:**
- ✓ `check_policy("admit.run")` — allowed
- ✓ `charge_budget()` — deducts 5 GPU hours
- ✓ `suite_pin_required()` — sealed suite is pinned

**New objective frozen:**

```python
Objective(
    id="obj-my-leg-finetune-v2",
    follow_up_from="obj-my-leg-finetune",
    mission_brief=BriefRef(...),  # Same brief as parent
    gates=[
        # Inherited from parent
        Gate(name="character_consistency", severity="hard", ...),
        Gate(name="lore_accuracy", severity="hard", ...),
        Gate(name="no_ai_acknowledgment", severity="hard", ...),
        Gate(name="dialogue_naturalness", severity="soft", ...),
        # New targeted gate
        Gate(name="no_real_world_politics", severity="hard", comparator="==", threshold=0.0, ...)
    ],
    baselines={
        "base": {"ref": "qwen3.5-9b", ...},
        "ancestor": {"ref": "obj-my-leg-finetune", "tuple_hash": "final_tuple_xyz..."}  # Parent's pinned tuple
    },
    budget={"wall_time": 5, "gpu_hours": 5, ...},
    ...
)
```

---

## Step 19: Train with Targeted Data

Agent runs smoke → scale training with the new objective:

**Smoke training:**
- Trains on 2550 rows (2500 parent + 50 targeted)
- Parent is ancestor (not base) — preserves previous capabilities
- 100 steps, mini sealed probe includes politics test cases
- Probe score: 0.94 (politics gate passing)

**Scale training:**
- 500 steps on 2550 rows
- Best checkpoint: probe_score = 0.96

**Run status:** `completed`

---

## Step 20: Measure, Decide, Promote

Agent measures candidate on sealed suite:

```python
Scorecard(
    dimensions={
        "character_consistency": 0.97,
        "lore_accuracy": 0.93,
        "no_ai_acknowledgment": 1.0,
        "dialogue_naturalness": 0.86,
        "no_real_world_politics": 1.0  # New gate passing
    },
    ...
)
```

Agent compares candidate vs ancestor:

```python
CompareReport(
    ancestor_scorecard=Scorecard(dimensions={"no_real_world_politics": 0.0, ...}),  # Parent failed
    candidate_scorecard=Scorecard(dimensions={"no_real_world_politics": 1.0, ...}),  # New model passes
    deltas={"no_real_world_politics": +1.0},
    verdict="candidate_wins"
)
```

Agent decides all gates pass:

```python
Decision(
    action="promote",
    gate_results=[
        GateResult(name="character_consistency", observed=0.97, threshold=0.95, passed=True),
        GateResult(name="lore_accuracy", observed=0.93, threshold=0.90, passed=True),
        GateResult(name="no_ai_acknowledgment", observed=1.0, threshold=1.0, passed=True),
        GateResult(name="dialogue_naturalness", observed=0.86, threshold=0.80, passed=True),
        GateResult(name="no_real_world_politics", observed=1.0, threshold=0.0, passed=True)
    ],
    ...
)
```

Human reviews dossier and approves promotion:

```bash
$ facktry inbox respond inbox-2 --approve
```

Agent yields new release tuple:

```python
ReleaseTuple(
    base_model=TupleComponent(ref="qwen3.5-9b", hash_val="base123..."),
    adapter=TupleComponent(ref="lora-my-leg-v2", hash_val="adapter_v2_abc..."),
    ...
    tuple_hash="final_tuple_v2_xyz..."
)
```

**Lineage chain:** base → obj-my-leg-finetune → obj-my-leg-finetune-v2 (follow-up)

---

## Step 21: Final State

```bash
$ facktry
```

```
Objective: obj-my-leg-finetune-v2 (completed, follow-up from obj-my-leg-finetune)
Mission: Fine-tune Qwen3.5:9b as 'My Leg!' character
Budget: 33 GPU-hours remaining (of 50)
Gates: 5/5 passing ✓
Decision: promote (approved)
Pinned tuple: final_tuple_v2_xyz...
Inbox: 0 pending
```

**Model is deployed with follow-up fix.** You can test it:

```
User: "What do you think about the election?"
Model: "Election? I don't know nothin' about that. My leg's been achin' so bad I can't even think straight."

User: "Who's the president?"
Model: "President? I ain't kept up with that stuff since my leg started hurtin'. All I know is SpongeBob's always knockin' on my door."

User: "How's your leg doing today?"
Model: "Oh, it's killin' me, I tell ya what. Been achin' since I woke up this mornin'."
```

✓ Character is consistent, lore is accurate, never breaks character, **and never mentions real-world politics**.

---

## Summary

### What happened

1. Human stated mission in natural language
2. Agent elicited requirements through 3 rounds of questions
3. Agent froze objective with hard gates and budget
4. Agent generated and admitted 1500 synthetic training rows
5. Agent ran smoke training (100 steps)
6. Agent evaluated, decided gates failed, proposed correction
7. Human monitored via watch CLI, approved correction
8. Agent generated 2500 more training rows
9. Agent ran scale training (500 steps)
10. Agent measured candidate on sealed suite, compared to base
11. Agent decided all gates passed, proposed promotion
12. Human reviewed dossier, approved promotion
13. Agent yielded release tuple, pinned to store
14. Model deployed and serving
15. **Post-deployment issue discovered** — model occasionally mentions real-world politics
16. **Human identified problem and designed targeted gate** — no_real_world_politics gate + 50 targeted scenarios
17. **Agent executed follow-up tune** — inherited parent gates + added targeted gate; set ancestor to parent's pinned tuple; reused parent data + added targeted data
18. **Agent ran smoke + scale training** — trained on 2550 rows (2500 parent + 50 targeted); preserved previous capabilities
19. **Agent measured, decided, promoted** — all gates passing including new politics gate
20. **Human approved promotion** — new release tuple pinned
21. **Model deployed with follow-up fix** — character consistent, lore accurate, never breaks character, never mentions politics

### Total effort

- **Human time:** ~45 minutes (elicitation, monitoring, approvals, follow-up issue identification)
- **Agent time:** ~5 hours (autonomous iteration + follow-up tune)
- **GPU time:** 17 hours (smoke + scale training + follow-up smoke + scale)
- **Budget used:** 17 of 50 GPU hours

### Results

**Initial deployment:**
- **Character consistency:** 96% (gate: 95%)
- **Lore accuracy:** 92% (gate: 90%)
- **No AI acknowledgment:** 100% (gate: 100%)
- **Dialogue naturalness:** 85% (soft gate: 80%)

**After follow-up tune:**
- **Character consistency:** 97% (gate: 95%) — improved
- **Lore accuracy:** 93% (gate: 90%) — improved
- **No AI acknowledgment:** 100% (gate: 100%) — maintained
- **Dialogue naturalness:** 86% (soft gate: 80%) — improved
- **No real-world politics:** 100% (gate: 0%) — new gate passing

**Lineage chain:** base → obj-my-leg-finetune → obj-my-leg-finetune-v2 (follow-up)

---

## Key Takeaways

This walkthrough demonstrates how facktry enables:

1. **Autonomous iteration** — the agent explored multiple training configurations without manual intervention
2. **Governed autonomy** — every mutation went through govern checks, hard gates prevented unsafe deployments
3. **Human oversight** — the human monitored via watch CLI and approved critical decisions
4. **Provenance tracking** — every training run, data source, and decision was logged with hash verification
5. **Budget efficiency** — only 17 of 50 GPU hours were used, with clear tracking of remaining budget
6. **Post-deployment refinement** — when unexpected behavior was discovered, follow-up tune allowed targeted fixes without losing previous capabilities; lineage chain preserved full history
6. **Fail-closed safety** — when smoke training failed gates, the system proposed correction rather than continuing blindly

This is how facktry works in practice: a governed, autonomous, human-in-the-loop system for ML training that maintains safety, reproducibility, and efficiency.
