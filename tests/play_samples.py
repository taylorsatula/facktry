"""Deterministic toy-world and backend fixtures for Phase 14 red tests."""


class CounterWorld:
    def __init__(self):
        self.value = 0
        self.steps = []

    def reset(self, seed, scenario):
        self.value = seed
        self.steps = []
        return {"observation": f"count:{self.value}"}

    def step(self, action):
        self.steps.append(action)
        if action.get("name") != "increment":
            raise AssertionError("world received unauthorized action")
        self.value += 1
        return {"observation": f"count:{self.value}"}, False, {"tool_ok": True}

    def oracle_state(self):
        return {"secret": "PRIVATE-ORACLE-9842", "count": self.value}

    def export_transcript(self):
        return {"transcript_schema_version": "1", "turns": list(self.steps)}


class NeverStops:
    def __init__(self, action=None):
        self.calls = []
        self.action = action or {"name": "increment"}

    def generate(self, messages, decode_config=None, tools=None):
        self.calls.append({"messages": messages, "decode": decode_config, "tools": tools})
        return {"text": "continue", "action": self.action, "stop": False}


class ScriptedPartner:
    model_id = "scripted-partner"
    engagement_length = 3
    instructions = "Ask the subject for the next step."
    pain_points = ["clarity"]
    stop_sequence = "DONE"

    def generate(self, messages, decode_config=None, tools=None):
        return {"text": "partner response", "stop": False}
