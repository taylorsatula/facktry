"""Phase 10 red tests: pure auto-focus ordering and empty state."""

import pytest

from cli_samples import item

pytestmark = pytest.mark.unit


def test_focus_priority_matches_adr_order():
    from facktry.cli.focus import resolve_focus

    states = [
        ({"inbox": [item("inbox", "i1", status="pending")], "runs": [item("run", "r1", status="running")], "briefs": [item("brief", "b1")], "objectives": [item("objective", "o1", status="frozen")], "decisions": [item("decision", "d1")]}, "i1"),
        ({"inbox": [], "runs": [item("run", "r1", status="running")], "briefs": [item("brief", "b1")], "objectives": [item("objective", "o1", status="frozen")], "decisions": [item("decision", "d1")]}, "r1"),
        ({"inbox": [], "runs": [item("run", "r1", status="guarded")], "briefs": [item("brief", "b1")], "objectives": [item("objective", "o1", status="frozen")], "decisions": [item("decision", "d1")]}, "r1"),
        ({"inbox": [], "runs": [], "briefs": [item("brief", "b1", attached=False)], "objectives": [item("objective", "o1", status="frozen")], "decisions": [item("decision", "d1")]}, "b1"),
        ({"inbox": [], "runs": [], "briefs": [], "objectives": [item("objective", "o1", status="frozen")], "decisions": [item("decision", "d1")]}, "o1"),
        ({"inbox": [], "runs": [], "briefs": [], "objectives": [], "decisions": [item("decision", "d1")]}, "d1"),
    ]
    for query_surface, expected_id in states:
        assert resolve_focus(query_surface).id == expected_id


def test_empty_focus_is_concrete_and_actionable():
    from facktry.cli.focus import resolve_focus

    focus = resolve_focus({"inbox": [], "runs": [], "briefs": [], "objectives": [], "decisions": []})
    assert focus.kind == "empty"
    assert "MissionBrief" in focus.message
    assert "elicit" in focus.message.lower()
