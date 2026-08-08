"""Phase 05 red tests: deterministic parallel generation metadata."""


def test_parallel_manifest_records_global_ranges_seeds_and_counts():
    from facktry.admit import GenerationPartManifest

    manifest = GenerationPartManifest(part_id=0, start_index=0, end_index=10, seed=42, candidate_count=10, kept_count=4, rejected_count=6)
    data = manifest.to_dict()
    assert data["start_index"] == 0
    assert data["end_index"] == 10
    assert data["seed"] == 42
    assert data["candidate_count"] == 10
    assert data["kept_count"] + data["rejected_count"] == data["candidate_count"]
