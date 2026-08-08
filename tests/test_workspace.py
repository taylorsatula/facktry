"""Phase 00: workspace discovery (ADR §7.1, phase_00_skeleton.md)."""

import os
import subprocess
import sys
from pathlib import Path


def resolve():
    from facktry.workspace import resolve_workspace

    return resolve_workspace()


def test_env_var_wins(tmp_path, monkeypatch):
    env = tmp_path / "envhome"
    env.mkdir()
    (env / ".facktry").mkdir()
    # ancestor + local .facktry must be ignored when FACKTRY_HOME is set
    anc = tmp_path / "anc" / ".facktry"
    anc.mkdir(parents=True)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / ".facktry").mkdir()
    monkeypatch.setenv("FACKTRY_HOME", str(env))
    monkeypatch.chdir(cwd)
    ws = resolve()
    assert ws.root == env


def test_parent_walk_finds_ancestor(tmp_path, monkeypatch):
    root = tmp_path
    (root / ".facktry").mkdir()
    cwd = root / "a" / "b" / "c"
    cwd.mkdir(parents=True)
    monkeypatch.delenv("FACKTRY_HOME", raising=False)
    monkeypatch.chdir(cwd)
    ws = resolve()
    assert ws.root == root


def test_fallback_creates_in_cwd(tmp_path, monkeypatch):
    cwd = tmp_path / "fresh"
    cwd.mkdir()
    monkeypatch.delenv("FACKTRY_HOME", raising=False)
    monkeypatch.chdir(cwd)
    ws = resolve()
    assert ws.root == cwd
    assert (cwd / ".facktry").is_dir()


def test_idempotent_repeat(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    ws1 = resolve()
    (ws1.root / "sentinel.txt").write_text("preserve-me")
    ws2 = resolve()
    assert ws2.root == ws1.root
    assert (ws1.root / "sentinel.txt").read_text() == "preserve-me"


def test_concurrent_workspace_creation_does_not_clobber(tmp_path):
    home = tmp_path / "concurrent-home"
    home.mkdir()
    sentinel = home / "sentinel.txt"
    sentinel.write_text("preserve-me")
    script = "from facktry.workspace import resolve_workspace; print(resolve_workspace().root)"
    env = {**os.environ, "FACKTRY_HOME": str(home)}
    processes = [
        subprocess.Popen([sys.executable, "-c", script], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for _ in range(4)
    ]
    outputs = [process.communicate(timeout=15) for process in processes]
    assert all(process.returncode == 0 for process in processes), outputs
    assert {stdout.strip() for stdout, _ in outputs} == {str(home)}
    assert sentinel.read_text() == "preserve-me"
    assert (home / "runs").is_dir()
    assert (home / "artifacts").is_dir()


def test_standard_subpaths(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    ws = resolve()
    assert ws.root == tmp_path
    assert ws.runs.is_dir()
    assert ws.artifacts.is_dir()
    assert ws.objectives.is_dir()
    assert ws.index.name == "index.sqlite3"
    assert ws.index.parent == ws.root


def test_agent_human_parity(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    ws = resolve()
    script = (
        "from facktry.workspace import resolve_workspace as r;"
        f"import os;os.chdir({str(ws.root)!r});"
        "print(r().root)"
    )
    out = subprocess.check_output([sys.executable, "-c", script]).decode().strip()
    assert out == str(ws.root)
