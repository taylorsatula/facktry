"""Shared fixtures for the Facktry test suite.

Deliberately lazy: no facktry.* imports at module top-level during the red
phase, so collection still succeeds and each test fails individually.
"""

from pathlib import Path

import pytest

# Repository root, resolved from this file's location.
REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def tmp_workspace(monkeypatch, tmp_path):
    """A workspace root with FACKTRY_HOME pointed at it (test isolation)."""
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    return tmp_path
