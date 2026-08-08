"""Phase 05 red tests: structure, leakage, and attribution."""

import pytest

from admit_samples import row, scenario, valid_rows
from govern_support import frozen_store


def test_role_structure_failure_happens_before_generation():
    from facktry.admit import AdmitRejection, validate_scenario

    invalid = scenario()
    invalid["visible_input"]["messages"] = [{"role": "assistant", "content": "wrong first role"}]
    with pytest.raises(AdmitRejection):
        validate_scenario(invalid)


def test_dependence_key_leakage_between_train_and_dev_is_hard_failure(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry.admit import admit

    report = admit(store, "objective-valid", [row("train", "train", "same"), row("dev", "dev", "same")], for_training=False)
    assert not report.passed
    assert "thread_id" in str(report).lower()


def test_dependence_key_leakage_against_existing_admitted_rows_is_rejected(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry.admit import admit

    first = admit(store, "objective-valid", [row("first", "train", "existing")], for_training=False)
    assert first.passed
    second = admit(store, "objective-valid", [row("second", "dev", "existing")], for_training=False)
    assert not second.passed


def test_hidden_generator_context_is_not_attributed(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry.admit import admit

    hidden = row("hidden", target="The hidden scenario says the answer is red.")
    hidden["generator_context"] = {"hidden_brief": "The answer is red."}
    report = admit(store, "objective-valid", [hidden], for_training=False)
    assert not report.passed
    assert "attribution" in str(report).lower() or "hidden" in str(report).lower()


def test_visible_input_fact_is_attributable(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry.admit import admit

    report = admit(store, "objective-valid", [row("visible")], for_training=False)
    assert report.passed


def test_invalid_role_sequence_is_rejected_on_materialized_row(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry.admit import admit

    invalid = row("bad")
    invalid["visible_input"]["messages"] = [{"role": "user", "content": "x"}, {"role": "user", "content": "y"}]
    report = admit(store, "objective-valid", [invalid], for_training=False)
    assert not report.passed
