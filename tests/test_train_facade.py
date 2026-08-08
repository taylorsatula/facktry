"""Phase 11 red tests: governed smoke-to-scale facade wiring."""

from api_support import api_for


def test_agent_api_smoke_to_scale_happy_path_persists_runs_and_cards(tmp_path, monkeypatch):
    api, store = api_for(tmp_path, monkeypatch)
    backend = "fake-facade"
    api.register_train_backend(backend, {"method": backend})
    smoke = api.train_smoke("objective-valid", {"backend": backend, "admission_report_hash": "a" * 64})
    assert smoke.ok
    assert smoke.data["run_id"]
    scale = api.train_scale("objective-valid", {"smoke_run_id": smoke.data["run_id"], "backend": backend, "admission_report_hash": "a" * 64})
    assert scale.ok
    assert store.get_run(scale.data["run_id"]).outputs
    assert scale.data["train_card_ref"]


def test_scale_denied_without_passing_smoke_and_on_admission_mismatch(tmp_path, monkeypatch):
    api, _ = api_for(tmp_path, monkeypatch)
    denied = api.train_scale("objective-valid", {"backend": "fake", "admission_report_hash": "a" * 64})
    assert denied.error["type"] == "GovernDenial.SmokeGateUnsatisfied"
    assert denied.error["reason"] == "smoke_gate_unsatisfied"
    mismatch = api.train_scale("objective-valid", {"smoke_run_id": "smoke-1", "backend": "fake", "admission_report_hash": "b" * 64})
    assert mismatch.error["type"] == "GovernDenial.SmokeGateUnsatisfied"
    assert mismatch.error["reason"] == "admission_hash_mismatch"
