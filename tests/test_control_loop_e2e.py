"""Phase 17 red test: complete governed control-loop conformance path."""

import pytest

from api_support import api_for
from core_samples import payloads
from objective_samples import brief_payload, objective_payload


def test_control_loop_requires_ordered_governed_transitions_and_yields_pinned_release(tmp_path, monkeypatch):
    api, store = api_for(tmp_path, monkeypatch, {"policy": {"capabilities": {"human_promote": True}}})
    from facktry import types

    brief = types.MissionBrief.from_dict(brief_payload())
    saved = api.save_mission_brief(brief)
    assert saved.ok
    objective = types.Objective.from_dict(objective_payload({"mission_brief": {"id": brief.id, "version": brief.version, "brief_hash": brief.brief_hash}}))
    assert api.freeze_objective(objective).ok
    assert api.preflight(objective.id).ok
    assert api.pin_suites(objective.id).ok
    assert api.generate_and_admit(objective.id, {"rows": [{"text": "synthetic"}]}).ok
    smoke = api.train_smoke(objective.id)
    assert smoke.ok
    assert api.decide(smoke.data["decision_id"], action="scale").ok
    assert api.train_scale(objective.id).ok
    selected = api.select_checkpoint(objective.id)
    assert selected.ok
    measured = api.measure_and_compare(objective.id, selected.data["candidate_ref"])
    assert measured.ok
    decision = api.decide(measured.data["decision_id"], action="ask_human")
    assert decision.ok
    inbox = api.query_inbox().data
    assert inbox
    assert api.ingest_inbox(inbox[0]["id"], {"answer": "promote"}).ok
    release = api.yield_release(objective.id, selected.data["candidate_ref"])
    assert release.ok
    assert release.data["pinned"] is True
    assert release.data["dossier_hash"]


def test_control_loop_denies_out_of_order_or_missing_brief(tmp_path, monkeypatch):
    api, _ = api_for(tmp_path, monkeypatch)
    from facktry.errors import GovernDenial

    result = api.train_scale("objective-without-brief")
    assert not result.ok
    assert "brief" in result.error["reason"].lower() or "smoke" in result.error["reason"].lower()
    with pytest.raises(GovernDenial):
        api.require_mission_brief("objective-without-brief")


def test_recipe_stack_hash_propagates_through_governed_artifacts(tmp_path, monkeypatch):
    api, store = api_for(tmp_path, monkeypatch)
    stack_hash = "a" * 64
    from facktry import types

    brief = types.MissionBrief.from_dict(brief_payload())
    assert api.save_mission_brief(brief).ok
    objective = types.Objective.from_dict(objective_payload({"mission_brief": {"id": brief.id, "version": brief.version, "brief_hash": brief.brief_hash}, "recipe_stack_hash": stack_hash}))
    assert api.freeze_objective(objective).ok
    result = api.yield_release(objective.id, payloads()["ReleaseTuple"], recipe_stack_hash=stack_hash)
    assert result.ok
    assert result.data["recipe_stack_hash"] == stack_hash
    assert store.query_artifacts(recipe_stack_hash=stack_hash)
