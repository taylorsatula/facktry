"""Phase 08 red tests: intervention mapping, defects, and dossier artifacts."""

from decision_samples import admission, budget, scorecard, train_card, objective_gate
from govern_support import frozen_store


def run_decision(store, gate):
    from facktry import decide, types

    return decide.decide(
        store,
        "objective-valid",
        scorecards=[types.Scorecard.from_dict(scorecard([gate]))],
        admission=types.AdmissionReport.from_dict(admission()),
        train_cards=[types.TrainCard.from_dict(train_card())],
        budget=types.BudgetLedger.from_dict(budget()),
    )


def test_intervention_patterns_map_to_machine_readable_classes(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    patterns = [
        ("hidden_context", "data"),
        ("over_specialize", "mixture"),
        ("keep_rate_out_of_band", "rubric"),
        ("collapse_nonfinite", "hparam"),
        ("interface_drift", "interface"),
        ("budget_exhausted", "stop"),
    ]
    for taxonomy, expected in patterns:
        gate = objective_gate(observed=0, passed=False)
        gate["name"] = taxonomy
        decision = run_decision(store, gate)
        assert decision.intervention is not None
        assert decision.intervention["class"] == expected
        assert decision.intervention["hint"]


def test_repeated_failure_upserts_one_open_defect(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    gate = objective_gate(observed=0, passed=False)
    gate["name"] = "hidden_context"
    first = run_decision(store, gate)
    second = run_decision(store, gate)
    defects = store.open_defects()
    assert first.action.value == "correct"
    assert second.action.value == "correct"
    assert len([d for d in defects if d.taxonomy == "hidden_context"]) == 1
    assert defects[0].interventions


def test_decision_persists_single_pass_dossier_and_recipe_stack_ref(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    decision = run_decision(store, objective_gate(observed=0, passed=False))
    persisted = store.latest_decision("objective-valid")
    assert persisted.id == decision.id
    dossier = store.get_artifact(decision.dossier_ref.sha256, verify=True)
    text = dossier.path.read_text() if hasattr(dossier.path, "read_text") else store.read_artifact(dossier.sha256).decode()
    for section in ("MissionBrief", "Gate", "Intervention", "Budget"):
        assert section.lower() in text.lower()
    assert decision.recipe_stack_ref is not None
