"""Phase 15 red tests: criteria hashing, calibration, and severity limits."""

import pytest

from judge_samples import ScriptedJudge, calibration_items, criteria, write_calibration_fixture


def test_criteria_hash_is_recorded_on_report():
    from facktry.judge import assess

    report = assess([{"item_id": "item-1", "text": "visible"}], criteria(), ScriptedJudge())
    assert report.criteria_hash
    assert report.assessments[0].item_id == "item-1"
    assert report.assessments[0].rationale


def test_passing_calibration_allows_soft_gate_credit():
    from facktry.judge import assess, calibrate, judge_gate_results

    backend = ScriptedJudge(labels=["pass", "fail", "borderline"])
    result = calibrate(backend, criteria(), fixtures=calibration_items())
    assert result.passed
    report = assess([{"item_id": "item-1", "text": "visible"}], criteria(), backend, calibration=result)
    gates = judge_gate_results(report, severity="soft")
    assert gates[0].severity.value == "soft"


def test_failed_calibration_forces_diagnostic_only():
    from facktry.judge import assess, calibrate, judge_gate_results

    backend = ScriptedJudge(labels=["fail", "fail", "fail"])
    calibration = calibrate(backend, criteria(), fixtures=calibration_items())
    assert not calibration.passed
    report = assess([{"item_id": "item-1", "text": "visible"}], criteria(), backend, calibration=calibration)
    assert judge_gate_results(report, severity="soft")[0].severity.value == "diagnostic"


def test_hard_severity_judge_result_is_rejected():
    from facktry.errors import JudgeRefusal
    from facktry.judge import judge_gate_results

    report = type("Report", (), {"assessments": [{"item_id": "x", "score": 1}], "calibration": None})()
    with pytest.raises(JudgeRefusal):
        judge_gate_results(report, severity="hard")


def test_tampered_calibration_fixture_fails_hash_verification(tmp_path):
    from facktry.errors import StoreError
    from facktry.judge import load_calibration_fixture

    fixture = write_calibration_fixture(tmp_path / "calibration.json")
    loaded = load_calibration_fixture(fixture)
    assert [item["item_id"] for item in loaded] == ["clear-pass", "clear-fail", "borderline"]

    fixture.write_text(fixture.read_text().replace("borderline fixture", "tampered fixture"))
    with pytest.raises(StoreError, match="calibration"):
        load_calibration_fixture(fixture)


def test_criteria_or_backend_change_invalidates_calibration():
    from facktry.judge import assess, calibrate, judge_gate_results

    backend = ScriptedJudge(labels=["pass", "fail", "borderline"])
    calibration = calibrate(backend, criteria(), fixtures=calibration_items())
    changed_criteria = criteria(prompt="Changed rubric.")
    changed_criteria_report = assess([{"item_id": "item-1", "text": "visible"}], changed_criteria, backend, calibration=calibration)
    assert judge_gate_results(changed_criteria_report, severity="soft")[0].severity.value == "diagnostic"

    changed_backend = ScriptedJudge(labels=["pass", "fail", "borderline"], backend_id="scripted-v2")
    changed_backend_report = assess([{"item_id": "item-1", "text": "visible"}], criteria(), changed_backend, calibration=calibration)
    assert judge_gate_results(changed_backend_report, severity="soft")[0].severity.value == "diagnostic"
