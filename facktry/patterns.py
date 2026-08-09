"""Shared deterministic pattern utilities.

Used by verify (privacy oracle) and admit (PII/grounding filters).
No network access; pure regex/string matching.
"""
from __future__ import annotations

import re
from typing import Protocol

#: Default compiled PII / canary patterns shipped with facktry.
_DEFAULT_PATTERNS = [
    # Canaries / sentinel tokens.
    re.compile(r"CANARY-[0-9A-Z]{3,}"),
    # US Social Security Number.
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    # Email address.
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
]

# --- Protocols (for typed config, tested with callable injectors) ---

class PatternChecker(Protocol):
    """Check text against one or more patterns."""

    def matches(self, text: str) -> bool: ...


def _check_canaries(text: str, *, patterns: list[str | re.Pattern]) -> list[str]:
    """Return all matched canary / PII pattern IDs found in *text*."""
    matches_found: list[str] = []
    for p in patterns:
        compiled = p.pattern if isinstance(p, re.Pattern) else p
        rx = re.compile(compiled)
        if rx.search(text):
            matches_found.append(compiled)
    return matches_found


def _contains_canary(text: str, canaries: list[str]) -> bool:
    """True if any configured canary substring appears in *text* (case-sensitive)."""
    return any(c in text for c in canaries)


def check_pii_patterns(text: str, patterns: list[str] | None = None) -> list[str]:
    """Scan *text* against *patterns* (or defaults) and return matched pattern strings."""
    return _check_canaries(
        text,
        patterns=patterns or [pat for pat in _DEFAULT_PATTERNS],
    )

# --- Gate-result helpers ---

def match_gate_result(gate_config: dict, checker: str) -> dict | None:
    """Return the first gate whose checker_ref == *checker*, or None."""
    for g in gate_config:
        if g.get("checker_ref") == checker:
            return g
    return None


findings_to_gate_results = match_gate_result  # alias
