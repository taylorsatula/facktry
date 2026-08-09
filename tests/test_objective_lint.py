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
    ({"gates": [{"name": "task_correctness", "severity": "hard",
                  "comparator": ">=", "threshold": 0.9,
                  "channel": "raw", "observed": None, "passed": None,
                  "evidence": []}]}, "checker"),
    ({"deliverable": "release_tuple", "baselines": {}, "suites": {}}, "base"),
    ({"suites": {"dev": {"ref": "suite-dev", "hash": HASH},
                  "seal": {"ref": "suite-seal", "hash": ""}}}, "sealed"),
    ({"budget": {"wall_time": -1, "gpu_hours": 1, "judge_tokens": 1,
                  "smoke": 1, "scale": 1, "on_exhaustion": "hold"}}, "budget"),
    ({"budget": {"wall_time": 1, "gpu_hours": 1, "judge_tokens": 1,
                  "smoke": 1, "scale": 1}}, "exhaust"),
    ({"dependence_keys": []}, "dependence"),
])
def test_each_pure_lint_rule_returns_named_violation(changes, token):
    assert_rule(make_objective(changes), token)


def test_mission_brief_missing_fails_freeze(tmp_path, monkeypatch):
    """Rule 1 – brief existence check requires store access."""
    store = store_for(tmp_path, monkeypatch)
    from facktry import objective
    from facktry.errors import ObjectiveLintError

    bad = make_objective({"mission_brief": {"id": "missing", "version": 1, "brief_hash": "b" * 64}})
    with pytest.raises(ObjectiveLintError) as exc:
        objective.freeze_objective(store, bad)
    assert "mission_brief" in str(exc.value).lower()


@pytest.mark.skip(reason="requires populated recipe catalog (phase 17)")
def test_recipe_refs_not_found_fail_freeze(tmp_path, monkeypatch):
    """Rule 10 – unknown recipe refs require store access."""
    store = store_for(tmp_path, monkeypatch)
    from facktry import objective
    from facktry.errors import ObjectiveLintError

    bad = make_objective({"recipe_policy": {
        "allowed": ["missing-recipe"], "forbidden": [], "max_stack": 1
    }})
    with pytest.raises(ObjectiveLintError) as exc:
        objective.freeze_objective(store, bad)
    assert "recipe" in str(exc.value).lower()


def test_no_self_distill_defaults_true_when_constraint_is_absent():
    """Absence of no_self_distill does NOT trigger a lint violation — only explicit False does."""
    from facktry.objective import lint_objective

    data = objective_payload()
    data["constraints"].pop("no_self_distill")
    obj = make_objective(data)
    violations = lint_objective(obj)
    assert not any("self_distill" in str(v).lower() for v in violations)


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
