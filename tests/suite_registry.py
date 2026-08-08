"""Test-only suite fixture helpers for Phase 07."""

from core_samples import HASH


def suite_data(split="dev"):
    return {
        "id": "suite-1",
        "version": "1.0.0",
        "cases": [{
            "id": "case-1", "family": "grounding", "split": split,
            "dependence_keys": {"scenario_id": "s-1"},
            "visible_input": {"messages": [{"role": "user", "content": "The color is blue."}]},
            "private_state": {"answer": "blue", "secret": "SEALED-STEM"},
            "authorized_tools": [], "verifiers": ["schema"], "tags": ["basic"], "kind": "single_turn",
        }],
        "metadata": {"dialogue": False},
        "suite_hash": HASH,
    }
