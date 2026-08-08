"""Non-sensitive training/checkpoint fixtures for Phases 11–13."""

from core_samples import HASH, payloads


def train_spec(**changes):
    value = {
        "objective_id": "objective-valid",
        "parent_tuple": payloads()["ReleaseTuple"],
        "admission_report_hash": HASH,
        "data_refs": ["artifact:train-1"],
        "mixture": {"synthetic": 1, "replay": 1},
        "hparams": {"learning_rate": 0.0001, "steps": 5, "batch_size": 1, "adapter_rank": 4},
        "seed": 7,
        "decode": {"temperature": 0},
        "interface": {"tokenizer": HASH, "chat_template": HASH, "prompt_policy": HASH, "tool_schema": HASH, "decode": HASH},
        "memory_envelope": {"max_vram": 100},
    }
    value.update(changes)
    return value


def checkpoint(step, hard_pass=True, soft_score=0.5, loss=1.0, adapter_hash=None):
    return {
        "step": step,
        "ref": f"artifact:checkpoint-{step}",
        "adapter_hash": adapter_hash or ("b" * 63 + str(step % 10)),
        "hard_gates": {"task_correctness": hard_pass},
        "soft_scores": {"style": soft_score},
        "loss": loss,
    }


def preference_pair(pair_id="pair-1", same_input=True, same_state=True):
    visible = {"messages": [{"role": "user", "content": "The color is blue."}]}
    state = {"color": "blue"}
    return {
        "pair_id": pair_id,
        "chosen": {"visible_input": visible, "state": state, "target": "The answer is blue."},
        "rejected": {
            "visible_input": visible if same_input else {"messages": [{"role": "user", "content": "The color is green."}]},
            "state": state if same_state else {"color": "green"},
            "target": "The answer is red.",
        },
        "chosen_source": "rubric:grounding-v1",
        "rejected_defect": "unsupported_claim",
        "dependence_keys": {"scenario_id": "scenario-1"},
        "split": "train",
    }
