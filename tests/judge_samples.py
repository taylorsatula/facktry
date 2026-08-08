"""Non-sensitive scripted judge fixtures for Phase 15 red tests."""


class ScriptedJudge:
    def __init__(self, labels=None, remote=False):
        self.labels = labels or ["pass"]
        self.calls = []
        self.remote = remote

    def assess(self, batch, criteria):
        self.calls.append({"batch": batch, "criteria": criteria})
        return [{"item_id": item["item_id"], "label": self.labels[i % len(self.labels)], "score": i % 3, "rationale": "scripted rationale"} for i, item in enumerate(batch)]


def criteria(**changes):
    value = {"id": "criteria-1", "version": "1", "prompt": "Assess groundedness.", "scale": [0, 1, 2], "severity_ceiling": "soft"}
    value.update(changes)
    return value


def calibration_items():
    return [
        {"item_id": "clear-pass", "text": "pass fixture", "expected": "pass"},
        {"item_id": "clear-fail", "text": "fail fixture", "expected": "fail"},
        {"item_id": "borderline", "text": "borderline fixture", "expected": "borderline"},
    ]
