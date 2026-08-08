"""Phase 06 red tests: deterministic hard-gate oracles."""

import pytest


def context(**changes):
    from facktry.verify import OracleContext

    value = {
        "visible_input": {"messages": [{"role": "user", "content": "The color is blue."}]},
        "verified_state": {"color": "blue"},
        "authorized_tools": [{"name": "send_email", "arguments": {"to": "string"}}],
        "tool_records": [],
        "evidence_docs": ["The color is blue."],
        "config": {"canaries": ["CANARY-123"], "pii_patterns": [], "abstention": {"state_sufficient": True}},
    }
    value.update(changes)
    return OracleContext.from_dict(value)


@pytest.mark.parametrize("oracle_name,clean,bad", [
    ("schema", '{"answer":"blue"}', '{bad json'),
    ("privacy", "safe response", "leaked CANARY-123"),
    ("state_transition", {"action": "set_color", "color": "blue"}, {"action": "set_color", "color": "red"}),
    ("claim_not_executed", "I can help.", "I've sent the email."),
    ("unsupported_action", {"tool": "send_email", "arguments": {"to": "a"}}, {"tool": "delete_database", "arguments": {}}),
    ("entailment", "The color is blue.", "The color is red."),
    ("abstention", "I need more information.", "The answer is definitely red."),
])
def test_each_oracle_has_clean_and_negative_behavior(oracle_name, clean, bad):
    from facktry.verify import run_oracles

    clean_context = context()
    bad_context = context()
    if oracle_name == "abstention":
        bad_context = context(verified_state={}, config={"abstention": {"state_sufficient": False}})
    assert not [f for f in run_oracles(clean, clean_context, [oracle_name]) if f.oracle == oracle_name]
    findings = run_oracles(bad, bad_context, [oracle_name])
    assert any(f.oracle == oracle_name for f in findings)
    assert all(f.message for f in findings)


def test_claim_not_executed_is_clean_after_confirmed_tool_success():
    from facktry.verify import run_oracles

    ctx = context(tool_records=[{"tool": "send_email", "success": True}])
    assert not run_oracles("I've sent the email.", ctx, ["claim_not_executed"])


def test_execution_oracle_uses_injected_executor_and_reports_missing_configuration():
    from facktry.verify import run_oracles

    missing = run_oracles("query", context(), ["execution"])
    assert any(f.oracle == "execution" and "config" in f.message.lower() for f in missing)
    passing = run_oracles("query", context(config={"executor": lambda output: True}), ["execution"])
    assert not [f for f in passing if f.oracle == "execution"]


def test_oracles_are_deterministic_and_findings_map_to_gate_severity():
    from facktry.verify import findings_to_gate_results, run_oracles

    findings_a = run_oracles("I've sent the email.", context(), ["claim_not_executed"])
    findings_b = run_oracles("I've sent the email.", context(), ["claim_not_executed"])
    assert [f.to_dict() for f in findings_a] == [f.to_dict() for f in findings_b]
    results = findings_to_gate_results(findings_a, [{"name": "claim", "severity": "hard", "checker_ref": "claim_not_executed", "channel": "raw", "threshold": 0}])
    assert results[0].severity.value == "hard"
