"""Phase 16 red tests: local HTTP service lifecycle."""

import json
from urllib.request import Request, urlopen

import pytest

from serve_samples import ScriptedModel, guard_policy, tuple_payload

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def test_http_service_exposes_health_and_raw_guarded_generate(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry import serve, types
    from facktry.store import Store
    from facktry.workspace import resolve_workspace

    store = Store(resolve_workspace())
    store.save_guard_policy(guard_policy())
    tuple_ = types.ReleaseTuple.from_dict(tuple_payload())
    store.save_release_tuple(tuple_)

    with serve.start_http_service(store, tuple_.tuple_hash, ScriptedModel()) as service:
        with urlopen(f"{service.url}/health", timeout=5) as response:
            health = json.loads(response.read())
        assert health == {"ok": True, "tuple_hash": tuple_.tuple_hash}

        request = Request(
            f"{service.url}/generate",
            data=json.dumps({"messages": [{"role": "user", "content": "hello"}]}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=5) as response:
            generated = json.loads(response.read())
        assert generated["raw"]
        assert generated["guarded"]
        assert generated["guard_report"]
