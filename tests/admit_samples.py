"""Non-sensitive row and admission fixtures for Phase 05 red tests."""

from core_samples import HASH


def row(row_id, split="train", thread_id="thread-1", text="Visible fact: blue.", target="The answer is blue.", source_class="synthetic", teacher_id="base"):
    return {
        "row_id": row_id,
        "split": split,
        "visible_input": {"messages": [{"role": "user", "content": text}]},
        "target": target,
        "dependence_keys": {"thread_id": thread_id, "scenario_id": thread_id},
        "source_class": source_class,
        "teacher_id": teacher_id,
        "labels": ["grounded"],
        "tags": ["family-a"],
        "transformation_policy_id": "policy-1",
        "provenance_refs": ["artifact:source-1"],
        "row_hash": HASH,
    }


def valid_rows():
    return [row("row-1"), row("row-2", thread_id="thread-2", text="Visible fact: green.", target="The answer is green.")]


def scenario():
    return {
        "scenario_id": "scenario-1",
        "visible_input": {"messages": [{"role": "user", "content": "Visible fact: blue."}]},
        "verified_state": {"color": "blue"},
        "authorized_tools": [],
        "target_shape": {"roles": ["user", "assistant"]},
    }
