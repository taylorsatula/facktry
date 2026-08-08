"""Phase 10 red tests: documented watch command surface and fixed panes."""

import json
import subprocess
import sys

import pytest

from api_support import pending_inbox_item
from govern_support import frozen_store

pytestmark = [pytest.mark.cli, pytest.mark.integration, pytest.mark.slow]


def run_cli(home, *args):
    return subprocess.run(
        [sys.executable, "-m", "facktry.cli.main", *args, "--home", str(home)],
        capture_output=True,
        text=True,
    )


def test_ls_and_unknown_show_are_useful_and_non_mutating(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    before = {path: path.read_bytes() for path in store.workspace.root.rglob("*") if path.is_file()}

    listed = run_cli(tmp_path, "ls")
    assert listed.returncode == 0
    assert "objective-valid" in listed.stdout

    unknown = run_cli(tmp_path, "show", "does-not-exist")
    assert unknown.returncode != 0
    assert "does-not-exist" in (unknown.stdout + unknown.stderr)
    after = {path: path.read_bytes() for path in store.workspace.root.rglob("*") if path.is_file()}
    assert after == before


def test_inbox_show_and_ingest_file_follow_the_same_schema_path(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    item = pending_inbox_item(store, item_id="inbox-file", response_schema={"type": "boolean"})
    response_file = tmp_path / "response.json"
    response_file.write_text(json.dumps({"id": item.id, "response": True, "reviewer": "human-1"}))

    shown = run_cli(tmp_path, "inbox", "show", item.id)
    assert shown.returncode == 0
    assert item.id in shown.stdout
    assert "pending" in shown.stdout.lower()

    ingested = run_cli(tmp_path, "inbox", "ingest", str(response_file))
    assert ingested.returncode == 0
    assert "answered" in ingested.stdout.lower()


def test_live_once_renders_every_documented_fixed_pane_without_mutating_store(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    before = {path: path.read_bytes() for path in store.workspace.root.rglob("*") if path.is_file()}
    result = run_cli(tmp_path, "--once")
    repeated = run_cli(tmp_path, "--once")
    assert result.returncode == repeated.returncode == 0
    output = result.stdout.lower()
    for pane in ("loop", "active run", "gates", "decision", "defects", "inbox", "release", "machine", "log"):
        assert pane in output, pane
    after = {path: path.read_bytes() for path in store.workspace.root.rglob("*") if path.is_file()}
    assert after == before
