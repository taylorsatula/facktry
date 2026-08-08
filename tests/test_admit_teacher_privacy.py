"""Phase 05 red tests: source class, teacher identity, and suite pin."""

import pytest

from admit_samples import row
from govern_support import frozen_store, store_for


def test_unlabeled_source_class_is_rejected(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry.admit import admit

    unlabeled = row("unlabeled")
    unlabeled["source_class"] = None
    assert not admit(store, "objective-valid", [unlabeled], for_training=False).passed


def test_private_raw_row_is_rejected_and_not_persisted(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry.admit import admit

    private = row("private", source_class="private_raw")
    report = admit(store, "objective-valid", [private], for_training=False)
    assert not report.passed
    assert not list(store.workspace.artifacts.rglob("private"))


def test_specialist_teacher_is_rejected_without_self_distill_waiver(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry.admit import admit

    specialist = row("specialist", teacher_id="production-specialist")
    report = admit(store, "objective-valid", [specialist], for_training=False)
    assert not report.passed
    assert "teacher" in str(report).lower() or "distill" in str(report).lower()


def test_base_teacher_is_accepted(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry.admit import admit

    assert admit(store, "objective-valid", [row("base", teacher_id="base")], for_training=False).passed


def test_training_admission_requires_frozen_sealed_suite_hash(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry import types
    from facktry.admit import admit
    from facktry.errors import SuiteNotPinned
    from core_samples import payloads

    data = payloads()["Objective"]
    data["id"] = "objective-unpinned-admit"
    data["suites"]["seal"] = {"ref": "suite-seal", "hash": None}
    store.save_objective(types.Objective.from_dict(data))
    with pytest.raises(SuiteNotPinned):
        admit(store, "objective-unpinned-admit", [row("train")], for_training=True)
