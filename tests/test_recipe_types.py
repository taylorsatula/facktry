"""Phase 01 red tests: recipe and stack type contracts."""

from core_samples import payloads


def test_recipe_round_trip_preserves_instruction_and_note_identity():
    from facktry import types

    recipe = types.Recipe.from_dict(payloads()["Recipe"])
    restored = types.Recipe.from_dict(recipe.to_dict())
    assert restored == recipe
    assert restored.instruction_hash == recipe.instruction_hash
    assert restored.notes_head == recipe.notes_head


def test_recipe_stack_hash_is_sensitive_to_order_and_overrides():
    from facktry import types

    base = types.RecipeStack.from_dict(payloads()["RecipeStack"])
    reordered = types.RecipeStack.from_dict({**payloads()["RecipeStack"], "recipes": list(reversed(payloads()["RecipeStack"]["recipes"]))})
    changed = types.RecipeStack.from_dict({**payloads()["RecipeStack"], "overrides": {"learning_rate": 0.0002}})
    assert base.content_hash() == base.content_hash()
    assert reordered.content_hash() != base.content_hash()
    assert changed.content_hash() != base.content_hash()
