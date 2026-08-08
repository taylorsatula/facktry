"""Phase 13 red tests: reference preservation and post-preference gates."""

import copy

import pytest

from api_support import api_for
from core_samples import HASH, payloads
from train_samples import preference_pair, train_spec
from train_support import train_store


def test_tampered_reference_tuple_is_refused_and_hash_is_carded(tmp_path, monkeypatch):
    store = train_store(tmp_path, monkeypatch)
    from facktry.train.preference import run_preference
    from facktry.train.testing import FakePreferenceBackend
    from facktry.errors import TrainRefusal

    reference = payloads()["ReleaseTuple"]
    bad = copy.deepcopy(reference)
    bad["tuple_hash"] = "b" * 64
    with pytest.raises(TrainRefusal):
        run_preference(store, "objective-valid", train_spec(reference_tuple=bad), [preference_pair()], FakePreferenceBackend())
    result = run_preference(store, "objective-valid", train_spec(reference_tuple=reference), [preference_pair()], FakePreferenceBackend(reference_hash=HASH))
    assert result.train_card.reference_tuple_hash == reference["tuple_hash"]


def test_preference_margin_with_task_hard_gate_regression_cannot_promote(tmp_path, monkeypatch):
    store = train_store(tmp_path, monkeypatch)
    from facktry.train.preference import run_preference
    from facktry.train.testing import FakePreferenceBackend
    from facktry import decide, types
    from decision_samples import admission, budget, scorecard, train_card, objective_gate

    result = run_preference(store, "objective-valid", train_spec(), [preference_pair()], FakePreferenceBackend(preference_margin=0.9))
    task_regression = objective_gate(observed=0.2, passed=False, name="task_correctness")
    task_regression["severity"] = "hard"
    decision = decide.decide(store, "objective-valid", scorecards=[types.Scorecard.from_dict(scorecard([task_regression]))], admission=types.AdmissionReport.from_dict(admission()), train_cards=[result.train_card], budget=types.BudgetLedger.from_dict(budget()))
    assert decision.action.value in {"correct", "hold"}
    assert decision.action.value != "promote"


def test_post_preference_decide_requires_non_preference_hard_suites(tmp_path, monkeypatch):
    store = train_store(tmp_path, monkeypatch)
    from facktry import decide, types
    from decision_samples import admission, budget, scorecard

    preference_only = types.Scorecard.from_dict(scorecard([{"name": "preference_margin", "severity": "soft", "comparator": ">=", "threshold": 0.5, "suite_ref": "preference", "checker_ref": "pref", "channel": "raw", "observed": 0.9, "passed": True, "evidence": []}]))
    decision = decide.decide(store, "objective-valid", scorecards=[preference_only], admission=types.AdmissionReport.from_dict(admission()), train_cards=[], budget=types.BudgetLedger.from_dict(budget()))
    assert decision.action.value != "promote"
    assert any(not gate.passed for gate in decision.gate_results)
