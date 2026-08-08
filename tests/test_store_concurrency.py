"""Phase 02 red tests: real concurrent metrics/index access."""

import multiprocessing
import sqlite3


def test_store_uses_wal_and_survives_concurrent_metric_readers(store_factory):
    store = store_factory()
    with sqlite3.connect(store.workspace.index) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    run_id = store_factory.seed_run().run_id
    errors = multiprocessing.Manager().list()

    def append_metrics():
        try:
            writer = store_factory()
            for step in range(50):
                writer.append_metric(run_id, {"step": step})
        except Exception as exc:  # assertion below reports any process failure
            errors.append(repr(exc))

    def read_metrics():
        try:
            reader = store_factory()
            for _ in range(50):
                reader.tail_metrics(run_id, 10)
                reader.query_snapshot("objective-1")
        except Exception as exc:
            errors.append(repr(exc))

    writers = [multiprocessing.Process(target=append_metrics), multiprocessing.Process(target=read_metrics)]
    for process in writers:
        process.start()
    for process in writers:
        process.join()
    assert not errors
    assert len(store_factory().tail_metrics(run_id, 100)) == 50
