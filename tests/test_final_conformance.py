"""Phase 17 red tests: ADR §13.3/§14 conformance evidence wiring."""

from pathlib import Path


def test_mandatory_conformance_categories_have_executable_test_modules():
    tests = Path(__file__).resolve().parent
    required = {
        "test_admit_structure_leakage.py", "test_admit_teacher_privacy.py", "test_verify_oracles.py",
        "test_train_facade.py", "test_select.py", "test_decide_aggregation.py", "test_suite_custody_compare.py",
        "test_suite_pin.py", "test_preference_pairs.py", "test_govern_gates.py", "test_agent_api_inbox_release.py",
        "test_watch_focus.py", "test_recipe_catalog.py", "test_recipe_composition.py", "test_control_loop_e2e.py",
        "test_domain_packs.py", "test_serve_canary_rollback.py",
    }
    missing = sorted(name for name in required if not (tests / name).is_file())
    assert not missing


def test_core_has_no_reference_repo_dependency_or_concrete_domain_imports():
    root = Path(__file__).resolve().parents[1] / "facktry"
    offenders = []
    for path in root.rglob("*.py"):
        text = path.read_text(errors="ignore")
        if "reference_repos" in text or "phase17_samples" in text or "FixtureDomain" in text:
            offenders.append(str(path))
    assert not offenders


def test_recipe_sources_contain_no_private_markers_or_workflow_implementation():
    root = Path(__file__).resolve().parents[1] / "docs" / "recipes"
    forbidden = ("PRIVATE-", "CANARY-", "password=", "@example.com", "subprocess", "os.system")
    for path in root.glob("*/RECIPE.md"):
        text = path.read_text()
        assert not any(marker in text for marker in forbidden), path
        assert "govern" in text.lower() or path.parent.name == "_template"


def test_recipe_catalog_is_declarative_not_a_second_workflow_engine():
    root = Path(__file__).resolve().parents[1] / "facktry" / "recipes"
    if not root.exists():
        assert False, "recipe catalog implementation is missing"
    for path in root.rglob("*.py"):
        text = path.read_text(errors="ignore")
        assert "subprocess" not in text
        assert "os.system" not in text
