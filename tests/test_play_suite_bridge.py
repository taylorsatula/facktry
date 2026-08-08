"""Phase 14 red tests: tool-episode bridge into suite execution."""

import pytest

from core_samples import payloads
from play_samples import CounterWorld, NeverStops
from suite_registry import suite_data


def test_tool_episode_case_runs_through_play_into_normal_scorecard(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry import suite, types
    from facktry.store import Store
    from facktry.workspace import resolve_workspace

    store = Store(resolve_workspace())
    data = suite_data()
    data["cases"][0]["kind"] = "tool_episode"
    data["cases"][0]["world"] = "counter"
    data["cases"][0]["scenario"] = {"seed": 1}
    value = suite.Suite.from_dict(data)
    store.register_suite(value)
    scorecard = suite.run_suite(store, (value.id, value.content_hash()), types.ReleaseTuple.from_dict(payloads()["ReleaseTuple"]), NeverStops(), seeds=[1], decode={"temperature": 0}, worlds={"counter": CounterWorld()})
    assert scorecard.subject_tuple_hash
    assert scorecard.dimensions
