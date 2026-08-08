"""Phase 07 red tests: sealed blindness and paired comparison."""

import pytest

from core_samples import payloads
from suite_registry import suite_data


class NeverStops:
    def generate(self, messages, decode_config, tools):
        return {"text": "continue", "stop": False}


def test_sealed_planner_api_returns_no_case_text_private_state_or_transcript(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry import suite, types
    from facktry.store import Store
    from facktry.workspace import resolve_workspace

    store = Store(resolve_workspace())
    sealed = suite.Suite.from_dict(suite_data(split="seal"))
    store.register_suite(sealed)
    subject = types.ReleaseTuple.from_dict(payloads()["ReleaseTuple"])
    result = suite.run_suite(store, (sealed.id, sealed.content_hash()), subject, NeverStops(), seeds=[1], decode={"temperature": 0})
    rendered = repr(result.to_dict())
    assert "SEALED-STEM" not in rendered
    assert "private_state" not in rendered
    assert "visible_input" not in rendered


def test_compare_emits_paired_deltas_slices_and_margin_verdicts(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry import suite, types
    from facktry.store import Store
    from facktry.workspace import resolve_workspace

    store = Store(resolve_workspace())
    value = suite.Suite.from_dict(suite_data())
    store.register_suite(value)
    subject = types.ReleaseTuple.from_dict(payloads()["ReleaseTuple"])
    report = suite.compare(store, (value.id, value.content_hash()), {"base": subject, "candidate": subject}, lambda _: NeverStops(), {"correctness": 0.0})
    assert report.paired_deltas
    assert report.slices
    assert report.margin_verdicts


def test_compare_requires_base_and_candidate(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry import suite, types
    from facktry.errors import SuiteError
    from facktry.store import Store
    from facktry.workspace import resolve_workspace

    store = Store(resolve_workspace())
    value = suite.Suite.from_dict(suite_data())
    store.register_suite(value)
    subject = types.ReleaseTuple.from_dict(payloads()["ReleaseTuple"])
    for tuples in ({"candidate": subject}, {"base": subject}):
        with pytest.raises(SuiteError, match="base|candidate"):
            suite.compare(store, (value.id, value.content_hash()), tuples, lambda _: NeverStops(), {"correctness": 0.0})


def test_multiturn_runner_hard_caps_backend_that_never_stops(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry import suite, types
    from facktry.store import Store
    from facktry.workspace import resolve_workspace

    store = Store(resolve_workspace())
    data = suite_data()
    data["metadata"] = {"dialogue": True, "max_turns": 3}
    data["cases"][0]["kind"] = "multi_turn"
    value = suite.Suite.from_dict(data)
    store.register_suite(value)
    subject = types.ReleaseTuple.from_dict(payloads()["ReleaseTuple"])
    scorecard = suite.run_suite(store, (value.id, value.content_hash()), subject, NeverStops(), seeds=[1], decode={"temperature": 0})
    assert scorecard.dimensions["resources"]["max_turns"] == 3


def test_dialogue_suite_without_multiturn_case_fails_registration(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry import suite
    from facktry.store import Store
    from facktry.workspace import resolve_workspace
    from facktry.errors import StoreError

    store = Store(resolve_workspace())
    data = suite_data()
    data["metadata"] = {"dialogue": True}
    with pytest.raises(StoreError):
        store.register_suite(suite.Suite.from_dict(data))
