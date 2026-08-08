"""Phase 07 red tests: pin_suites integration with govern."""

from suite_registry import suite_data
from govern_support import frozen_store


def test_pin_suites_persists_real_hashes_and_satisfies_govern(tmp_path, monkeypatch):
    monkeypatch.setenv("FACKTRY_HOME", str(tmp_path))
    from facktry import suite
    from facktry.govern import suite_pin_required
    from facktry.store import Store
    from facktry.workspace import resolve_workspace

    store = frozen_store(tmp_path, monkeypatch)
    value = suite.Suite.from_dict(suite_data())
    store.register_suite(value)
    suite.pin_suites(store, "objective-valid", [(value.id, value.content_hash())])
    assert store.get_objective("objective-valid").suites["seal"]["hash"] == value.content_hash()
    assert suite_pin_required(store, "objective-valid") is None
