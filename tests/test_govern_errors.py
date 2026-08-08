"""Phase 04 red tests: typed fail-closed denial taxonomy."""


def test_govern_denial_subclasses_have_reason_and_details():
    from facktry.errors import (
        BudgetExhausted,
        CompatMismatch,
        GovernDenial,
        MissionBriefRequired,
        PolicyDenied,
        PreflightFailed,
        SmokeGateUnsatisfied,
        SuiteNotPinned,
    )

    classes = (MissionBriefRequired, BudgetExhausted, PolicyDenied, PreflightFailed, CompatMismatch, SmokeGateUnsatisfied, SuiteNotPinned)
    assert all(issubclass(cls, GovernDenial) for cls in classes)
    denial = PolicyDenied("capability denied", reason="policy", details={"capability": "unknown"})
    assert denial.reason == "policy"
    assert denial.details["capability"] == "unknown"
