"""Phase 05 red tests: diversity, vocabulary, and mixture gates."""

from admit_samples import row
from govern_support import frozen_store


def test_duplicate_inputs_and_final_turns_fail_diversity(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch, {"constraints": {"admission": {"max_duplicate_rate": 0}}})
    from facktry.admit import admit

    report = admit(store, "objective-valid", [row("a"), row("b")], for_training=False)
    assert not report.passed
    assert "duplicate" in str(report).lower()


def test_template_family_collapse_and_near_duplicates_are_reported(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch, {"constraints": {"admission": {"max_template_family_share": 0.5, "max_near_duplicate_rate": 0}}})
    from facktry.admit import admit

    rows = [row(str(i), thread_id=str(i), text="Visible fact blue", target="The answer is blue.") for i in range(4)]
    report = admit(store, "objective-valid", rows, for_training=False)
    assert not report.passed
    assert report.reject_reasons
    assert report.near_dupes
    assert report.template_families


def test_large_uniform_batch_is_not_a_diversity_pass(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch, {"constraints": {"admission": {"max_duplicate_rate": 0, "min_unique_inputs": 3}}})
    from facktry.admit import admit

    rows = [row(str(i), thread_id=str(i)) for i in range(20)]
    assert not admit(store, "objective-valid", rows, for_training=False).passed


def test_controlled_vocab_violation_is_rejected(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch, {"constraints": {"controlled_vocabs": {"labels": ["grounded"]}}})
    from facktry.admit import admit

    invalid = row("bad")
    invalid["labels"] = ["not-declared"]
    report = admit(store, "objective-valid", [invalid], for_training=False)
    assert not report.passed


def test_target_shape_floors_and_caps_are_enforced(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch, {"mixture": {"dimensions": ["source_class"], "floors": {"public": 2}, "caps": {"synthetic": 1}}})
    from facktry.admit import admit

    report = admit(store, "objective-valid", [row("a"), row("b")], for_training=False)
    assert not report.passed
    assert report.mixture_deltas
