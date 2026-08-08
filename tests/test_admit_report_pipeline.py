"""Phase 05 red tests: AdmissionReport and generate_and_admit pipeline."""

from admit_samples import row, scenario
from govern_support import frozen_store


class ScriptedGenerator:
    def __init__(self, candidates):
        self.candidates = candidates
        self.calls = []

    def generate(self, scenarios, seed):
        self.calls.append((scenarios, seed))
        return self.candidates


def test_admission_report_contains_required_evidence(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry.admit import admit

    report = admit(store, "objective-valid", [row("one"), row("two", thread_id="two")], for_training=False)
    assert report.passed
    assert report.input_artifacts
    assert report.keep_count == 2
    assert report.reject_reasons == {}
    assert report.overlap_matrix is not None
    assert report.near_dupes is not None
    assert report.template_families is not None
    assert report.suite_hash
    assert report.gate_results is not None
    assert store.latest_passing_admission("objective-valid").report_hash == report.report_hash


def test_generate_and_admit_validates_constructs_before_generator(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry.admit import AdmitRejection, generate_and_admit

    generator = ScriptedGenerator([row("candidate")])
    invalid = dict(scenario(), visible_input={"messages": [{"role": "assistant", "content": "bad"}]})
    try:
        generate_and_admit(store, "objective-valid", {"scenarios": [invalid], "generator": generator, "seed": 1, "keep_target": 1})
    except AdmitRejection:
        pass
    assert generator.calls == []


def test_generate_and_admit_runs_filter_then_admit_and_records_histogram(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry.admit import generate_and_admit

    generator = ScriptedGenerator([row("keep"), row("reject", target="Unsupported hidden claim.")])
    report = generate_and_admit(store, "objective-valid", {"scenarios": [scenario()], "generator": generator, "seed": 7, "keep_target": 1})
    assert generator.calls
    assert report.passed
    assert report.reject_reasons
    assert report.transformation_policy_id
    assert report.seeds == [7]


def test_parallel_part_manifests_merge_by_global_index_deterministically(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry.admit import merge_generation_parts

    parts = [
        {"part_id": 1, "start_index": 2, "end_index": 4, "seed": 9, "candidates": [row("2"), row("3")]},
        {"part_id": 0, "start_index": 0, "end_index": 2, "seed": 9, "candidates": [row("0"), row("1")]},
    ]
    first = merge_generation_parts(parts)
    second = merge_generation_parts(list(reversed(parts)))
    assert [item["row_id"] for item in first.rows] == ["0", "1", "2", "3"]
    assert first.merged_hash == second.merged_hash
