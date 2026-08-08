"""Phase 00: no runtime dependency on reference_repos (ADR §13.5)."""

import re
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "facktry"
PATTERN = re.compile(r"\breference_repos\b")


def test_package_exists():
    # Non-vacuous guard: without this, "no offenders" is trivially true.
    assert PKG.is_dir(), "facktry package directory must exist"


def test_no_reference_repos_imports():
    assert PKG.is_dir()
    offenders = [
        str(p.relative_to(PKG))
        for p in PKG.rglob("*.py")
        if p.is_file() and PATTERN.search(p.read_text(errors="ignore"))
    ]
    assert not offenders, f"reference_repos referenced in: {offenders}"
