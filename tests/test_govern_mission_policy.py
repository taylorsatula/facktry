"""Phase 04 red tests: MissionBrief provenance and policy gates."""

import pytest

from core_samples import HASH
from objective_samples import brief_payload, objective_payload
from govern_support import store_for


def test_missing_or_mismatched_brief_is_required_for_experiments(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry import types
    from facktry.govern import mission_brief_required
    from facktry.errors import MissionBriefRequired

    store.save_objective(types.Objective.from_dict(objective_payload()))
    with pytest.raises(MissionBriefRequired):
        mission_brief_required(store, "objective-valid", {"stage": "admit"})


def test_matching_saved_brief_satisfies_requirement(tmp_path, monkeypatch):
    store = __import__("govern_support").frozen_store(tmp_path, monkeypatch)
    from facktry.govern import mission_brief_required

    assert mission_brief_required(store, "objective-valid", {"stage": "admit"}) is None


@pytest.mark.parametrize("capability", ["data.use_private", "data.remote_send", "serve.flip_default", "objective.supersede", "unknown.capability"])
def test_default_denied_capabilities_raise(capability, tmp_path, monkeypatch):
    store = __import__("govern_support").frozen_store(tmp_path, monkeypatch)
    from facktry.govern import check_policy
    from facktry.errors import PolicyDenied

    with pytest.raises(PolicyDenied):
        check_policy(store, "objective-valid", capability)


def test_explicitly_allowed_capability_passes(tmp_path, monkeypatch):
    store = __import__("govern_support").frozen_store(tmp_path, monkeypatch, {"policy": {"capabilities": {"admit.run": True}}})
    from facktry.govern import check_policy

    assert check_policy(store, "objective-valid", "admit.run") is None
