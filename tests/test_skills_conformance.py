"""Phase 17 red tests: canonical operator skill documentation alignment."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.conformance


SKILLS = [
    "operating-facktry", "elicit-mission", "freeze-objective", "preflight", "pin-suites",
    "admit-data", "generate-and-admit", "train-smoke", "train-scale", "measure-and-compare",
    "decide", "yield-release", "human-inbox", "defects-and-correct", "watch-progress",
    "recipe-authoring",
]


def _root():
    return Path(__file__).resolve().parents[1] / "docs" / "skills"


def test_skills_index_names_canonical_agent_api_module():
    index = _root() / "README.md"
    assert index.is_file()
    text = index.read_text()
    assert "facktry.agent_api" in text
    assert "documentation" in text.lower() or "skill" in text.lower()


def test_all_canonical_skills_exist_and_use_real_agent_api_boundary():
    root = _root()
    for skill in SKILLS:
        path = root / skill / "SKILL.md"
        assert path.is_file(), skill
        text = path.read_text()
        assert "facktry.agent_api" in text, skill
        assert "govern" in text.lower(), skill
        assert "error" in text.lower() or "denial" in text.lower(), skill


def test_skills_do_not_teach_governance_bypasses_or_direct_promotion():
    root = _root()
    forbidden = ("skip govern", "bypass govern", "without governance", "promote directly", "skip smoke")
    for path in root.glob("*/SKILL.md"):
        text = path.read_text().lower()
        assert not any(phrase in text for phrase in forbidden), path
        assert "sealed" not in text or "do not" in text or "blind" in text


def test_skills_distinguish_recipe_planning_from_measured_gate_evidence():
    recipe = (_root() / "recipe-authoring" / "SKILL.md").read_text().lower()
    assert "note" in recipe
    assert "measure" in recipe
    assert "gate" in recipe
    assert "evidence" in recipe
