"""Canonical JSON serialization and SHA-256 hashing.

All modules that produce content hashes must use these helpers — never hand-roll.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def canonical_json(obj) -> bytes:
    """Serialize *obj* to canonical JSON bytes.

    Key order is deterministic (sorted), separators are compact, non-ASCII
    characters are preserved (not escaped).
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def hash_bytes(b: bytes) -> str:
    """SHA-256 digest of raw bytes."""
    return hashlib.sha256(b).hexdigest()


def hash_file(path: Path | str) -> str:
    """SHA-256 digest of a file, streamed in chunks (no full read)."""
    h = hashlib.sha256()
    chunk_size = 1 << 20  # 1 MiB
    with open(str(path), "rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def hash_obj(obj) -> str:
    """SHA-256 digest of any serializable object via canonical JSON."""
    return hash_bytes(canonical_json(obj))
