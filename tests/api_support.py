"""Test-only helpers for Phase 09 agent API red tests."""

from core_samples import payloads
from govern_support import frozen_store


def api_for(tmp_path, monkeypatch, objective_changes=None):
    store = frozen_store(tmp_path, monkeypatch, objective_changes)
    from facktry.agent_api import AgentAPI

    return AgentAPI(store), store


def pending_inbox_item(store, *, item_id="inbox-test", objective_id="objective-valid", gate_name="taste", response_schema=None):
    """Persist a pending item through the store primitive; facade ingest never creates items."""
    from copy import deepcopy
    from facktry import types

    data = deepcopy(payloads()["HumanInboxItem"])
    data.update({
        "id": item_id,
        "objective_id": objective_id,
        "gate_name": gate_name,
        "response_schema": response_schema or {"type": "boolean"},
        "status": "pending",
    })
    item = types.HumanInboxItem.from_dict(data)
    store.save_inbox_item(item)
    return item
