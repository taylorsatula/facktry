"""Phase 17 red test: complete governed control-loop conformance path."""

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.integration]

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
    assert api.pin_suites(objective.id, ["suite-dev", "suite-seal"]).ok
    assert api.generate_and_admit(objective.id, {"rows": [{"text": "synthetic"}]}).ok
    smoke = api.train_smoke(objective.id, {})
    assert smoke.ok
    assert api.decide(objective.id).ok
    assert api.train_scale(objective.id, {}).ok
    selected = api.select_checkpoint(objective.id, {})
    assert selected.ok
    candidate_ref = selected.data["candidate_ref"]
    measured = api.measure(objective.id, {"candidate_ref": candidate_ref})
    assert measured.ok
    compared = api.compare(objective.id, {"candidate_ref": candidate_ref})
    assert compared.ok
    decision = api.decide(objective.id)
    assert decision.ok
    inbox = api.inbox_list().data
    assert inbox
    assert api.inbox_ingest(inbox[0]["id"], {"answer": "promote"}).ok
    release = api.yield_release(objective.id, candidate_ref, human_request_id=inbox[0]["id"])
    assert release.ok
    assert release.data["pinned"] is True
    assert release.data["dossier_hash"]


def test_control_loop_denies_out_of_order_or_missing_brief(tmp_path, monkeypatch):
    api, _ = api_for(tmp_path, monkeypatch)
    from facktry.errors import GovernDenial

    result = api.train_scale("objective-without-brief", {})
    assert result.error["type"] == "GovernDenial.MissionBriefRequired"
    assert result.error["reason"] == "mission_brief_required"
    assert result.error["details"]["objective_id"] == "objective-without-brief"
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
