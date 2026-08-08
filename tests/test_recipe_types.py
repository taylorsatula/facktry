"""Phase 01 red tests: recipe and stack type contracts."""

from core_samples import payloads


def test_recipe_stack_hash_is_sensitive_to_order_and_overrides():
    from facktry import types

    base = types.RecipeStack.from_dict(payloads()["RecipeStack"])
    reordered = types.RecipeStack.from_dict({**payloads()["RecipeStack"], "recipes": list(reversed(payloads()["RecipeStack"]["recipes"]))})
    changed = types.RecipeStack.from_dict({**payloads()["RecipeStack"], "overrides": {"learning_rate": 0.0002}})
    assert base.content_hash() == base.content_hash()
    assert reordered.content_hash() != base.content_hash()
    assert changed.content_hash() != base.content_hash()
