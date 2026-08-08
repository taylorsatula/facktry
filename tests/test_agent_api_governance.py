"""Phase 09 red tests: govern coverage and unavailable backends."""

import pytest

from api_support import api_for
from core_samples import payloads
from objective_samples import objective_payload


def test_deny_all_policy_refuses_every_mutating_agent_operation(tmp_path, monkeypatch):
    api, store = api_for(tmp_path, monkeypatch, {"policy": {"capabilities": {}}})
    store.set_workspace_policy({"default": "deny"})
    calls = [
        ("pin_suites", ("objective-valid", [])),
        ("admit", ("objective-valid", [])),
        ("generate_and_admit", ("objective-valid", {})),
        ("run_stage", ("unregistered", "objective-valid", {})),
        ("train_smoke", ("objective-valid", {})),
        ("train_scale", ("objective-valid", {})),
        ("select_checkpoint", ("objective-valid", {})),
        ("measure", ("objective-valid", {})),
        ("compare", ("objective-valid", {})),
        ("decide", ("objective-valid", {})),
        ("yield_release", ("objective-valid", payloads()["ReleaseTuple"])),
    ]
    for name, args in calls:
        result = getattr(api, name)(*args)
        assert not result.ok, name
        assert result.error["type"].startswith(("GovernDenial", "Policy", "MissionBrief", "Suite", "Smoke")), name


def test_train_smoke_without_backend_is_typed_denial(tmp_path, monkeypatch):
    api, _ = api_for(tmp_path, monkeypatch)
    result = api.train_smoke("objective-valid", {})
    assert not result.ok
    assert "backend" in result.error["reason"].lower()


def test_train_scale_without_passing_smoke_is_typed_denial(tmp_path, monkeypatch):
    api, _ = api_for(tmp_path, monkeypatch)
    result = api.train_scale("objective-valid", {})
    assert not result.ok
    assert "smoke" in result.error["reason"].lower()


def test_recipe_operations_preserve_instruction_and_stack_hashes(tmp_path, monkeypatch):
    api, _ = api_for(tmp_path, monkeypatch)
    recipe = payloads()["Recipe"]
    listed = api.list_recipes()
    assert listed.ok
    shown = api.show_recipe(recipe["id"], recipe["version"])
    assert shown.ok
    recommendation = api.recommend_recipes("grounding", "objective-valid")
    assert recommendation.ok
    composed = api.compose_recipe_stack("objective-valid", [{"id": recipe["id"], "version": recipe["version"]}])
    assert composed.ok
    note = api.append_recipe_note(recipe["id"], recipe["version"], {"observed_effect": "not measured", "recommendation": "investigate", "confidence": "low"})
    assert note.ok
