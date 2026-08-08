"""Phase 16 red tests: retries, fallback, and quiet logging."""

import json

from serve_samples import ScriptedModel, guard_policy


def test_retry_cap_is_bounded_and_unclassifiable_failure_falls_back(tmp_path, monkeypatch):
    from facktry.serve import RequestServer

    backend = ScriptedModel(failures=[ValueError("unclassifiable"), ValueError("unclassifiable"), ValueError("unclassifiable")])
    server = RequestServer(backend, guard_policy(), retry_cap=2)
    result = server.generate({"messages": [{"role": "user", "content": "hello"}]})
    assert backend.calls == 1
    assert result.guarded_text
    assert len(result.guarded_text) < 200
    assert "truth" in result.guarded_text.lower() or "unable" in result.guarded_text.lower()


def test_retryable_guard_failure_stops_at_cap(tmp_path, monkeypatch):
    from facktry.serve import RequestServer

    backend = ScriptedModel(outputs=[{"text": "{bad json"}] * 5)
    server = RequestServer(backend, guard_policy(), retry_cap=2)
    result = server.generate({"messages": [{"role": "user", "content": "hello"}]})
    assert backend.calls <= 3
    assert result.guarded_text


def test_raw_and_guarded_response_records_are_both_emitted_without_private_text(tmp_path, monkeypatch):
    from facktry.serve import RequestServer

    backend = ScriptedModel(outputs=[{"text": "safe response CANARY-777"}])
    server = RequestServer(backend, guard_policy(), log_dir=tmp_path)
    result = server.generate({"messages": [{"role": "user", "content": "PRIVATE-REQUEST-111"}]})
    assert result.raw_record
    assert result.guarded_record
    for path in tmp_path.rglob("*"):
        if path.is_file():
            text = path.read_text(errors="ignore")
            assert "PRIVATE-REQUEST-111" not in text
    data = json.dumps(result.to_dict())
    assert "raw" in data and "guarded" in data
