"""Phase 10 red tests: explicit inbox CLI mutation only."""

import json
import subprocess
import sys


def run_cli(home, *args):
    return subprocess.run([sys.executable, "-m", "facktry.cli.main", *args, "--home", str(home)], capture_output=True, text=True)


def test_inbox_response_rejects_schema_invalid_payload(tmp_path):
    result = run_cli(tmp_path, "inbox", "respond", "item-1", "--json", json.dumps({"response": "wrong"}))
    assert result.returncode != 0
    assert "schema" in (result.stdout + result.stderr).lower()


def test_inbox_response_valid_payload_completes_item(tmp_path):
    result = run_cli(tmp_path, "inbox", "respond", "item-1", "--json", json.dumps({"response": True, "reviewer": "human-1"}))
    assert result.returncode == 0
    assert "answered" in (result.stdout + result.stderr).lower()
