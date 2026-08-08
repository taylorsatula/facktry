"""Phase 01 red tests: canonical JSON and SHA-256 helpers."""

import hashlib
import json
import subprocess
import sys


def test_canonical_json_is_exact_and_key_order_invariant():
    from facktry.hashing import canonical_json

    left = {"z": 1, "nested": {"é": "café", "a": [True, None]}}
    right = {"nested": {"a": [True, None], "é": "café"}, "z": 1}
    expected = b'{"nested":{"a":[true,null],"\xc3\xa9":"caf\xc3\xa9"},"z":1}'
    assert canonical_json(left) == expected
    assert canonical_json(left) == canonical_json(right)


def test_hash_helpers_match_sha256_vectors(tmp_path):
    from facktry.hashing import canonical_json, hash_bytes, hash_file, hash_obj

    data = b"abc"
    assert hash_bytes(data) == hashlib.sha256(data).hexdigest()
    path = tmp_path / "large.bin"
    path.write_bytes(data * 500_000)
    assert hash_file(path) == hashlib.sha256(path.read_bytes()).hexdigest()
    obj = {"b": 2, "a": 1}
    assert hash_obj(obj) == hashlib.sha256(canonical_json(obj)).hexdigest()


def test_hash_obj_is_stable_across_processes():
    from facktry.hashing import hash_obj

    obj = {"unicode": "café", "items": [3, 2, 1]}
    script = "from facktry.hashing import hash_obj; print(hash_obj({'items':[3,2,1],'unicode':'café'}))"
    child = subprocess.check_output([sys.executable, "-c", script], text=True).strip()
    assert child == hash_obj(obj)
