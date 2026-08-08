"""Phase 17 red tests: domain-pack protocol, registry, and stage dispatch."""

import pytest

from phase17_samples import FixtureDomain


def test_domain_pack_register_get_and_protocol_surface():
    from facktry.domains import get_domain, register_domain, validate_domain_pack

    pack = FixtureDomain("fixture-register")
    validate_domain_pack(pack)
    register_domain(pack)
    assert get_domain("fixture-register") is pack
    assert get_domain("fixture-register").required_brief_sections == ["success_case"]


def test_duplicate_or_missing_domain_is_typed_failure():
    from facktry.domains import get_domain, register_domain
    from facktry.errors import DomainError

    with pytest.raises(DomainError):
        get_domain("does-not-exist")
    pack = FixtureDomain("fixture-duplicate")
    register_domain(pack)
    with pytest.raises(DomainError):
        register_domain(pack)


def test_run_stage_dispatches_to_registered_pack_inside_governed_run(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from govern_support import frozen_store
    from facktry import agent_api
    from facktry.domains import register_domain

    store = frozen_store(tmp_path, monkeypatch)
    register_domain(FixtureDomain("fixture-run"))
    result = agent_api.AgentAPI(store).run_stage("fixture_stage", "objective-valid", {"value": "ran"}, domain="fixture-run")
    assert result.ok
    assert result.data["stage"] == "fixture_stage"
    assert result.data["mission_brief_hash"]
    assert result.data["objective_id"] == "objective-valid"


def test_unregistered_stage_does_not_improvise(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from govern_support import frozen_store
    from facktry import agent_api

    store = frozen_store(tmp_path, monkeypatch)
    result = agent_api.AgentAPI(store).run_stage("missing_stage", "objective-valid", {})
    assert result.error["type"] == "DomainError"
    assert result.error["reason"] == "unregistered_stage"
    assert result.error["details"]["stage"] == "missing_stage"


@pytest.mark.conformance
def test_core_source_does_not_import_fixture_domain():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "facktry"
    assert root.is_dir()
    offenders = []
    for path in root.rglob("*.py"):
        if "FixtureDomain" in path.read_text(errors="ignore") or "phase17_samples" in path.read_text(errors="ignore"):
            offenders.append(str(path))
    assert not offenders


@pytest.mark.conformance
def test_template_domain_pack_has_skeleton_documentation():
    from pathlib import Path

    template = Path(__file__).resolve().parents[1] / "facktry" / "domains" / "_template"
    assert (template / "README.md").is_file()
    assert (template / "suites").is_dir()
