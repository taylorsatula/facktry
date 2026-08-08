"""Phase 02 red tests: append-only metrics."""

import json

from core_samples import payloads


def store_for(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry.store import Store
    from facktry.workspace import resolve_workspace

    return Store(resolve_workspace())


def test_append_metric_and_tail_are_ordered_jsonl(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry import types

    run = types.Run.from_dict(payloads()["Run"])
    store.create_run(run)
    for step in range(3):
        store.append_metric(run.run_id, {"step": step, "loss": 1.0 - step / 10})
    assert [row["step"] for row in store.tail_metrics(run.run_id, 2)] == [1, 2]
    lines = (store.workspace.runs / run.run_id / "metrics.jsonl").read_text().splitlines()
    assert all(json.loads(line)["step"] == i for i, line in enumerate(lines))
