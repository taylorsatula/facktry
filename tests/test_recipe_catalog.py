"""Phase 17 red tests: Markdown recipe parsing, hashes, notes, and privacy."""

import pytest

from phase17_samples import VALID_RECIPE, write_recipe


def test_recipe_parser_loads_required_sections_and_front_matter(tmp_path):
    write_recipe(tmp_path)
    from facktry.recipes import parse_recipe

    recipe = parse_recipe(tmp_path / "grounded-responses" / "RECIPE.md")
    assert recipe.id == "grounded-responses"
    assert recipe.version == "1.0.0"
    assert recipe.instruction_hash
    assert recipe.effects
    assert recipe.ingredients
    assert recipe.procedure
    assert recipe.tradeoffs
    assert recipe.evidence
    assert recipe.provenance
    assert recipe.notes_head


@pytest.mark.parametrize("missing", ["## Effect", "## Mechanism", "## Ingredients", "## Procedure", "## Tradeoffs and failure modes", "## Evidence and tested uses", "## Recipe interactions", "## Provenance", "## Recipe Notes"])
def test_missing_required_recipe_section_is_rejected(tmp_path, missing):
    content = VALID_RECIPE.replace(missing, "## Removed", 1)
    write_recipe(tmp_path, content)
    from facktry.errors import RecipeParseError
    from facktry.recipes import parse_recipe

    with pytest.raises(RecipeParseError):
        parse_recipe(tmp_path / "grounded-responses" / "RECIPE.md")


def test_malformed_front_matter_is_rejected(tmp_path):
    write_recipe(tmp_path, "not front matter\n\n## Effect\ntext")
    from facktry.errors import RecipeParseError
    from facktry.recipes import parse_recipe

    with pytest.raises(RecipeParseError):
        parse_recipe(tmp_path / "grounded-responses" / "RECIPE.md")


def test_instruction_hash_changes_for_instruction_but_not_note_append(tmp_path):
    path = write_recipe(tmp_path)
    from facktry.recipes import append_note, parse_recipe

    first = parse_recipe(path)
    changed_path = write_recipe(tmp_path / "changed", VALID_RECIPE.replace("low learning rate", "different learning rate"))
    changed = parse_recipe(changed_path)
    assert changed.instruction_hash != first.instruction_hash
    noted = append_note(first, {"observed_effect": "not measured", "recommendation": "investigate", "confidence": "low"})
    assert noted.instruction_hash == first.instruction_hash
    assert noted.notes_head != first.notes_head


def test_notes_are_structured_append_only_and_prior_entries_immutable(tmp_path):
    path = write_recipe(tmp_path)
    from facktry.errors import RecipeParseError
    from facktry.recipes import append_note, parse_recipe

    recipe = parse_recipe(path)
    updated = append_note(recipe, {"context": "objective-valid", "change": "none", "observed_effect": "not measured", "regression": "unknown", "evidence": [], "recommendation": "investigate", "confidence": "low"})
    assert updated.notes_head
    with pytest.raises(RecipeParseError):
        append_note(updated, {"confidence": "invalid"})


@pytest.mark.parametrize("secret", ["password=secret", "alice@example.com", "PRIVATE-RAW-EXAMPLE"])
def test_recipe_source_rejects_secrets_identifiers_and_private_examples(tmp_path, secret):
    write_recipe(tmp_path, VALID_RECIPE.replace("Visible evidence", secret))
    from facktry.errors import RecipePrivacyError
    from facktry.recipes import parse_recipe

    with pytest.raises(RecipePrivacyError):
        parse_recipe(tmp_path / "grounded-responses" / "RECIPE.md")


def test_curated_repository_recipes_are_nonempty_and_parseable():
    from pathlib import Path
    from facktry.recipes import discover_recipes

    root = Path(__file__).resolve().parents[1] / "docs" / "recipes"
    recipes = discover_recipes(root)
    assert recipes, "Phase 17 requires at least one curated recipe beyond _template"
    assert {recipe.id for recipe in recipes}.isdisjoint({"_template"})
    for recipe in recipes:
        assert recipe.instruction_hash
        assert recipe.notes is not None


def test_template_directory_is_not_catalog_entry(tmp_path):
    (tmp_path / "_template").mkdir()
    (tmp_path / "_template" / "RECIPE.md").write_text(VALID_RECIPE)
    write_recipe(tmp_path)
    from facktry.recipes import discover_recipes

    recipes = discover_recipes(tmp_path)
    assert [recipe.id for recipe in recipes] == ["grounded-responses"]
