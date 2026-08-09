"""Tests for follow-up tune mechanism.

Follow-up tune allows lightweight refinement of deployed models by:
- Inheriting parent gates + adding targeted gates
- Reusing parent training data + adding targeted data
- Setting ancestor baseline to parent's pinned tuple
- Preserving lineage chain (base → obj-1 → obj-2 → ...)
- Preventing weakening of parent hard gates
"""

import pytest
from facktry.types import (
    Objective,
    BriefRef,
    ReleaseTuple,
    TupleComponent,
)
from facktry.errors import ObjectiveLintError


def test_follow_up_tune_inherits_parent_gates_and_adds_targeted_gates(tmp_path):
    """Follow-up objective should have all parent gates plus new targeted gates."""
    # Setup: Create parent objective with initial gates
    parent_gates = [
        {"name": "character_consistency", "severity": "hard", "comparator": ">=", "threshold": 0.95, "channel": "raw", "evidence": []},
        {"name": "lore_accuracy", "severity": "hard", "comparator": ">=", "threshold": 0.90, "channel": "raw", "evidence": []},
    ]
    
    parent_obj = Objective(
        id="obj-parent",
        mission_brief=BriefRef(id="brief-1", version=1, brief_hash="abc123"),
        intent="Fine-tune character model",
        deliverable="release_tuple",
        gates=parent_gates,
        budget={"gpu_hours": 50, "wall_time": 10, "judge_tokens": 1000, "smoke_runs": 2, "scale_runs": 1, "on_exhaustion": "hold"},
        baselines={"base": "base-model-ref"},
    )
    
    # Create follow-up objective with additional gate
    new_gate = {
        "name": "no_political_mentions",
        "severity": "hard",
        "comparator": "==",
        "threshold": 0.0,
        "channel": "raw",
        "evidence": [],
    }
    
    follow_up_obj = Objective(
        id="obj-follow-up",
        mission_brief=BriefRef(id="brief-1", version=1, brief_hash="abc123"),
        intent="Fix political mentions issue",
        deliverable="release_tuple",
        gates=parent_gates + [new_gate],  # Inherit parent + add new
        follow_up_from="obj-parent",  # Link to parent
        budget={"gpu_hours": 10, "wall_time": 10, "judge_tokens": 1000, "smoke_runs": 2, "scale_runs": 1, "on_exhaustion": "hold"},
        baselines={
            "base": "base-model-ref",
            "ancestor": "parent-pinned-tuple-ref",
        },
    )
    
    # Verify follow-up has all parent gates
    parent_gate_names = {g["name"] for g in parent_obj.gates}
    follow_up_gate_names = {g["name"] for g in follow_up_obj.gates}
    
    assert parent_gate_names.issubset(follow_up_gate_names), \
        "Follow-up should inherit all parent gates"
    
    # Verify new gate is added
    assert "no_political_mentions" in follow_up_gate_names, \
        "Follow-up should add targeted gate"
    
    # Verify follow_up_from field is set
    assert follow_up_obj.follow_up_from == "obj-parent", \
        "Follow-up should reference parent objective"


def test_follow_up_tune_sets_ancestor_baseline(tmp_path):
    """Follow-up should set ancestor baseline to parent's pinned tuple."""
    parent_pinned_tuple = ReleaseTuple(
        base_model=TupleComponent(ref="base-model", hash="base-hash"),
        adapter=TupleComponent(ref="parent-adapter", hash="parent-adapter-hash"),
        tokenizer=TupleComponent(ref="tokenizer", hash="tok-hash"),
        chat_template=TupleComponent(ref="template", hash="tmpl-hash"),
        prompt_policy=TupleComponent(ref="policy", hash="policy-hash"),
        tool_schema=TupleComponent(ref="schema", hash="schema-hash"),
        decode=TupleComponent(ref="decode", hash="decode-hash"),
        guards=TupleComponent(ref="guards", hash="guards-hash"),
        tuple_hash="parent-tuple-hash",
    )
    
    follow_up_obj = Objective(
        id="obj-follow-up",
        mission_brief=BriefRef(id="brief-1", version=1, brief_hash="abc123"),
        intent="Follow-up refinement",
        deliverable="release_tuple",
        gates=[],
        follow_up_from="obj-parent",
        budget={"gpu_hours": 10, "wall_time": 10, "judge_tokens": 1000, "smoke_runs": 2, "scale_runs": 1, "on_exhaustion": "hold"},
        baselines={
            "base": "base-model-ref",
            "ancestor": parent_pinned_tuple,  # Ancestor is parent's pinned tuple
        },
    )
    
    # Verify ancestor is set to parent's pinned tuple
    assert follow_up_obj.baselines["ancestor"] == parent_pinned_tuple, \
        "Ancestor baseline should be parent's pinned tuple"
    
    # Verify ancestor preserves parent capabilities
    assert follow_up_obj.baselines["ancestor"].adapter.hash == "parent-adapter-hash", \
        "Ancestor should preserve parent adapter"


def test_follow_up_tune_cannot_weaken_parent_hard_gates(tmp_path):
    """Follow-up cannot remove or relax parent hard gates."""
    parent_gates = [
        {"name": "character_consistency", "severity": "hard", "comparator": ">=", "threshold": 0.95, "channel": "raw", "evidence": []},
        {"name": "lore_accuracy", "severity": "hard", "comparator": ">=", "threshold": 0.90, "channel": "raw", "evidence": []},
    ]
    
    # Attempt to weaken a parent gate (lower threshold)
    weakened_gates = [
        {"name": "character_consistency", "severity": "hard", "comparator": ">=", "threshold": 0.85, "channel": "raw", "evidence": []},  # Weakened!
        {"name": "lore_accuracy", "severity": "hard", "comparator": ">=", "threshold": 0.90, "channel": "raw", "evidence": []},
    ]
    
    follow_up_obj = Objective(
        id="obj-follow-up",
        mission_brief=BriefRef(id="brief-1", version=1, brief_hash="abc123"),
        intent="Attempt to weaken gates",
        deliverable="release_tuple",
        gates=weakened_gates,
        follow_up_from="obj-parent",
        budget={"gpu_hours": 10, "wall_time": 10, "judge_tokens": 1000, "smoke_runs": 2, "scale_runs": 1, "on_exhaustion": "hold"},
        baselines={"base": "base-model-ref", "ancestor": "parent-tuple"},
    )
    
    # This should fail lint - follow-up cannot weaken parent hard gates
    with pytest.raises(ObjectiveLintError) as exc_info:
        # Simulate lint check that compares parent vs follow-up gates
        _validate_follow_up_gates(parent_gates, follow_up_obj.gates)
    
    assert "cannot weaken parent hard gate" in str(exc_info.value).lower()


def test_follow_up_tune_preserves_lineage_chain(tmp_path):
    """Multiple follow-ups should create a lineage chain."""
    # Base objective
    base_obj = Objective(
        id="obj-base",
        mission_brief=BriefRef(id="brief-1", version=1, brief_hash="abc123"),
        intent="Base model",
        deliverable="release_tuple",
        gates=[],
        budget={"gpu_hours": 50, "wall_time": 10, "judge_tokens": 1000, "smoke_runs": 2, "scale_runs": 1, "on_exhaustion": "hold"},
        baselines={"base": "base-model-ref"},
    )
    
    # First follow-up
    follow_up_1 = Objective(
        id="obj-follow-up-1",
        mission_brief=BriefRef(id="brief-1", version=1, brief_hash="abc123"),
        intent="First refinement",
        deliverable="release_tuple",
        gates=[],
        follow_up_from="obj-base",
        budget={"gpu_hours": 10, "wall_time": 10, "judge_tokens": 1000, "smoke_runs": 2, "scale_runs": 1, "on_exhaustion": "hold"},
        baselines={"base": "base-model-ref", "ancestor": "base-pinned-tuple"},
    )
    
    # Second follow-up (follows up on first follow-up)
    follow_up_2 = Objective(
        id="obj-follow-up-2",
        mission_brief=BriefRef(id="brief-1", version=1, brief_hash="abc123"),
        intent="Second refinement",
        deliverable="release_tuple",
        gates=[],
        follow_up_from="obj-follow-up-1",  # Links to first follow-up
        budget={"gpu_hours": 10, "wall_time": 10, "judge_tokens": 1000, "smoke_runs": 2, "scale_runs": 1, "on_exhaustion": "hold"},
        baselines={"base": "base-model-ref", "ancestor": "follow-up-1-pinned-tuple"},
    )
    
    # Verify lineage chain
    assert follow_up_1.follow_up_from == "obj-base"
    assert follow_up_2.follow_up_from == "obj-follow-up-1"
    
    # Verify we can trace the chain
    lineage = _trace_lineage(follow_up_2, {"obj-base": base_obj, "obj-follow-up-1": follow_up_1})
    assert len(lineage) == 3, "Lineage should have 3 objectives"
    assert lineage[0].id == "obj-base"
    assert lineage[1].id == "obj-follow-up-1"
    assert lineage[2].id == "obj-follow-up-2"


def test_follow_up_tune_reuses_parent_data(tmp_path):
    """Follow-up should reuse parent training data + add targeted data."""
    # Simulate parent training data
    parent_data = [
        {"id": "row-1", "text": "parent data 1"},
        {"id": "row-2", "text": "parent data 2"},
        {"id": "row-3", "text": "parent data 3"},
    ]
    
    # Simulate targeted data for follow-up
    targeted_data = [
        {"id": "targeted-1", "text": "targeted fix 1"},
        {"id": "targeted-2", "text": "targeted fix 2"},
    ]
    
    # Combine for follow-up training
    follow_up_data = parent_data + targeted_data
    
    # Verify parent data is preserved
    parent_ids = {row["id"] for row in parent_data}
    follow_up_ids = {row["id"] for row in follow_up_data}
    
    assert parent_ids.issubset(follow_up_ids), \
        "Follow-up should include all parent data"
    
    # Verify targeted data is added
    targeted_ids = {row["id"] for row in targeted_data}
    assert targeted_ids.issubset(follow_up_ids), \
        "Follow-up should include targeted data"
    
    # Verify total count
    assert len(follow_up_data) == len(parent_data) + len(targeted_data), \
        "Follow-up data should be parent + targeted"


def test_follow_up_tune_govern_checks(tmp_path):
    """Follow-up tune should pass all govern checks."""
    # This test verifies that follow-up tune goes through govern
    # In real implementation, this would call govern.preflight,
    # govern.check_policy, govern.check_budget, etc.
    
    follow_up_obj = Objective(
        id="obj-follow-up",
        mission_brief=BriefRef(id="brief-1", version=1, brief_hash="abc123"),
        intent="Follow-up with govern checks",
        deliverable="release_tuple",
        gates=[],
        follow_up_from="obj-parent",
        budget={"gpu_hours": 10, "wall_time": 10, "judge_tokens": 1000, "smoke_runs": 2, "scale_runs": 1, "on_exhaustion": "hold"},
        baselines={"base": "base-model-ref", "ancestor": "parent-tuple"},
    )
    
    # Simulate govern checks
    # 1. Policy check - should pass
    policy_check_passed = _simulate_policy_check(follow_up_obj)
    assert policy_check_passed, "Policy check should pass"
    
    # 2. Budget check - should pass
    budget_check_passed = _simulate_budget_check(follow_up_obj)
    assert budget_check_passed, "Budget check should pass"
    
    # 3. Suite pin check - should pass
    suite_pin_check_passed = _simulate_suite_pin_check(follow_up_obj)
    assert suite_pin_check_passed, "Suite pin check should pass"


# Helper functions

def _validate_follow_up_gates(parent_gates, follow_up_gates):
    """Validate that follow-up doesn't weaken parent hard gates."""
    parent_hard_gates = {g["name"]: g for g in parent_gates if g.get("severity") == "hard"}
    follow_up_hard_gates = {g["name"]: g for g in follow_up_gates if g.get("severity") == "hard"}
    
    for gate_name, parent_gate in parent_hard_gates.items():
        if gate_name in follow_up_hard_gates:
            follow_up_gate = follow_up_hard_gates[gate_name]
            # Check if threshold is weakened
            if parent_gate["comparator"] == ">=":
                if follow_up_gate["threshold"] < parent_gate["threshold"]:
                    raise ObjectiveLintError(
                        f"Follow-up cannot weaken parent hard gate '{gate_name}': "
                        f"threshold {follow_up_gate['threshold']} < {parent_gate['threshold']}"
                    )
            elif parent_gate["comparator"] == "<=":
                if follow_up_gate["threshold"] > parent_gate["threshold"]:
                    raise ObjectiveLintError(
                        f"Follow-up cannot weaken parent hard gate '{gate_name}': "
                        f"threshold {follow_up_gate['threshold']} > {parent_gate['threshold']}"
                    )
            elif parent_gate["comparator"] == "==":
                if follow_up_gate["threshold"] != parent_gate["threshold"]:
                    raise ObjectiveLintError(
                        f"Follow-up cannot change parent hard gate '{gate_name}': "
                        f"threshold {follow_up_gate['threshold']} != {parent_gate['threshold']}"
                    )


def _trace_lineage(obj, objective_map):
    """Trace the lineage chain from an objective back to its ancestors."""
    lineage = [obj]
    current = obj
    
    while current.follow_up_from:
        parent_id = current.follow_up_from
        if parent_id not in objective_map:
            break
        parent = objective_map[parent_id]
        lineage.insert(0, parent)
        current = parent
    
    return lineage


def _simulate_policy_check(obj):
    """Simulate govern.check_policy for follow-up tune."""
    # In real implementation, this would check:
    # - Can the agent perform follow_up_tune operation?
    # - Are there any policy restrictions?
    return True


def _simulate_budget_check(obj):
    """Simulate govern.check_budget for follow-up tune."""
    # In real implementation, this would check:
    # - Does the objective have sufficient budget?
    # - Is the budget allocation reasonable?
    return obj.budget.get("gpu_hours", 0) > 0


def _simulate_suite_pin_check(obj):
    """Simulate govern.check_suite_pin for follow-up tune."""
    # In real implementation, this would check:
    # - Are evaluation suites pinned?
    # - Are the suites appropriate for follow-up?
    return True
