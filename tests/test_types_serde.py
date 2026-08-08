"""Phase 01 red tests: complete typed serde round trips."""

import pytest

from core_samples import payloads


@pytest.mark.parametrize("type_name", sorted(payloads()))
def test_every_core_type_round_trips_without_loss(type_name):
    from facktry import types

    cls = getattr(types, type_name)
    original = cls.from_dict(payloads()[type_name])
    restored = cls.from_dict(original.to_dict())
    assert restored == original
    assert restored.to_dict() == original.to_dict()
    if type_name == "ReleaseTuple":
        assert restored.recipe_stack is not None


def test_mission_brief_preserves_immutable_version_provenance():
    from facktry import types

    data = payloads()["MissionBrief"]
    brief = types.MissionBrief.from_dict(data)
    assert brief.version == 1
    assert brief.parent_version is None
    assert brief.hard_gate_approvals
    assert brief.research_notes
    assert brief.recipe_considerations
    assert brief.to_dict() == data


def test_missing_required_type_field_raises_typed_serde_error():
    from facktry import types
    from facktry.errors import SerdeError

    with pytest.raises(SerdeError):
        types.Artifact.from_dict({"path": "x"})
