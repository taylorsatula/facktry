"""Phase 07 red tests: pinned runner and scorecard population."""

import pytest

from suite_registry import suite_data
from core_samples import payloads


class ScriptedModel:
    def __init__(self, output="The color is blue."):
        self.output = output
        self.calls = []

    def generate(self, messages, decode_config, tools):
        self.calls.append((messages, decode_config, tools))
        return {"text": self.output, "tokens": 4}


def test_runner_pins_seeds_decode_and_subject_tuple(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry import suite, types
    from facktry.store import Store
    from facktry.workspace import resolve_workspace

    store = Store(resolve_workspace())
    value = suite.Suite.from_dict(suite_data())
    store.register_suite(value)
    backend = ScriptedModel()
    scorecard = suite.run_suite(store, (value.id, value.content_hash()), types.ReleaseTuple.from_dict(payloads()["ReleaseTuple"]), backend, seeds=[1, 2], decode={"temperature": 0})
    assert scorecard.seeds == [1, 2]
    assert scorecard.decode_hash
    assert scorecard.subject_tuple_hash


def test_runner_refuses_unpinned_execution(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry import suite, types
    from facktry.store import Store
    from facktry.workspace import resolve_workspace
    from facktry.errors import StoreError

    store = Store(resolve_workspace())
    backend = ScriptedModel()
    with pytest.raises(StoreError):
        suite.run_suite(store, "missing-suite", types.ReleaseTuple.from_dict(payloads()["ReleaseTuple"]), backend, seeds=None, decode=None)


def test_scorecard_contains_dimensions_or_na_and_raw_guarded_channels(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry import suite, types
    from facktry.store import Store
    from facktry.workspace import resolve_workspace

    store = Store(resolve_workspace())
    value = suite.Suite.from_dict(suite_data())
    store.register_suite(value)
    scorecard = suite.run_suite(store, (value.id, value.content_hash()), types.ReleaseTuple.from_dict(payloads()["ReleaseTuple"]), ScriptedModel(), seeds=[1], decode={"temperature": 0})
    required = {"correctness", "unsupported_claim", "abstention", "retention", "robustness", "privacy", "preference", "style", "diversity", "raw_guarded", "resources"}
    assert required <= set(scorecard.dimensions)
    assert scorecard.raw is not None
    assert scorecard.guarded is not None
    assert scorecard.slices is not None
    assert scorecard.resources is not None
