"""Phase 10 red tests: status rendering and read-only behavior."""

import subprocess
import sys

import pytest

pytestmark = [pytest.mark.cli, pytest.mark.integration, pytest.mark.slow]


def run_status(home, *args):
    return subprocess.run([sys.executable, "-m", "facktry.cli.main", "status", "--once", "--home", str(home), *args], capture_output=True, text=True)


def snapshot_files(root):
    return {path: (path.stat().st_mtime_ns, path.read_bytes()) for path in root.rglob("*") if path.is_file()}


def test_status_on_bare_workspace_exits_cleanly_with_empty_state(tmp_path):
    result = run_status(tmp_path)
    assert result.returncode == 0
    output = result.stdout + result.stderr
    assert "no active objective" in output.lower()
    assert "missionbrief" in output.lower()


def test_status_on_populated_workspace_does_not_mutate_store(tmp_path, monkeypatch):
    from govern_support import frozen_store

    store = frozen_store(tmp_path, monkeypatch)
    before = snapshot_files(store.workspace.root)
    result = run_status(tmp_path)
    after = snapshot_files(store.workspace.root)
    assert result.returncode == 0
    assert after == before


def test_missing_metrics_and_gpu_degrade_without_crashing(tmp_path):
    result = run_status(tmp_path)
    assert result.returncode == 0
    output = result.stdout + result.stderr
    assert "no metrics" in output.lower() or "metrics" in output.lower()
    assert "gpu" in output.lower()
