"""Phase 13 red tests: preference pair contract."""

import pytest

from admit_samples import row
from train_samples import preference_pair
from train_support import train_store


def test_preference_pairs_require_identical_visible_input_and_state(tmp_path, monkeypatch):
    store = train_store(tmp_path, monkeypatch)
    from facktry.train.preference import admit_pairs

    report = admit_pairs(store, "objective-valid", [preference_pair(same_input=False)])
    assert not report.passed
    assert "input" in str(report).lower()
    report = admit_pairs(store, "objective-valid", [preference_pair(same_state=False)])
    assert not report.passed
    assert "state" in str(report).lower()


def test_missing_chosen_source_or_rejected_defect_is_rejected(tmp_path, monkeypatch):
    store = train_store(tmp_path, monkeypatch)
    from facktry.train.preference import admit_pairs

    missing_source = preference_pair()
    missing_source.pop("chosen_source")
    assert not admit_pairs(store, "objective-valid", [missing_source]).passed
    missing_defect = preference_pair()
    missing_defect.pop("rejected_defect")
    assert not admit_pairs(store, "objective-valid", [missing_defect]).passed


def test_random_alternate_is_not_a_valid_rejected_behavior(tmp_path, monkeypatch):
    store = train_store(tmp_path, monkeypatch)
    from facktry.train.preference import admit_pairs

    pair = preference_pair()
    pair["rejected_defect"] = "random_alternate"
    report = admit_pairs(store, "objective-valid", [pair])
    assert not report.passed


def test_preference_pair_dependence_keys_cannot_leak_across_splits(tmp_path, monkeypatch):
    store = train_store(tmp_path, monkeypatch)
    from facktry.train.preference import admit_pairs

    first = preference_pair("train-pair")
    second = preference_pair("dev-pair")
    second["split"] = "dev"
    report = admit_pairs(store, "objective-valid", [first, second])
    assert not report.passed
    assert "leak" in str(report).lower()
