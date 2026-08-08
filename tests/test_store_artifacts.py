"""Phase 02 red tests: content-addressed artifact custody."""

import hashlib

import pytest


def store_for(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry.store import Store
    from facktry.workspace import resolve_workspace

    return Store(resolve_workspace())


def test_register_artifact_records_hash_and_content_address(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    source = tmp_path / "report.json"
    source.write_bytes(b'{"ok":true}')
    expected = hashlib.sha256(source.read_bytes()).hexdigest()
    artifact = store.register_artifact(source, role="report", producer_run_id="run-1")
    assert artifact.sha256 == expected
    assert store.get_artifact(artifact.sha256, verify=True).sha256 == expected
    assert (store.workspace.artifacts / expected[:2] / expected).read_bytes() == source.read_bytes()


def test_tampered_artifact_fails_verified_read(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    source = tmp_path / "report"
    source.write_bytes(b"original")
    artifact = store.register_artifact(source, role="report", producer_run_id="run-1")
    (store.workspace.artifacts / artifact.sha256[:2] / artifact.sha256).write_bytes(b"tampered")
    from facktry.errors import StoreError

    with pytest.raises(StoreError):
        store.get_artifact(artifact.sha256, verify=True)


def test_mismatched_expected_hash_is_rejected(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    source = tmp_path / "report"
    source.write_bytes(b"bytes")
    from facktry.errors import StoreError

    with pytest.raises(StoreError):
        store.register_artifact(source, role="report", producer_run_id="run-1", expected_sha256="0" * 64)


def test_private_raw_artifact_is_rejected_before_persistence(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    source = tmp_path / "private.raw"
    source.write_bytes(b"synthetic test bytes")
    from facktry.errors import StoreError

    with pytest.raises(StoreError):
        store.register_artifact(source, role="private_raw", producer_run_id="run-1")
    assert not list(store.workspace.artifacts.rglob("*"))
