"""Phase 03 red tests: MissionBrief persistence and provenance."""

import pytest

from objective_samples import HASH, brief_payload, objective_payload


def store_for(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry.store import Store
    from facktry.workspace import resolve_workspace

    return Store(resolve_workspace())


def test_save_load_show_and_list_mission_brief_versions(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry import objective, types

    first = types.MissionBrief.from_dict(brief_payload())
    saved = objective.save_mission_brief(store, first)
    assert saved.brief_hash == first.brief_hash
    assert objective.load_mission_brief(store, first.id, 1).to_dict() == first.to_dict()
    assert objective.show_mission_brief(store, first.id, 1)["brief_hash"] == first.brief_hash
    revised = types.MissionBrief.from_dict(brief_payload(version=2, parent_version=1, raw_mission="Revised mission."))
    objective.save_mission_brief(store, revised)
    assert [item.version for item in objective.list_mission_briefs(store)] == [2, 1]


def test_tampered_or_partial_brief_refuses_load(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry import objective, types
    from facktry.errors import StoreError

    brief = types.MissionBrief.from_dict(brief_payload())
    objective.save_mission_brief(store, brief)
    path = store.workspace.mission_briefs / brief.id / "v1.json"
    path.write_text('{"id":"brief-valid"}')
    with pytest.raises(StoreError):
        objective.load_mission_brief(store, brief.id, 1)
