"""Phase 02 red tests: seeded store query surface.

Note: With SQLite as sole authority, rebuild_index cannot magically restore
lost data — there is no independent filesystem index to fall back to. The old
"index rebuild from files" test has been removed; rebuild_index simply
reinitializes the schema (safe when called on a live DB).
"""


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
    assert seeded_store.pinned_production_tuple(objective_id="objective-1")
    assert seeded_store.list_recipes()
    assert seeded_store.list_recipe_stacks()
