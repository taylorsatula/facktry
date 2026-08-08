"""Phase 14 red tests: deterministic transcript analyzers and realism scorecard."""

from play_samples import CounterWorld, NeverStops, ScriptedPartner


def test_analyzers_are_deterministic_and_cover_required_signals():
    from facktry.play import analyze_transcript

    transcript = {
        "transcript_schema_version": "1",
        "turns": [
            {"speaker": "subject", "text": "repeat", "tool_error": False},
            {"speaker": "partner", "text": "repeat", "tool_error": True},
            {"speaker": "subject", "text": "repeat", "tool_error": False},
        ],
        "termination_reason": "turn_cap",
        "resolved": False,
    }
    first = analyze_transcript(transcript)
    second = analyze_transcript(transcript)
    assert first.to_dict() == second.to_dict()
    assert first.turn_count == 3
    assert first.repetition_detected
    assert first.unresolved_request
    assert first.tool_error_rate > 0
    assert first.termination_reason == "turn_cap"


def test_model_partner_has_separate_simulator_realism_scorecard():
    from facktry.play import run_episode

    episode = run_episode(NeverStops(), ScriptedPartner(), CounterWorld(), max_turns=2, seed=4)
    assert episode.subject_scorecard is not episode.simulator_realism_scorecard
    assert episode.simulator_realism_scorecard is not None
    assert "persona_consistency" in episode.simulator_realism_scorecard.dimensions
    assert "engagement_length" in episode.simulator_realism_scorecard.dimensions
    assert "stop_sequence" in episode.simulator_realism_scorecard.dimensions


def test_episode_export_is_replay_or_synthetic_and_excludes_private_state():
    from facktry.play import run_episode

    episode = run_episode(NeverStops(), None, CounterWorld(), max_turns=1, seed=9)
    artifact = episode.export_artifact(source_class="synthetic")
    assert artifact.role == "synthetic"
    assert "PRIVATE-ORACLE-9842" not in str(artifact.to_dict())
