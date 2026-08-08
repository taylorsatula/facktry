"""Phase 02 red tests: protected-run deletion policy."""

import pytest


def test_protected_run_deletes_are_refused(seeded_store):
    from facktry.errors import StoreError

    for run_id in ("run-with-children", "run-pinned", "run-decided"):
        with pytest.raises(StoreError):
            seeded_store.delete_run(run_id)


def test_unprotected_run_can_be_deleted(seeded_store):
    seeded_store.delete_run("run-unprotected")
    assert seeded_store.get_run("run-unprotected") is None
