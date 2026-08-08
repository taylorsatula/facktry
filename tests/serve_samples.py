"""Non-sensitive ReleaseTuple and serving fixtures for Phase 16 red tests."""

from core_samples import HASH, payloads


def tuple_payload(**changes):
    value = {key: (item.copy() if isinstance(item, dict) else item) for key, item in payloads()["ReleaseTuple"].items()}
    value.update(changes)
    return value


def guard_policy(**changes):
    value = {
        "id": "guards-1",
        "version": "1",
        "guards": [
            {"name": "unsupported_action", "action": "block", "config": {}},
            {"name": "claim_not_executed", "action": "fallback", "config": {}},
            {"name": "privacy", "action": "block", "config": {"canaries": ["CANARY-777"]}},
            {"name": "repetition", "action": "rewrite", "config": {"max_repeats": 1}},
            {"name": "mode_leak", "action": "block", "config": {}},
            {"name": "schema", "action": "fallback", "config": {}},
        ],
        "policy_hash": HASH,
    }
    value.update(changes)
    return value


class ScriptedModel:
    def __init__(self, outputs=None, failures=None):
        self.outputs = list(outputs or [{"text": "safe response"}])
        self.failures = list(failures or [])
        self.calls = 0

    def generate(self, request):
        self.calls += 1
        if self.failures:
            failure = self.failures.pop(0)
            raise failure
        return self.outputs[min(self.calls - 1, len(self.outputs) - 1)]
