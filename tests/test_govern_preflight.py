"""Phase 04 red tests: preflight machine-state checks."""

import shutil

import pytest

from govern_support import frozen_store, store_for


def test_clean_preflight_returns_paths_hardware_and_gpu_report(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    from facktry.govern import preflight

    report = preflight(store)
    assert report.workspace_root == store.workspace.root
    assert report.hardware is not None
    assert report.gpus is not None
    assert report.preservation_paths_ok


def test_disk_floor_violation_is_typed(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    import facktry.govern as govern_module
    from facktry.errors import PreflightFailed

    real_usage = shutil.disk_usage(tmp_path)
    monkeypatch.setattr(govern_module.shutil, "disk_usage", lambda _: type(real_usage)(total=10, used=9, free=1))
    with pytest.raises(PreflightFailed):
        govern_module.preflight(store, disk_floor_bytes=2)


def test_broken_gpu_probe_degrades_to_report(tmp_path, monkeypatch):
    store = store_for(tmp_path, monkeypatch)
    import facktry.govern as govern_module

    def broken_probe():
        raise OSError("NVML unavailable")
    monkeypatch.setattr(govern_module, "probe_gpus", broken_probe)
    report = govern_module.preflight(store)
    assert report.gpus
    assert any("unavailable" in str(gpu).lower() for gpu in report.gpus)


def test_configured_conflicting_large_service_is_refused(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch, {"intent": "train and serve a large model"})
    (store.workspace.root / "preflight.json").write_text('{"occupied_services":[{"name":"inference","gpus":[7],"large_model":true}]}')
    from facktry.govern import preflight
    from facktry.errors import PreflightFailed

    with pytest.raises(PreflightFailed):
        preflight(store, objective_id="objective-valid")
