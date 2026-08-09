"""Phase 02 red tests: real concurrent metrics/index access.

Uses threading with separate Store instances per thread so each gets an
independent SQLite connection exercising WAL-mode concurrent reads/writes.
"""

import sqlite3
import threading

import pytest

pytestmark = [pytest.mark.store, pytest.mark.slow]


def test_store_uses_wal_and_survives_concurrent_metric_readers(store_factory):
    store = store_factory()
    with sqlite3.connect(store.workspace.index) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    run_id = store_factory.seed_run().run_id
    errors: list[BaseException] = []

    def append_metrics():
        try:
            writer = store_factory()
            for step in range(50):
                writer.append_metric(run_id, {"step": step})
        except BaseException as exc:
            errors.append(exc)

    def read_metrics():
        try:
            reader = store_factory()
            for _ in range(50):
                reader.tail_metrics(run_id, 10)
                reader.query_snapshot("objective-1")
        except BaseException as exc:
            errors.append(exc)

    t_write = threading.Thread(target=append_metrics)
    t_read = threading.Thread(target=read_metrics)
    t_write.start()
    t_read.start()
    t_write.join()
    t_read.join()
    assert not errors
    assert len(store_factory().tail_metrics(run_id, 100)) == 50
