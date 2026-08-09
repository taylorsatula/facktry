"""Phase 04 red tests: ReleaseTuple interface compatibility."""

import copy

import pytest

from core_samples import HASH, payloads


@pytest.mark.parametrize("field", ["tokenizer", "chat_template", "prompt_policy", "tool_schema", "decode"])
def test_interface_drift_is_named_and_rejected(field):
    from facktry import types
    from facktry.govern import compat_check

    left = types.ReleaseTuple.from_dict(payloads()["ReleaseTuple"])
    right_data = copy.deepcopy(payloads()["ReleaseTuple"])
    if isinstance(right_data[field], str):
        right_data[field] = HASH[:-1] + "b"
    else:
        right_data[field]["hash"] = HASH[:-1] + "b"
    result = compat_check(left, types.ReleaseTuple.from_dict(right_data))
    assert not result.passed
    assert field in str(result.mismatches).lower()


def test_identical_tuples_pass_and_adapter_only_diff_can_be_allowed():
    from facktry import types
    from facktry.govern import compat_check

    left = types.ReleaseTuple.from_dict(payloads()["ReleaseTuple"])
    same = types.ReleaseTuple.from_dict(payloads()["ReleaseTuple"])
    assert compat_check(left, same).passed
    changed = copy.deepcopy(payloads()["ReleaseTuple"])
    changed["adapter"] = {"ref": "adapter-1", "hash": HASH}
    assert compat_check(left, types.ReleaseTuple.from_dict(changed), allowed_diffs=frozenset({"adapter"})).passed


def test_guard_drift_requires_declared_raw_guarded_comparison():
    from facktry import types
    from facktry.govern import compat_check

    left = types.ReleaseTuple.from_dict(payloads()["ReleaseTuple"])
    changed = copy.deepcopy(payloads()["ReleaseTuple"])
    changed["guards"] = {"ref": "other", "hash": "b" * 64}
    right = types.ReleaseTuple.from_dict(changed)
    assert not compat_check(left, right).passed
    assert compat_check(left, right, allowed_diffs=frozenset({"guards"})).passed
