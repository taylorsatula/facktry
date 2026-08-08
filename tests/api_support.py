"""Test-only helpers for Phase 09 agent API red tests."""

from govern_support import frozen_store


def api_for(tmp_path, monkeypatch, objective_changes=None):
    store = frozen_store(tmp_path, monkeypatch, objective_changes)
    from facktry.agent_api import AgentAPI

    return AgentAPI(store), store
