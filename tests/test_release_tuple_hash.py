"""Phase 01 red tests: complete ReleaseTuple identity."""

import copy

from core_samples import HASH, payloads


def test_tuple_hash_changes_for_each_component():
    from facktry import types

    original = payloads()["ReleaseTuple"]
    fields = ["base_model", "adapter", "tokenizer", "chat_template", "prompt_policy", "tool_schema", "decode", "guards", "recipe_stack"]
    baseline = types.ReleaseTuple.from_dict(original).compute_tuple_hash()
    for field in fields:
        changed = copy.deepcopy(original)
        if changed[field] is None:
            changed[field] = {"ref": "changed", "hash": HASH[:-1] + "b"}
        elif isinstance(changed[field], str):
            changed[field] = HASH[:-1] + "b"
        else:
            changed[field] = {**changed[field], "hash": HASH[:-1] + "b"}
        assert types.ReleaseTuple.from_dict(changed).compute_tuple_hash() != baseline, field
