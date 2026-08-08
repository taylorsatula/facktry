"""Phase 16 red tests: canary, policy-gated flip, and rollback."""

import pytest

from core_samples import payloads
from govern_support import frozen_store


def test_canary_uses_identical_paired_probes_for_production_and_candidate(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry import serve, types

    production = types.ReleaseTuple.from_dict(payloads()["ReleaseTuple"])
    candidate_data = dict(payloads()["ReleaseTuple"])
    candidate_data["adapter"] = {"ref": "candidate", "hash": "b" * 64}
    candidate = types.ReleaseTuple.from_dict(candidate_data)
    store.save_release_tuple(production)
    store.save_release_tuple(candidate)
    report = serve.canary_start(store, candidate.tuple_hash, probes=[{"input": "probe-1"}, {"input": "probe-2"}])
    assert report.production_hash == production.tuple_hash
    assert report.candidate_hash == candidate.tuple_hash
    assert report.probe_inputs == ["probe-1", "probe-2"]
    assert report.paired_deltas


def test_flip_default_requires_policy_and_promote_decision(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry import serve, types
    from facktry.errors import PolicyDenied

    candidate = types.ReleaseTuple.from_dict(payloads()["ReleaseTuple"])
    store.save_release_tuple(candidate)
    with pytest.raises(PolicyDenied):
        serve.flip_default(store, candidate.tuple_hash)


def test_flip_then_rollback_restores_previous_tuple_hash(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch, {"policy": {"capabilities": {"serve.flip_default": True}}})
    from facktry import serve, types

    first_data = dict(payloads()["ReleaseTuple"])
    first = types.ReleaseTuple.from_dict(first_data)
    second_data = dict(payloads()["ReleaseTuple"])
    second_data["adapter"] = {"ref": "candidate", "hash": "b" * 64}
    second = types.ReleaseTuple.from_dict(second_data)
    store.save_release_tuple(first)
    store.save_release_tuple(second)
    store.pin_production_tuple(first)
    store.save_promote_decision("objective-valid", second.tuple_hash)
    serve.flip_default(store, second.tuple_hash)
    assert store.pinned_production_tuple().tuple_hash == second.tuple_hash
    serve.rollback(store)
    assert store.pinned_production_tuple().tuple_hash == first.tuple_hash
