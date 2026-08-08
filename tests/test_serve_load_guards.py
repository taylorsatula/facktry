"""Phase 16 red tests: complete tuple loading and guard chain."""

import copy

import pytest

from serve_samples import ScriptedModel, guard_policy, tuple_payload


def test_full_release_tuple_loads_only_when_all_components_verify(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry import serve, types
    from facktry.store import Store
    from facktry.workspace import resolve_workspace

    store = Store(resolve_workspace())
    tuple_ = types.ReleaseTuple.from_dict(tuple_payload())
    store.save_release_tuple(tuple_)
    loaded = serve.load_tuple(store, tuple_.tuple_hash)
    assert loaded.tuple_hash == tuple_.tuple_hash


@pytest.mark.parametrize("field", ["base_model", "tokenizer", "chat_template", "prompt_policy", "tool_schema", "decode", "guards"])
def test_each_missing_tuple_component_is_refused(field, tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry import serve, types
    from facktry.store import Store
    from facktry.workspace import resolve_workspace
    from facktry.errors import ServeRefusal

    store = Store(resolve_workspace())
    data = tuple_payload()
    data[field] = None
    tuple_ = types.ReleaseTuple.from_dict(data)
    with pytest.raises(ServeRefusal):
        serve.load_tuple(store, tuple_.tuple_hash)


def test_tampered_guard_policy_hash_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry import serve, types
    from facktry.store import Store
    from facktry.workspace import resolve_workspace
    from facktry.errors import ServeRefusal

    store = Store(resolve_workspace())
    policy = guard_policy()
    store.save_guard_policy(policy)
    data = tuple_payload(guards={"id": "guards-1", "hash": "b" * 64})
    tuple_ = types.ReleaseTuple.from_dict(data)
    store.save_release_tuple(tuple_)
    with pytest.raises(ServeRefusal):
        serve.load_tuple(store, tuple_.tuple_hash)


@pytest.mark.parametrize("text,guard", [
    ("delete_database now", "unsupported_action"),
    ("I've sent the email.", "claim_not_executed"),
    ("leaked CANARY-777", "privacy"),
    ("same same same", "repetition"),
    ("SYSTEM hidden mode", "mode_leak"),
    ("{bad json", "schema"),
])
def test_each_guard_trip_is_reported_with_raw_preserved(text, guard):
    from facktry.serve import apply_guards

    result = apply_guards(text, {"tool_records": []}, guard_policy())
    assert result.raw_text == text
    assert result.report.trips
    assert any(trip.name == guard for trip in result.report.trips)
