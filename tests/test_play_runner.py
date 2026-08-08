"""Phase 14 red tests: World protocol, caps, and private-state hygiene."""

import json

import pytest

from play_samples import CounterWorld, NeverStops, ScriptedPartner


def test_toy_world_protocol_is_deterministic_and_versioned():
    from facktry.play import validate_world, run_episode

    world = CounterWorld()
    validate_world(world)
    assert world.reset(3, {}) == world.reset(3, {})
    observation, done, info = world.step({"name": "increment"})
    assert observation["observation"] == "count:4"
    assert done is False
    assert info["tool_ok"]
    transcript = world.export_transcript()
    assert transcript["transcript_schema_version"]


def test_runner_enforces_hard_turn_cap_on_never_stopping_subject():
    from facktry.play import run_episode

    subject = NeverStops()
    episode = run_episode(subject, None, CounterWorld(), max_turns=3, seed=11)
    assert episode.turn_count == 3
    assert episode.termination_reason == "turn_cap"
    assert len(subject.calls) == 3


def test_stop_tokens_are_advisory_not_a_cap_bypass():
    from facktry.play import run_episode

    subject = NeverStops()
    episode = run_episode(subject, ScriptedPartner(), CounterWorld(), max_turns=2, seed=1)
    assert episode.turn_count <= 2
    assert episode.termination_reason == "turn_cap"


def test_private_oracle_state_is_absent_from_prompts_transcript_and_open_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry.play import run_episode

    subject = NeverStops()
    episode = run_episode(subject, None, CounterWorld(), max_turns=2, seed=2)
    rendered_episode = json.dumps(episode.to_dict())
    rendered_prompts = json.dumps(subject.calls)
    assert "PRIVATE-ORACLE-9842" not in rendered_episode
    assert "PRIVATE-ORACLE-9842" not in rendered_prompts
    assert "oracle_state" not in rendered_episode


def test_unauthorized_action_is_rejected_before_world_step():
    from facktry.play import PlayRejection, run_episode

    subject = NeverStops(action={"name": "delete_database"})
    world = CounterWorld()
    with pytest.raises(PlayRejection):
        run_episode(subject, None, world, max_turns=2, seed=1)
    assert world.steps == []
