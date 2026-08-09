"""Phase 04 red tests: atomic multi-dimensional budget charging."""

from concurrent.futures import ThreadPoolExecutor

import pytest

from govern_support import frozen_store


def test_budget_charge_decrements_and_persists(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry.govern import BudgetCost, charge_budget

    charge_budget(store, "objective-valid", "train.smoke", BudgetCost(wall_time=2, gpu_hours=1, judge_tokens=10, smoke_runs=1, scale_runs=0))
    ledger = store.load_budget("objective-valid")
    assert ledger.wall_time == 8
    assert ledger.gpu_hours == 1
    assert ledger.smoke_runs == 1


@pytest.mark.parametrize("field", ["wall_time", "gpu_hours", "judge_tokens", "smoke_runs", "scale_runs"])
def test_insufficient_or_zero_budget_raises(field, tmp_path, monkeypatch):
    # Create objective with zero across all budget dimensions so any positive
    # charge in *any* dimension exhausts it.
    from govern_support import store_for

    store = store_for(tmp_path, monkeypatch)
    from facktry import objective, types
    from objective_samples import brief_payload, objective_payload

    objective.save_mission_brief(store, types.MissionBrief.from_dict(brief_payload()))
    empty_budget = {
        "wall_time": 0,
        "gpu_hours": 0,
        "judge_tokens": 0,
        "smoke_runs": 0,
        "scale_runs": 0,
        "on_exhaustion": "hold",
    }
    obj = types.Objective.from_dict(objective_payload({"budget": empty_budget}))
    objective.freeze_objective(store, obj)

    from facktry.govern import BudgetCost, charge_budget
    from facktry.errors import BudgetExhausted

    values = {"wall_time": 0, "gpu_hours": 0, "judge_tokens": 0, "smoke_runs": 0, "scale_runs": 0}
    values[field] = 1
    with pytest.raises(BudgetExhausted):
        charge_budget(store, "objective-valid", "test", BudgetCost(**values))


def test_concurrent_budget_charges_cannot_overspend(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry.govern import BudgetCost, charge_budget
    from facktry.errors import BudgetExhausted

    def charge():
        try:
            charge_budget(store, "objective-valid", "test", BudgetCost(wall_time=1, gpu_hours=1, judge_tokens=0, smoke_runs=0, scale_runs=0))
            return True
        except BudgetExhausted:
            return False

    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(lambda _: charge(), range(20)))
    assert sum(results) <= 2
    assert store.load_budget("objective-valid").gpu_hours >= 0
