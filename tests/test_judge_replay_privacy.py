"""Phase 15 red tests: pairwise, replay, overseer, and privacy policy."""

import pytest

from govern_support import frozen_store
from judge_samples import ScriptedJudge, criteria


def test_pairwise_assessment_swaps_positions_and_surfaces_disagreement():
    from facktry.judge import pairwise_assess

    backend = ScriptedJudge(labels=["a", "b"])
    report = pairwise_assess({"item_id": "pair-1", "left": "A", "right": "B"}, criteria(), backend)
    assert len(backend.calls) == 2
    assert report.position_orders == [["left", "right"], ["right", "left"]]
    assert report.disagreement is not None


def test_corpus_overseer_flags_canned_openings_and_repetition():
    from facktry.judge import oversee_corpus

    items = [{"item_id": str(i), "text": "Sure, I can help. repeated content"} for i in range(4)]
    report = oversee_corpus(items, criteria())
    assert report.findings
    assert any("canned" in finding.name or "repetition" in finding.name for finding in report.findings)


def test_replay_uses_pinned_trajectory_hashes_without_regeneration(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry import judge

    store.save_artifact_bytes("trajectory-a", b"visible trajectory", role="replay")
    backend = ScriptedJudge()
    report = judge.replay(store, ["trajectory-a"], criteria(prompt="new rubric"), backend)
    assert report.source_trajectory_hashes
    assert report.criteria_hash != ""
    assert len(backend.calls) == 1
    assert backend.calls[0]["batch"][0]["item_id"] == "trajectory-a"


def test_remote_judge_redacts_private_sentinel_before_backend(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry import judge

    backend = ScriptedJudge(remote=True)
    report = judge.assess([{"item_id": "x", "text": "email alice@example.com CANARY-555"}], criteria(), backend, store=store, remote=True)
    payload = backend.calls[0]["batch"][0]["text"]
    assert "alice@example.com" not in payload
    assert "CANARY-555" not in payload
    assert report.assessments


def test_remote_judge_policy_denial_blocks_call(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch, {"policy": {"capabilities": {"judge.use": False, "data.remote_send": False}}})
    from facktry import judge
    from facktry.errors import PolicyDenied

    backend = ScriptedJudge(remote=True)
    with pytest.raises(PolicyDenied):
        judge.assess([{"item_id": "x", "text": "private"}], criteria(), backend, store=store, remote=True)
    assert backend.calls == []
