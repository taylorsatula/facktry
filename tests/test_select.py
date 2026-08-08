"""Phase 12 red tests: hard-constrained checkpoint selection."""

import pytest

from train_samples import checkpoint
from train_support import train_store


def seed_checkpoints(store, run_id="run-train"):
    store.save_checkpoint_set(run_id, [checkpoint(1, hard_pass=True, soft_score=0.4, loss=1.0), checkpoint(2, hard_pass=True, soft_score=0.8, loss=0.8), checkpoint(3, hard_pass=False, soft_score=1.0, loss=0.1)])
    return run_id


def test_select_does_not_choose_last_step_when_hard_probe_prefers_earlier(tmp_path, monkeypatch):
    store = train_store(tmp_path, monkeypatch)
    from facktry import select

    run_id = seed_checkpoints(store)
    ranking = select.select_checkpoint(store, "objective-valid", run_id, soft_objectives=[{"name": "style", "direction": "maximize"}], hard_constraints=[{"name": "task_correctness", "floor": True}])
    assert ranking.winner.step == 2
    assert ranking.winner.step != 3


def test_selection_refuses_missing_or_loss_only_soft_objectives(tmp_path, monkeypatch):
    store = train_store(tmp_path, monkeypatch)
    from facktry import select
    from facktry.errors import SelectionRefusal

    run_id = seed_checkpoints(store)
    with pytest.raises(SelectionRefusal):
        select.select_checkpoint(store, "objective-valid", run_id, soft_objectives=[], hard_constraints=[])
    with pytest.raises(SelectionRefusal):
        select.select_checkpoint(store, "objective-valid", run_id, soft_objectives=[{"name": "train_loss", "direction": "minimize"}], hard_constraints=[])


def test_checkpoint_missing_hard_gate_evidence_cannot_win(tmp_path, monkeypatch):
    store = train_store(tmp_path, monkeypatch)
    from facktry import select

    store.save_checkpoint_set(
        "run-missing-evidence",
        [
            checkpoint(1, hard_pass=True, soft_score=0.4),
            {"step": 2, "ref": "artifact:checkpoint-2", "adapter_hash": "b" * 64, "hard_gates": {}, "soft_scores": {"style": 1.0}, "loss": 0.1},
        ],
    )
    ranking = select.select_checkpoint(
        store,
        "objective-valid",
        "run-missing-evidence",
        soft_objectives=[{"name": "style", "direction": "maximize"}],
        hard_constraints=[{"name": "task_correctness", "floor": True}],
    )
    assert ranking.winner.step == 1
    assert ranking.gate_matrix[2]["task_correctness"]["state"] == "missing"


def test_ranking_artifact_contains_matrix_margins_and_rationale(tmp_path, monkeypatch):
    store = train_store(tmp_path, monkeypatch)
    from facktry import select

    run_id = seed_checkpoints(store)
    ranking = select.select_checkpoint(store, "objective-valid", run_id, soft_objectives=[{"name": "style", "direction": "maximize"}], hard_constraints=[{"name": "task_correctness", "floor": True}])
    assert ranking.candidates
    assert ranking.gate_matrix
    assert ranking.margins
    assert ranking.rationale


def test_candidate_tuple_swaps_adapter_and_preserves_interface(tmp_path, monkeypatch):
    store = train_store(tmp_path, monkeypatch)
    from facktry import select
    from facktry.govern import compat_check
    from core_samples import payloads

    run_id = seed_checkpoints(store)
    candidate = select.build_candidate_tuple(store, "objective-valid", {"run_id": run_id, "step": 2, "adapter_hash": "b" * 64})
    base = payloads()["ReleaseTuple"]
    assert candidate.adapter.hash == "b" * 64
    assert candidate.tokenizer.hash == base["tokenizer"]["hash"]
    assert compat_check(base, candidate, allowed_diffs=frozenset({"adapter"})).passed
