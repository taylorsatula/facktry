"""Query-surface fixtures for Phase 10 focus tests."""


def item(kind, item_id, **extra):
    value = {"kind": kind, "id": item_id}
    value.update(extra)
    return value
