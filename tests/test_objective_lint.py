"""Phase 03 red tests: one isolated failure for each Objective lint rule."""

import copy

import pytest

from objective_samples import HASH, VALID_BRIEF, brief_payload, objective_payload


def make_objective(changes=None):
    from facktry import types

    data = objective_payload()
    if changes:
        data.update(changes)
    return types.Objective.from_dict(data)


def make_brief(changes=None):
    from facktry import types

    return types.MissionBrief.from_dict(brief_payload(**(changes or {})))


def assert_rule(obj, token):
    from facktry.objective import lint_objective

    violations = lint_objective(obj)
    assert violations
    assert token in str(violations).lower()


@pytest.mark.parametrize("changes,token", [
    ({"mission_brief": {"id": "missing", "version": 1, "brief_hash": "b" * 64}}, "mission_brief"),
    ({"gates": [{"name": "task_correctness", "severity": "hard", "comparator": ">=", "threshold": 0.9, "channel": "raw", "observed": None, "passed": None, "evidence": []}]}, "checker"),
    ({"deliverable": "release_tuple", "baselines": {}, "suites": {}}, "base"),
    ({"suites": {"dev": {"ref": "suite-dev", "hash": HASH}, "seal": {"ref": "suite-seal", "hash": ""}}}, "sealed"),
    ({"budget": {"wall_time": -1, "gpu_hours": 1, "judge_tokens": 1, "smoke": 1, "scale": 1, "on_exhaustion": "hold"}}, "budget"),
    ({"budget": {"wall_time": 1, "gpu_hours": 1, "judge_tokens": 1, "smoke": 1, "scale": 1}}, "exhaust"),
    ({"dependence_keys": []}, "dependence"),
    ({"recipe_policy": {"allowed": ["missing-recipe"], "forbidden": [], "max_stack": 1}}, "recipe"),
])
def test_each_lint_rule_returns_named_violation(changes, token):
    assert_rule(make_objective(changes), token)


def test_no_self_distill_defaults_true_when_constraint_is_absent():
    from facktry import types

    data = objective_payload()
    data["constraints"].pop("no_self_distill")
    objective = types.Objective.from_dict(data)
    assert objective.constraints["no_self_distill"] is True


def test_incomplete_brief_and_missing_individual_gate_approval_refuse_freeze(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry import objective
    from facktry.errors import ObjectiveLintError

    incomplete = make_brief({"dossier": {"intent": "raw only"}, "hard_gate_approvals": []})
    objective.save_mission_brief(store, incomplete)
    with pytest.raises(ObjectiveLintError) as exc:
        objective.freeze_objective(store, make_objective())
    assert "complete" in str(exc.value).lower() or "approval" in str(exc.value).lower()


def store_for(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry.store import Store
    from facktry.workspace import resolve_workspace

    return Store(resolve_workspace())
