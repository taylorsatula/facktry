"""Phase 00: console entrypoint placeholder (phase_00_skeleton.md)."""

import shutil
import subprocess


def test_console_script_runs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    exe = shutil.which("facktry")
    assert exe, "console script 'facktry' must be installed"
    r = subprocess.run([exe], capture_output=True, text=True)
    assert r.returncode == 0
    assert "not yet implemented" in (r.stdout + r.stderr)
