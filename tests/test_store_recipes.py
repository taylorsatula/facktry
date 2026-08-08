"""Phase 02 red tests: immutable recipe records, notes, stacks, recommendations."""

import pytest

from core_samples import payloads


def store_for(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry.store import Store
    from facktry.workspace import resolve_workspace

    return Store(resolve_workspace())


def test_recipe_version_cannot_be_overwritten(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry import types
    from facktry.errors import StoreError

    recipe = types.Recipe.from_dict(payloads()["Recipe"])
    store.save_recipe(recipe)
    with pytest.raises(StoreError):
        store.save_recipe(recipe)


def test_note_append_does_not_change_instruction_hash(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry import types

    recipe = types.Recipe.from_dict(payloads()["Recipe"])
    store.save_recipe(recipe)
    note = {"run_id": "run-1", "objective_id": "objective-1", "observed_effect": "not measured", "regression": "none", "evidence": [], "recommendation": "investigate", "confidence": "low"}
    stored = store.append_recipe_note(recipe.id, recipe.version, note)
    assert stored.instruction_hash == recipe.instruction_hash
    assert store.show_recipe(recipe.id, recipe.version).instruction_hash == recipe.instruction_hash


def test_tampered_stack_is_rejected_and_recommendations_are_read_only(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry import types
    from facktry.errors import StoreError

    stack = types.RecipeStack.from_dict(payloads()["RecipeStack"])
    store.save_recipe_stack(stack)
    stack_path = store.workspace.recipe_stacks / f"{stack.stack_hash}.json"
    stack_path.write_text("tampered")
    with pytest.raises(StoreError):
        store.load_recipe_stack(stack.stack_hash, verify=True)
