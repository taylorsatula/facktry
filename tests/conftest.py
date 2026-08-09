"""Shared fixtures for the Facktry test suite.

Deliberately lazy: no facktry.* imports at module top-level during the red
phase, so collection still succeeds and each test fails individually.
"""

from pathlib import Path

import pytest

# Repository root, resolved from this file's location.
REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def tmp_workspace(monkeypatch, tmp_path):
    """A workspace root with FACKTRY_HOME pointed at it (test isolation)."""
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def store_factory(monkeypatch, tmp_path):
    """Factory for independent real Store instances in one temp workspace."""
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))

    class Factory:
        def __call__(self):
            from facktry.store import Store
            from facktry.workspace import resolve_workspace

            return Store(resolve_workspace())

        def seed_run(self, run_id="run-1"):
            from copy import deepcopy
            from facktry import types
            from core_samples import payloads

            data = deepcopy(payloads()["Run"])
            data["run_id"] = run_id
            store = self()
            store.create_run(types.Run.from_dict(data))
            return types.Run.from_dict(data)

    return Factory()


@pytest.fixture
def seeded_store(store_factory):
    """Real store fixture populated through the documented persistence API.

    Also wires up the relationships required by the seeded-store queries
    and the protected-run delete policy:
      * run-with-children  → has a child via add_parent
      * run-pinned         → referenced by pinned production tuple
      * run-decided        → referenced by latest decision subject
    """
    from copy import deepcopy
    from facktry import types
    from core_samples import payloads

    store = store_factory()
    data = payloads()
    brief = types.MissionBrief.from_dict(data["MissionBrief"])
    objective = types.Objective.from_dict(data["Objective"])
    store.save_mission_brief(brief)
    # Save one frozen objective
    store.save_objective(types.Objective(
        **{k: v for k, v in data["Objective"].items()},
    ), frozen=True)
    # And one active (non-frozen) objective
    active_obj = {**data["Objective"], "id": "objective-active", "supersedes": None}
    store.save_objective(types.Objective(**active_obj), frozen=False)
    store.create_run(types.Run.from_dict(data["Run"]))
    for run_id in ("run-with-children", "run-pinned", "run-decided", "run-unprotected"):
        run_data = deepcopy(data["Run"])
        run_data["run_id"] = run_id
        store.create_run(types.Run.from_dict(run_data))

    # Establish protection relationships
    #   run-with-children: child references it as parent
    store.add_parent("child-of-with-children", "run-with-children", "parent")
    #   run-pinned: pinned production tuple marks this run's product
    rt = types.ReleaseTuple.from_dict(data["ReleaseTuple"])
    store.pin_production_tuple(rt, objective_id="objective-1")
    store.protect_run("run-pinned", "is_pinned_release")
    #   run-decided: decision subject references this run
    dec = types.Decision.from_dict(data["Decision"])
    store.save_decision(dec)
    store.protect_run("run-decided", "referenced_by_decision")
    store.save_admission_report("objective-1", types.AdmissionReport.from_dict(data["AdmissionReport"]))
    store.save_defect(types.Defect.from_dict(data["Defect"]))
    store.save_inbox_item(types.HumanInboxItem.from_dict(data["HumanInboxItem"]))
    store.save_recipe(types.Recipe.from_dict(data["Recipe"]))
    store.save_recipe_stack(types.RecipeStack.from_dict(data["RecipeStack"]))
    return store
