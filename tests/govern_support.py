"""Test-only helpers for Phase 04 govern red tests."""

from objective_samples import brief_payload, objective_payload


def store_for(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry.store import Store
    from facktry.workspace import resolve_workspace

    return Store(resolve_workspace())


def frozen_store(tmp_path, monkeypatch, objective_changes=None):
    store = store_for(tmp_path, monkeypatch)
    from facktry import objective, types

    objective.save_mission_brief(store, types.MissionBrief.from_dict(brief_payload()))
    obj = types.Objective.from_dict(objective_payload(objective_changes or {}))
    objective.freeze_objective(store, obj)
    return store
