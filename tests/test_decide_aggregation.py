"""Phase 08 red tests: deterministic Decision aggregation."""

import pytest

from decision_samples import admission, budget, scorecard, train_card, objective_gate
from govern_support import frozen_store


def decide_with(store, gates=None, admission_value=None, budget_value=None):
    from facktry import decide, types

    cards = [types.Scorecard.from_dict(scorecard(gates))]
    report = types.AdmissionReport.from_dict(admission_value or admission())
    trains = [types.TrainCard.from_dict(train_card())]
    ledger = types.BudgetLedger.from_dict(budget_value or budget())
    return decide.decide(store, "objective-valid", scorecards=cards, admission=report, train_cards=trains, budget=ledger)


def test_failed_hard_gate_never_promotes(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    decision = decide_with(store, [objective_gate(observed=0.5, passed=False)])
    assert decision.action.value in {"correct", "hold", "abort"}
    assert decision.action.value != "promote"


def test_pending_human_gate_routes_to_ask_human(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    decision = decide_with(store, [objective_gate(severity="human", passed=None)])
    assert decision.action.value == "ask_human"
    assert decision.human_requests


def test_soft_only_failure_never_promotes(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    decision = decide_with(store, [objective_gate(severity="soft", passed=False)])
    assert decision.action.value in {"correct", "hold"}
    assert decision.action.value != "promote"


def test_diagnostic_only_failure_does_not_block_by_itself(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    decision = decide_with(store, [objective_gate(severity="diagnostic", passed=False)])
    assert decision.action.value in {"ask_human", "promote", "hold"}
    assert any(result.severity.value == "diagnostic" for result in decision.gate_results)


@pytest.mark.parametrize("exhaustion,expected", [("hold", "hold"), ("abort", "abort")])
def test_budget_exhaustion_uses_objective_behavior(tmp_path, monkeypatch, exhaustion, expected):
    store = frozen_store(tmp_path, monkeypatch, {"budget": {"wall_time": 0, "gpu_hours": 0, "judge_tokens": 0, "smoke": 0, "scale": 0, "on_exhaustion": exhaustion}})
    decision = decide_with(store, [objective_gate()], budget_value=budget(exhausted=True, exhaustion=exhaustion))
    assert decision.action.value == expected


def test_missing_gate_evidence_fails_closed(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    gate = objective_gate()
    gate["evidence"] = ["artifact:missing"]
    decision = decide_with(store, [gate])
    assert decision.action.value != "promote"
    assert any(not result.passed for result in decision.gate_results)


def test_human_promote_default_routes_final_success_to_ask_human(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    decision = decide_with(store, [objective_gate()])
    assert decision.action.value == "ask_human"
