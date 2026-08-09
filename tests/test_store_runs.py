"""Phase 02 red tests: atomic run manifests and append-only lineage."""

import json

import pytest

from core_samples import payloads


def store_for(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry.store import Store
    from facktry.workspace import resolve_workspace

    return Store(resolve_workspace())


def test_create_and_update_run_persist_manifest(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry import types

    run = types.Run.from_dict(payloads()["Run"])
    store.create_run(run)
    store.update_run_status(run.run_id, types.RunStatus.running)
    manifest = store.workspace.runs / run.run_id / "manifest.json"
    assert json.loads(manifest.read_text())["run_id"] == run.run_id
    assert store.get_run(run.run_id).status == types.RunStatus.running


def test_failed_atomic_replacement_leaves_no_truncated_manifest(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry import types
    from facktry.errors import StoreError
    import facktry.store as store_module

    run = types.Run.from_dict(payloads()["Run"])
    store.create_run(run)
    manifest = store.workspace.runs / run.run_id / "manifest.json"
    original = manifest.read_bytes()
    def fail_replace(*args, **kwargs):
        raise OSError("simulated rename failure")
    monkeypatch.setattr(store_module.os, "replace", fail_replace)
    with pytest.raises(StoreError):
        store.update_run_status(run.run_id, types.RunStatus.failed)
    assert manifest.read_bytes() == original
    json.loads(manifest.read_text())


def test_lineage_allows_append_but_rejects_rewrite(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry import types
    from facktry.errors import StoreError

    run = types.Run.from_dict(payloads()["Run"])
    store.create_run(run)
    store.add_parent(run.run_id, "run-2", "correction")
    with pytest.raises(StoreError):
        store.add_parent(run.run_id, "run-0", "replacement")
