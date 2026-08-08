"""Phase 11 red tests: callback guards, probes, and keep-best."""

from train_samples import checkpoint, train_spec
from train_support import train_store


def test_nonfinite_loss_guards_run_and_saves_guard_checkpoint(tmp_path, monkeypatch):
    store = train_store(tmp_path, monkeypatch)
    from facktry.train import run
    from facktry.train.testing import FakeBackend

    result = run(store, "objective-valid", train_spec(), backend=FakeBackend(losses=[1.0, float("nan")]))
    assert result.status == "guarded"
    assert result.guard_report
    assert result.guard_checkpoint_ref
    assert store.get_artifact(result.guard_checkpoint_ref, verify=True)


def test_periodic_mini_probe_is_appended_to_metrics(tmp_path, monkeypatch):
    store = train_store(tmp_path, monkeypatch)
    from facktry.train import run
    from facktry.train.testing import FakeBackend

    result = run(store, "objective-valid", train_spec(), backend=FakeBackend(probe_scores=[0.4, 0.6], probe_every=2))
    metrics = store.tail_metrics(result.run_id, 20)
    assert any("probe" in metric for metric in metrics)


def test_keep_best_selects_midrun_checkpoint_not_last(tmp_path, monkeypatch):
    store = train_store(tmp_path, monkeypatch)
    from facktry.train import run
    from facktry.train.testing import FakeBackend

    backend = FakeBackend(checkpoints=[checkpoint(1, soft_score=0.4), checkpoint(2, soft_score=0.9), checkpoint(3, soft_score=0.2)])
    result = run(store, "objective-valid", train_spec(), backend=backend)
    assert result.train_card.best_checkpoint_ref.endswith("2")
    assert result.train_card.best_checkpoint_ref != result.checkpoints[-1].ref


def test_vram_or_budget_envelope_stops_cleanly_and_persists_best(tmp_path, monkeypatch):
    store = train_store(tmp_path, monkeypatch)
    from facktry.train import run
    from facktry.train.testing import FakeBackend

    result = run(store, "objective-valid", train_spec(memory_envelope={"max_vram": 1}), backend=FakeBackend(peak_vram=2))
    assert result.status in {"guarded", "completed"}
    assert result.train_card.best_checkpoint_ref
