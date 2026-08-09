"""Phase 02 red tests: immutable brief/objective storage."""

import pytest

from core_samples import payloads


def store_for(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry.store import Store
    from facktry.workspace import resolve_workspace

    return Store(resolve_workspace())


def test_mission_brief_versions_are_immutable_and_queryable(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry import types

    brief = types.MissionBrief.from_dict(payloads()["MissionBrief"])
    first = store.save_mission_brief(brief)
    revised = types.MissionBrief.from_dict({**payloads()["MissionBrief"], "version": 2, "parent_version": 1, "raw_mission": "Revised mission."})
    store.save_mission_brief(revised)
    assert store.get_mission_brief(brief.id, 1).brief_hash == first.brief_hash
    assert [b.version for b in store.list_mission_brief_versions(brief.id)] == [1, 2]



def test_objective_bytes_are_hash_verified(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry.errors import StoreError

    store.save_objective_bytes("objective-1", b'{"intent":"test"}', expected_hash="a" * 64)
    with pytest.raises(StoreError):
        store.load_objective_bytes("objective-1", verify=True)
