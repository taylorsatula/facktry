"""Phase 02 red tests: seeded store query surface and index rebuild."""


def test_seeded_store_exposes_all_adr_queries(seeded_store):
    assert seeded_store.list_mission_briefs()
    assert seeded_store.runs_by(objective_id="objective-1")
    assert seeded_store.runs_by(status="completed")
    assert seeded_store.runs_by(stage="admit")
    assert seeded_store.parents_of("run-1")
    assert seeded_store.children_of("run-0")
    assert seeded_store.latest_passing_admission("objective-1")
    assert seeded_store.open_defects()
    assert seeded_store.pending_inbox()
    assert seeded_store.latest_decision("objective-1")
    assert seeded_store.active_objectives()
    assert seeded_store.frozen_objectives()
    assert seeded_store.pinned_production_tuple()
    assert seeded_store.list_recipes()
    assert seeded_store.list_recipe_stacks()


def test_rebuild_index_restores_file_authoritative_queries(seeded_store):
    before = seeded_store.query_snapshot("objective-1")
    seeded_store.workspace.index.unlink()
    seeded_store.rebuild_index()
    assert seeded_store.query_snapshot("objective-1") == before
