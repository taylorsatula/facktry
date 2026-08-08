"""Phase 01 red tests: exact str-valued enum contracts."""

import pytest


EXPECTED = {
    "RunStatus": {"pending", "running", "completed", "failed", "guarded", "blocked"},
    "Severity": {"hard", "soft", "human", "diagnostic"},
    "Channel": {"raw", "guarded", "n/a"},
    "DecisionAction": {"promote", "hold", "correct", "abort", "ask_human"},
    "InterventionClass": {"data", "mixture", "rubric", "hparam", "interface", "stop"},
    "DefectStatus": {"open", "closed", "wont_fix"},
    "InboxStatus": {"pending", "answered", "expired"},
    "Split": {"dev", "seal"},
    "SourceClass": {
        "public", "fictional", "private_redacted", "private_raw", "synthetic",
        "replay", "preference", "train", "dev", "seal", "report", "checkpoint",
        "tuple", "decision", "scorecard", "admission", "mission_brief", "recipe",
        "recipe_stack", "recipe_evidence", "log",
    },
}


@pytest.mark.parametrize("name,values", EXPECTED.items())
def test_enum_values_are_exact_str_members(name, values):
    from facktry import types

    enum = getattr(types, name)
    assert {member.value for member in enum} == values
    assert all(isinstance(member.value, str) for member in enum)


def test_unknown_enum_value_is_a_typed_serde_error():
    from facktry import types
    from facktry.errors import SerdeError

    payload = {"name": "gate", "severity": "not-a-severity", "comparator": "==", "threshold": 1, "channel": "n/a", "passed": False, "evidence": []}
    with pytest.raises(SerdeError):
        types.Gate.from_dict(payload)
