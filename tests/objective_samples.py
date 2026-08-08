"""Complete, non-sensitive Objective/MissionBrief fixtures for Phase 03/04."""

from core_samples import HASH


VALID_BRIEF = {
    "id": "brief-valid",
    "version": 1,
    "brief_hash": HASH,
    "parent_version": None,
    "operator_session_id": "session-valid",
    "raw_mission": "Improve the documented task behavior.",
    "dossier": {
        "intent": "Improve the documented task behavior.",
        "deliverable": "release_tuple",
        "domain": "test",
        "task": "grounded response",
        "audience": "test users",
        "success_case": "The model answers from visible evidence.",
        "failure_cases": ["Unsupported claims"],
        "anti_goals": ["No hidden-context answers"],
        "baselines": {"base": "base-model"},
        "must_not_regress": ["capability retention"],
        "constraints": {"privacy": "synthetic", "budget": "small"},
        "evaluation_plan": {"dev": "suite-dev", "seal": "suite-seal"},
        "questions": [{"prompt": "Approve task gate?", "answer": "yes"}],
        "assumptions": [],
    },
    "hard_gate_approvals": [{"gate": "task_correctness", "approved": True, "reviewer": "human-1"}],
    "research_notes": [{"summary": "bounded research note", "ref": "paper:1", "retrieved_at": "2026-08-08"}],
    "recipe_considerations": [{"recipe_id": "effect-a", "version": "0.1.0", "decision": "considered", "tradeoff": "none"}],
    "objective_ref": None,
    "created_at": "2026-08-08T00:00:00Z",
}

VALID_OBJECTIVE = {
    "id": "objective-valid",
    "mission_brief": {"id": "brief-valid", "version": 1, "brief_hash": HASH},
    "intent": "Improve the documented task behavior.",
    "deliverable": "release_tuple",
    "gates": [{
        "name": "task_correctness",
        "severity": "hard",
        "comparator": ">=",
        "threshold": 0.9,
        "suite_ref": "suite-seal",
        "checker_ref": "checker-task",
        "channel": "raw",
        "observed": None,
        "passed": None,
        "evidence": [],
    }],
    "constraints": {"no_self_distill": True, "pin_suites_on_first_iteration": False},
    "budget": {"wall_time": 10, "gpu_hours": 2, "judge_tokens": 1000, "smoke": 2, "scale": 1, "on_exhaustion": "hold"},
    "baselines": {"base": {"ref": "base", "tuple_hash": HASH}},
    "suites": {"dev": {"ref": "suite-dev", "hash": HASH}, "seal": {"ref": "suite-seal", "hash": HASH}},
    "dependence_keys": ["scenario_id"],
    "mixture": None,
    "policy": {"human_promote": True, "capabilities": {"admit.run": True}},
    "interface": {"prompt_policy": HASH, "tool_schema": HASH, "decode": HASH},
    "recipe_policy": {"allowed": ["effect-a"], "forbidden": [], "max_stack": 1, "budget": {"gpu_hours": 1}},
    "supersedes": None,
}


def brief_payload(**changes):
    value = dict(VALID_BRIEF)
    value["dossier"] = dict(VALID_BRIEF["dossier"])
    value.update(changes)
    return value


def objective_payload(changes=None, **kwargs):
    value = dict(VALID_OBJECTIVE)
    value["constraints"] = dict(VALID_OBJECTIVE["constraints"])
    value["budget"] = dict(VALID_OBJECTIVE["budget"])
    value["baselines"] = dict(VALID_OBJECTIVE["baselines"])
    value["suites"] = {key: dict(item) for key, item in VALID_OBJECTIVE["suites"].items()}
    value["policy"] = dict(VALID_OBJECTIVE["policy"])
    value["recipe_policy"] = dict(VALID_OBJECTIVE["recipe_policy"])
    value["gates"] = [dict(gate) for gate in VALID_OBJECTIVE["gates"]]
    value.update(changes or {})
    value.update(kwargs)
    return value
