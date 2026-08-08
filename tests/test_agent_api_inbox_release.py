"""Phase 09 red tests: inbox resolution, release pinning, and secrets."""

import json

import pytest

from api_support import api_for
from core_samples import payloads


def test_invalid_inbox_response_is_rejected_and_valid_response_resolves_gate(tmp_path, monkeypatch):
    api, store = api_for(tmp_path, monkeypatch)
    item = api.inbox_ingest({"objective_id": "objective-valid", "gate_name": "taste", "response_schema": {"type": "boolean"}, "response": True, "reviewer": "human-1"})
    assert item.ok
    item_id = item.data["id"]
    invalid = api.inbox_ingest(item_id, {"response": "not-a-boolean"})
    assert not invalid.ok
    valid = api.inbox_ingest(item_id, {"response": True, "reviewer": "human-1"})
    assert valid.ok
    assert store.pending_inbox() == []


def test_yield_release_requires_human_promote_satisfaction(tmp_path, monkeypatch):
    api, _ = api_for(tmp_path, monkeypatch)
    tuple_data = payloads()["ReleaseTuple"]
    refused = api.yield_release("objective-valid", tuple_data)
    assert not refused.ok
    assert "human" in refused.error["reason"].lower()


def test_yield_release_pins_tuple_after_valid_human_ingest(tmp_path, monkeypatch):
    api, store = api_for(tmp_path, monkeypatch)
    tuple_data = payloads()["ReleaseTuple"]
    item = api.inbox_ingest({"objective_id": "objective-valid", "gate_name": "human_promote", "response_schema": {"type": "boolean"}, "response": True, "reviewer": "human-1"})
    assert item.ok
    result = api.yield_release("objective-valid", tuple_data, human_request_id=item.data["id"])
    assert result.ok
    assert result.data["tuple_hash"]
    assert store.pinned_production_tuple().tuple_hash == tuple_data["tuple_hash"]


def test_named_secret_value_never_reaches_persisted_specs_or_artifacts(tmp_path, monkeypatch):
    api, store = api_for(tmp_path, monkeypatch)
    monkeypatch.setenv("FACKTRY_TEST_SECRET", "DO-NOT-PERSIST-123")
    result = api.run_stage("unregistered", "objective-valid", {"secret_name": "FACKTRY_TEST_SECRET"})
    assert not result.ok
    for path in store.workspace.root.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".jsonl", ".md", ".log"}:
            assert "DO-NOT-PERSIST-123" not in path.read_text(errors="ignore")
