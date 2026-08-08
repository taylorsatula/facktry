"""Phase 04 red tests: smoke, suite-pin, and scale prerequisites."""

import copy

import pytest

from core_samples import HASH, payloads
from govern_support import frozen_store, store_for


def test_suite_pin_required_rejects_unpinned_objective(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry import types
    from facktry.govern import suite_pin_required
    from facktry.errors import SuiteNotPinned

    data = copy.deepcopy(payloads()["Objective"])
    data["id"] = "objective-unpinned"
    data["suites"]["seal"] = {"ref": "suite-seal", "hash": None}
    store.save_objective(types.Objective.from_dict(data))
    with pytest.raises(SuiteNotPinned):
        suite_pin_required(store, "objective-unpinned")


def test_pinned_objective_satisfies_suite_requirement(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry.govern import suite_pin_required

    assert suite_pin_required(store, "objective-valid") is None


def test_smoke_then_scale_rejects_without_smoke(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry.govern import smoke_then_scale
    from facktry.errors import SmokeGateUnsatisfied

    with pytest.raises(SmokeGateUnsatisfied):
        smoke_then_scale(store, "objective-valid", {"code_hash": HASH, "admission_report_hash": HASH, "memory_envelope": {}})


def test_smoke_then_scale_rejects_failed_smoke(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry import types
    from facktry.govern import smoke_then_scale
    from facktry.errors import SmokeGateUnsatisfied

    run_data = copy.deepcopy(payloads()["Run"])
    run_data.update({"run_id": "smoke-failed", "stage": "train_smoke", "status": "failed"})
    store.create_run(types.Run.from_dict(run_data))
    with pytest.raises(SmokeGateUnsatisfied):
        smoke_then_scale(store, "objective-valid", {"smoke_run_id": "smoke-failed", "code_hash": HASH, "admission_report_hash": HASH, "memory_envelope": {}})


def test_smoke_then_scale_rejects_admission_hash_mismatch(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry import types
    from facktry.govern import smoke_then_scale
    from facktry.errors import SmokeGateUnsatisfied

    run_data = copy.deepcopy(payloads()["Run"])
    run_data.update({"run_id": "smoke-complete", "stage": "train_smoke", "status": "completed"})
    store.create_run(types.Run.from_dict(run_data))
    decision = copy.deepcopy(payloads()["Decision"])
    decision.update({"objective_id": "objective-valid", "subject": {"smoke_run_id": "smoke-complete", "scale_allowed": True}})
    store.save_decision(types.Decision.from_dict(decision))
    with pytest.raises(SmokeGateUnsatisfied):
        smoke_then_scale(store, "objective-valid", {"smoke_run_id": "smoke-complete", "code_hash": HASH, "admission_report_hash": "b" * 64, "memory_envelope": {}})
