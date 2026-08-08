"""Phase 09 red tests: inbox resolution, release pinning, and secrets."""

from api_support import api_for, pending_inbox_item
from core_samples import payloads
from phase17_samples import FixtureDomain


def test_invalid_inbox_response_is_rejected_and_valid_response_resolves_gate(tmp_path, monkeypatch):
    api, store = api_for(tmp_path, monkeypatch)
    item = pending_inbox_item(store, item_id="inbox-taste")

    invalid = api.inbox_ingest(item.id, {"response": "not-a-boolean", "reviewer": "human-1"})
    assert invalid.error["type"] == "SchemaError"
    assert invalid.error["reason"] == "schema_invalid"
    assert invalid.error["details"]["field"] == "response"
    assert store.pending_inbox()[0].id == item.id

    valid = api.inbox_ingest(item.id, {"response": True, "reviewer": "human-1"})
    assert valid.ok
    assert valid.data["status"] == "answered"
    assert valid.data["reviewer"] == "human-1"
    assert store.pending_inbox() == []


def test_yield_release_requires_human_promote_satisfaction(tmp_path, monkeypatch):
    api, _ = api_for(tmp_path, monkeypatch)
    tuple_data = payloads()["ReleaseTuple"]
    refused = api.yield_release("objective-valid", tuple_data)
    assert refused.error["type"] == "HumanPromoteRequired"
    assert refused.error["reason"] == "human_promote_required"
    assert refused.error["details"]["objective_id"] == "objective-valid"


def test_yield_release_pins_tuple_after_valid_human_ingest(tmp_path, monkeypatch):
    api, store = api_for(tmp_path, monkeypatch)
    tuple_data = payloads()["ReleaseTuple"]
    item = pending_inbox_item(store, item_id="inbox-promote", gate_name="human_promote")
    assert api.inbox_ingest(item.id, {"response": True, "reviewer": "human-1"}).ok

    result = api.yield_release("objective-valid", tuple_data, human_request_id=item.id)
    assert result.ok
    assert result.data["tuple_hash"] == tuple_data["tuple_hash"]
    assert store.pinned_production_tuple().tuple_hash == tuple_data["tuple_hash"]


def test_named_secret_value_never_reaches_persisted_specs_or_artifacts(tmp_path, monkeypatch):
    api, store = api_for(tmp_path, monkeypatch)
    monkeypatch.setenv("FACKTRY_TEST_SECRET", "DO-NOT-PERSIST-123")
    from facktry.domains import register_domain

    register_domain(FixtureDomain("fixture-secret"))
    result = api.run_stage("fixture_stage", "objective-valid", {"secret_name": "FACKTRY_TEST_SECRET"}, domain="fixture-secret")
    assert result.ok
    for path in store.workspace.root.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".jsonl", ".md", ".log"}:
            assert "DO-NOT-PERSIST-123" not in path.read_text(errors="ignore")
