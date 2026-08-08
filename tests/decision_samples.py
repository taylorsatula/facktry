"""Non-sensitive decision fixtures for Phase 08 red tests."""

from core_samples import HASH, payloads


def objective_gate(observed=0.95, passed=True, severity="hard", name="task_correctness"):
    return {
        "name": name,
        "severity": severity,
        "comparator": ">=",
        "threshold": 0.9,
        "suite_ref": "suite-seal",
        "checker_ref": "checker-task",
        "channel": "raw",
        "observed": observed,
        "passed": passed,
        "evidence": ["artifact:evidence-1"],
    }


def scorecard(gates=None):
    value = dict(payloads()["Scorecard"])
    value["gate_results"] = gates or [objective_gate()]
    value["subject_tuple_hash"] = HASH
    value["recipe_stack_hash"] = HASH
    return value


def admission(passed=True):
    value = dict(payloads()["AdmissionReport"])
    value["passed"] = passed
    return value


def train_card():
    return payloads()["TrainCard"]


def budget(exhausted=False, exhaustion="hold"):
    value = dict(payloads()["BudgetLedger"])
    if exhausted:
        value.update({"wall_time": 0, "gpu_hours": 0, "judge_tokens": 0, "smoke_runs": 0, "scale_runs": 0})
    value["on_exhaustion"] = exhaustion
    return value
