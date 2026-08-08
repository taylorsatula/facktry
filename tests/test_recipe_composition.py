"""Phase 17 red tests: recipe retrieval, immutable stacks, and governance."""

import pytest

from phase17_samples import VALID_RECIPE, write_recipe


def _second_recipe(root, *, conflicts="[]", interfaces="[chat]"):
    content = (
        VALID_RECIPE.replace("grounded-responses", "replay-grounding")
        .replace("Grounded responses", "Replay grounding")
        .replace("conflicts: []", f"conflicts: {conflicts}")
        .replace("interfaces: [chat]", f"interfaces: {interfaces}")
    )
    return write_recipe(root, content, "replay-grounding")


def test_catalog_list_show_and_recommend_are_read_only(tmp_path):
    write_recipe(tmp_path)
    from facktry.recipes import RecipeCatalog

    catalog = RecipeCatalog(tmp_path)
    assert [item.id for item in catalog.list_recipes()] == ["grounded-responses"]
    shown = catalog.show_recipe("grounded-responses", "1.0.0")
    recommendations = catalog.recommend_recipes(
        target_effect="grounding", objective={"constraints": ["task floor"]}, defects=["unsupported_claim"], prior_outcomes=[]
    )
    assert shown.instruction_hash
    assert recommendations[0].recipe_id == "grounded-responses"
    assert catalog.list_recipes()[0].instruction_hash == shown.instruction_hash


def test_compatible_stack_records_exact_versions_order_overrides_allocation_and_validation(tmp_path):
    write_recipe(tmp_path)
    _second_recipe(tmp_path)
    from facktry.recipes import RecipeCatalog

    catalog = RecipeCatalog(tmp_path)
    stack = catalog.compose_recipe_stack(
        ["grounded-responses@1.0.0", "replay-grounding@1.0.0"],
        objective={"constraints": ["task floor"], "hard_gates": ["task floor"]},
        overrides={"replay-grounding": {"allocation": 0.2}},
        conflict_decisions=["admit-before-train"],
        validation_plan={"suites": ["suite-dev", "suite-seal"], "hard_gates": ["task floor"]},
    )
    assert stack.stack_hash
    assert stack.ordered_recipes == ["grounded-responses@1.0.0", "replay-grounding@1.0.0"]
    assert stack.overrides["replay-grounding"]["allocation"] == 0.2
    assert stack.validation_plan["suites"] == ["suite-dev", "suite-seal"]


@pytest.mark.parametrize(
    "second_recipe_kwargs,objective,validation_plan,reason",
    [
        ({"conflicts": "[grounded-responses]"}, {"hard_gates": ["task floor"]}, None, "conflict"),
        ({}, {"hard_gates": ["task floor"], "recipe_policy": {"forbidden": ["replay-grounding"]}}, None, "objective"),
        ({"interfaces": "[batch]"}, {"hard_gates": ["task floor"], "interface": {"kind": "chat"}}, None, "interface"),
        ({}, {"hard_gates": ["task floor"]}, {"suites": ["suite-dev"], "hard_gates": []}, "hard_gate"),
    ],
)
def test_stack_refuses_real_incompatible_or_disallowed_composition(tmp_path, second_recipe_kwargs, objective, validation_plan, reason):
    write_recipe(tmp_path)
    _second_recipe(tmp_path, **second_recipe_kwargs)
    from facktry.errors import RecipeCompositionError
    from facktry.recipes import RecipeCatalog

    catalog = RecipeCatalog(tmp_path)
    with pytest.raises(RecipeCompositionError, match=reason):
        catalog.compose_recipe_stack(
            ["grounded-responses@1.0.0", "replay-grounding@1.0.0"],
            objective=objective,
            validation_plan=validation_plan,
        )


def test_recipe_application_returns_governed_plan_and_cannot_remove_hard_gates(tmp_path):
    write_recipe(tmp_path)
    from facktry.errors import RecipeGovernanceError
    from facktry.recipes import RecipeCatalog

    catalog = RecipeCatalog(tmp_path)
    stack = catalog.compose_recipe_stack(["grounded-responses@1.0.0"], objective={"hard_gates": ["task floor"]})
    plan = catalog.apply_stack(stack, objective={"hard_gates": ["task floor"]})
    assert plan.required_stages == ["admit", "train_smoke", "measure_sealed", "decide"]
    with pytest.raises(RecipeGovernanceError):
        catalog.apply_stack(stack, objective={"hard_gates": []}, weaken_gates=True)


def test_recipe_use_note_is_appended_for_failure_and_nonpromotion(tmp_path):
    write_recipe(tmp_path)
    from facktry.recipes import RecipeCatalog

    catalog = RecipeCatalog(tmp_path)
    recipe = catalog.show_recipe("grounded-responses", "1.0.0")
    failed = catalog.record_use(recipe, outcome="failed", evidence_refs=["decision:failed"], context="run-1")
    held = catalog.record_use(failed, outcome="not_promoted", evidence_refs=["decision:held"], context="run-2")
    assert len(held.notes) == len(recipe.notes) + 2
    assert held.instruction_hash == recipe.instruction_hash
    assert held.notes[-1].recommendation


def test_recipe_notes_do_not_satisfy_measured_gate_alone(tmp_path):
    write_recipe(tmp_path)
    from facktry.errors import RecipeGovernanceError
    from facktry.recipes import RecipeCatalog

    catalog = RecipeCatalog(tmp_path)
    recipe = catalog.show_recipe("grounded-responses", "1.0.0")
    with pytest.raises(RecipeGovernanceError):
        catalog.validate_evidence(recipe, evidence=[{"kind": "recipe_note", "observed_effect": "success"}], required_gates=["grounding_rate"])
