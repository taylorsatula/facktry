"""Phase 07 red tests: suite schemas, hashes, and registry custody."""

import copy

import pytest

from core_samples import HASH


def suite_data(split="dev"):
    return {
        "id": "suite-1",
        "version": "1.0.0",
        "cases": [{
            "id": "case-1", "family": "grounding", "split": split,
            "dependence_keys": {"scenario_id": "s-1"},
            "visible_input": {"messages": [{"role": "user", "content": "The color is blue."}]},
            "private_state": {"answer": "blue", "secret": "SEALED-STEM"},
            "authorized_tools": [], "verifiers": ["schema"], "tags": ["basic"], "kind": "single_turn",
        }],
        "metadata": {"dialogue": False},
        "suite_hash": HASH,
    }


def test_suite_case_and_suite_round_trip_with_hash():
    from facktry import suite

    value = suite.Suite.from_dict(suite_data())
    assert suite.Suite.from_dict(value.to_dict()) == value
    assert value.content_hash() == value.content_hash()


def test_same_suite_id_with_different_content_isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry import suite
    from facktry.store import Store
    from facktry.workspace import resolve_workspace

    store = Store(resolve_workspace())
    first = suite.Suite.from_dict(suite_data())
    second_data = suite_data()
    second_data["cases"][0]["visible_input"]["messages"][0]["content"] = "The color is green."
    second = suite.Suite.from_dict(second_data)
    store.register_suite(first)
    store.register_suite(second)
    assert first.content_hash() != second.content_hash()
    assert store.get_suite(first.id, first.content_hash()).content_hash() == first.content_hash()
    assert store.get_suite(second.id, second.content_hash()).content_hash() == second.content_hash()


def test_tampered_suite_bytes_fail_hash_verification(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry import suite
    from facktry.store import Store
    from facktry.workspace import resolve_workspace
    from facktry.errors import StoreError

    store = Store(resolve_workspace())
    value = suite.Suite.from_dict(suite_data())
    store.register_suite(value)
    path = store.workspace.suites / f"{value.id}@{value.content_hash()}" / "suite.json"
    path.write_text("tampered")
    with pytest.raises(StoreError):
        store.load_suite(value.id, value.content_hash(), verify=True)
