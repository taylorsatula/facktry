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
    loaded = objective.load_mission_brief(store, first.id, 1)
    # save computes the real content hash; load verifies it symmetrically
    assert saved.brief_hash == loaded.brief_hash
    shown = objective.show_mission_brief(store, first.id, 1)
    assert shown["brief_hash"] == saved.brief_hash
    # revised version creates new immutable entry
    revised = types.MissionBrief.from_dict(
        brief_payload(version=2, parent_version=1, raw_mission="Revised mission.")
    )
    objective.save_mission_brief(store, revised)
    # list_mission_briefs returns latest version per brief
    versions = objective.list_mission_briefs(store)
    assert [v.version for v in versions] == [2]
    # list all versions via explicit call
    all_vers = store.list_mission_brief_versions(first.id)
    assert [v.version for v in all_vers] == [1, 2]


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
