"""Phase 09 red tests: structured facade results and governed provenance."""

from api_support import api_for
from objective_samples import brief_payload, objective_payload


def assert_envelope(result):
    assert isinstance(result.ok, bool)
    assert isinstance(result.status, str)
    assert result.error is None or {"type", "reason", "details"} <= set(result.error)
    assert isinstance(result.artifact_refs, list)


def test_success_and_denial_results_use_api_envelope(tmp_path, monkeypatch):
    api, _ = api_for(tmp_path, monkeypatch)
    from facktry import types

    success = api.save_mission_brief(types.MissionBrief.from_dict(brief_payload(version=2, parent_version=1)))
    assert_envelope(success)
    assert success.ok
    denial = api.freeze_objective(types.Objective.from_dict(objective_payload({"mission_brief": {"id": "missing", "version": 1, "brief_hash": "b" * 64}})))
    assert_envelope(denial)
    assert denial.error["type"] == "GovernDenial.MissionBriefRequired"
    assert denial.error["reason"] == "mission_brief_required"
    assert denial.error["details"]["objective_id"] == objective_payload()["id"]


def test_experiment_without_matching_brief_returns_typed_error(tmp_path, monkeypatch):
    from govern_support import store_for
    from facktry.agent_api import AgentAPI
    from facktry import types

    store = store_for(tmp_path, monkeypatch)
    store.save_objective(types.Objective.from_dict(objective_payload()))
    result = AgentAPI(store).run_stage("unregistered", "objective-valid", {"stage": "admit"})
    assert_envelope(result)
    assert result.error["type"] == "GovernDenial.MissionBriefRequired"
    assert result.error["reason"] == "mission_brief_required"
    assert result.error["details"]["objective_id"] == "objective-valid"


def test_query_surface_returns_structured_read_results(tmp_path, monkeypatch):
    api, _ = api_for(tmp_path, monkeypatch)
    calls = {
        "query_objectives": (), "query_runs": (), "query_run": ("run-1",),
        "query_decisions": (), "query_defects": (), "query_inbox": (),
        "query_budget": ("objective-valid",), "query_pins": (), "query_metrics_tail": ("run-1", 10),
    }
    for name, args in calls.items():
        result = getattr(api, name)(*args)
        assert_envelope(result)
        assert result.ok
