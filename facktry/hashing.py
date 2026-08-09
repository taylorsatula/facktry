"""Canonical JSON serialization and SHA-256 hashing.

All modules that produce content hashes must use these helpers — never hand-roll.

Contract for ``canonical_json`` / ``hash_obj``:
- Input must be JSON-serializable via ``json.dumps``
  (``dict``, ``list``, ``str``, ``int``, ``float``, ``bool``, ``None``).
- Floats must be finite (no NaN or Inf).
- Strings should be NFC-normalized. The caller is responsible for ensuring
  consistent Unicode representation before hashing — Pydantic models
  typically preserve input normalization, so this is enforced at the
  application level, not here.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any


#: Chunk size for streaming file reads (1 MiB).
_CHUNK_SIZE = 1 << 20


def canonical_json(obj: Any) -> bytes:
    """Serialize *obj* to deterministic JSON bytes.

    Key order is sorted, separators are compact, non-ASCII characters are
    preserved (not escaped). Produces identical output regardless of
    insertion order or process restart.

    Raises ``ValueError`` on non-serializable inputs (sets, NaN, Inf,
    datetime without custom encoder, etc.).
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
    with open(str(path), "rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_obj(obj: Any) -> str:
    """SHA-256 digest of any serializable object via canonical JSON."""
    return hash_bytes(canonical_json(obj))
