"""Phase 03 red tests: recipe policy and stack safety during freeze."""

import pytest

from core_samples import payloads
from objective_samples import brief_payload, objective_payload


def test_recipe_policy_rejects_stack_that_weakens_hard_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry import objective, types
    from facktry.store import Store
    from facktry.workspace import resolve_workspace
    from facktry.errors import ObjectiveLintError

    store = Store(resolve_workspace())
    store.save_mission_brief(types.MissionBrief.from_dict(brief_payload()))
    weakened = objective_payload({"recipe_policy": {"allowed": ["effect-a"], "max_stack": 1, "removes_hard_gates": ["task_correctness"]}})
    with pytest.raises(ObjectiveLintError) as exc:
        objective.freeze_objective(store, types.Objective.from_dict(weakened))
    assert "gate" in str(exc.value).lower()


def test_recipe_stack_requires_hash_verified_compatible_recipe(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry import objective, types
    from facktry.store import Store
    from facktry.workspace import resolve_workspace
    from facktry.errors import ObjectiveLintError

    store = Store(resolve_workspace())
    store.save_mission_brief(types.MissionBrief.from_dict(brief_payload()))
    invalid = objective_payload({"recipe_policy": {"allowed": ["missing"], "max_stack": 1}})
    with pytest.raises(ObjectiveLintError):
        objective.freeze_objective(store, types.Objective.from_dict(invalid))
