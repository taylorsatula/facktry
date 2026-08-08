"""Phase 11 red tests: backend registry and TrainSpec boundaries."""

import pytest

from train_samples import train_spec


def test_train_backend_protocol_and_fake_backend_are_available():
    from facktry.train import TrainBackend, TrainSpec, register_backend
    from facktry.train.testing import FakeBackend

    spec = TrainSpec.from_dict(train_spec())
    backend = FakeBackend()
    assert isinstance(backend.method, str)
    assert hasattr(backend, "train")
    register_backend(backend.method, backend)
    assert spec.parent_tuple


def test_training_without_passing_admission_hash_is_refused(tmp_path, monkeypatch):
    from train_support import train_store
    store = train_store(tmp_path, monkeypatch)
    from facktry import train
    from facktry.errors import AdmitRejection

    with pytest.raises(AdmitRejection):
        train.run(store, "objective-valid", train_spec(admission_report_hash="missing"), backend="fake")


def test_hparams_outside_objective_bounds_fail_before_backend_call(tmp_path, monkeypatch):
    from train_support import train_store
    store = train_store(tmp_path, monkeypatch)
    from facktry.train import TrainSpec, run
    from facktry.train.testing import FakeBackend
    from facktry.errors import TrainRefusal

    backend = FakeBackend()
    with pytest.raises(TrainRefusal):
        run(store, "objective-valid", TrainSpec.from_dict(train_spec()), backend=backend, hparams={"adapter_rank": 999999})
    assert backend.calls == []
