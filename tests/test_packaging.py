"""Phase 00: packaging metadata + extras (phase_00_skeleton.md)."""

import importlib.metadata as md


def test_entry_point_registered():
    names = {ep.name for ep in md.entry_points(group="console_scripts")}
    assert "facktry" in names


def test_version_metadata():
    assert md.distribution("facktry").version


def test_extras_declared():
    requires = md.distribution("facktry").requires or []
    rendered = " ".join(requires)
    for extra in ("train", "cli", "dev"):
        assert f'extra == "{extra}"' in rendered
