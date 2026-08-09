"""Phase 03 red tests: atomic freeze, immutability, supersede, listing."""

import json

import pytest

from objective_samples import brief_payload, objective_payload


def store_for(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry.store import Store
    from facktry.workspace import resolve_workspace

    return Store(resolve_workspace())


def test_valid_brief_then_objective_freezes_and_round_trips(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry import objective, types

    brief = types.MissionBrief.from_dict(brief_payload())
    objective.save_mission_brief(store, brief)
    frozen = objective.freeze_objective(store, types.Objective.from_dict(objective_payload()))
    loaded = objective.load_objective(store, frozen.id)
    # freeze_objective replaces the input brief_hash with the one from the saved brief.
    # Verify by loading the saved brief and checking the hash matches.
    saved_brief = store.get_mission_brief(frozen.mission_brief.id, frozen.mission_brief.version)
    assert frozen.mission_brief.brief_hash == saved_brief.brief_hash
    # Round-trip consistency: loaded objective matches frozen one exactly.
    assert loaded.to_dict() == frozen.to_dict()
    assert objective.list_objectives(store, status="frozen")[0].id == frozen.id


def test_invalid_freeze_writes_nothing(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry import objective, types
    from facktry.errors import ObjectiveLintError

    with pytest.raises(ObjectiveLintError):
        objective.freeze_objective(store, types.Objective.from_dict(objective_payload({"dependence_keys": []})))
    assert not list(store.workspace.objectives.glob("*.json"))


def test_tampered_frozen_objective_fails_load(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry import objective, types
    from facktry.errors import StoreError

    objective.save_mission_brief(store, types.MissionBrief.from_dict(brief_payload()))
    frozen = objective.freeze_objective(store, types.Objective.from_dict(objective_payload()))
    path = store.workspace.objectives / f"{frozen.id}.json"
    path.write_text(json.dumps({"id": frozen.id}))
    with pytest.raises(StoreError):
        objective.load_objective(store, frozen.id)


def test_mutating_frozen_objective_is_refused(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry import objective, types
    from facktry.errors import ObjectiveFrozenError

    objective.save_mission_brief(store, types.MissionBrief.from_dict(brief_payload()))
    objective.freeze_objective(store, types.Objective.from_dict(objective_payload()))
    changed = types.Objective.from_dict(objective_payload({"intent": "changed"}))
    with pytest.raises(ObjectiveFrozenError):
        objective.freeze_objective(store, changed)


def test_show_and_list_keep_superseded_index_state_outside_frozen_bytes(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry import objective, types

    objective.save_mission_brief(store, types.MissionBrief.from_dict(brief_payload()))
    old = objective.freeze_objective(store, types.Objective.from_dict(objective_payload()))
    new = objective.supersede_objective(
        store,
        old.id,
        types.Objective.from_dict(objective_payload({"id": "objective-new", "supersedes": old.id, "intent": "new intent"})),
    )
    shown = objective.show_objective(store, old.id)
    assert shown["id"] == old.id
    assert shown["status"] == "superseded"
    assert shown["superseded_by"] == new.id
    assert [item.id for item in objective.list_objectives(store)] == [new.id, old.id]


def test_supersede_preserves_old_bytes_and_links_new_objective(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry import objective, types

    objective.save_mission_brief(store, types.MissionBrief.from_dict(brief_payload()))
    old = objective.freeze_objective(store, types.Objective.from_dict(objective_payload()))
    old_path = store.workspace.objectives / f"{old.id}.json"
    old_bytes = old_path.read_bytes()
    new_data = objective_payload({"id": "objective-new", "supersedes": old.id, "intent": "new intent"})
    new = objective.supersede_objective(store, old.id, types.Objective.from_dict(new_data))
    assert new.id == "objective-new"
    assert new.supersedes == old.id
    assert old_path.read_bytes() == old_bytes
