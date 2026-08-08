"""Workspace discovery for Facktry.

Resolves the shared workspace path used by both agent and human processes.
Order of precedence:
  1. ``FACKTRY_HOME`` environment variable → that directory is the workspace root.
     If it contains a ``.facktry`` marker subdirectory, still returns the env-var path as root.
  2. Walk cwd up through parents looking for a ``.facktry/`` marker directory;
     the directory *containing* that marker becomes root.
  3. Create ``.facktry/`` in the current working directory; cwd becomes root.

Returns a :class:`Workspace` dataclass carrying ``root`` and standard subpaths.
Standard subdirs (runs/, artifacts/, objectives/) live inside ``root``,
and ``index.sqlite3`` lives at ``root/index.sqlite3``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Workspace:
    """Resolved workspace with pre-computed standard subpaths."""

    root: Path
    runs: Path = field(init=False)  # type: ignore[assignment]
    artifacts: Path = field(init=False)  # type: ignore[assignment]
    objectives: Path = field(init=False)  # type: ignore[assignment]
    index: Path = field(init=False)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        _ensure_subdirs(self.root)
        object.__setattr__(self, "runs", self.root / "runs")
        object.__setattr__(self, "artifacts", self.root / "artifacts")
        object.__setattr__(self, "objectives", self.root / "objectives")
        object.__setattr__(self, "index", self.root / "index.sqlite3")


def _ensure_subdirs(root: Path) -> None:
    """Idempotently create standard workspace subdirectories."""
    for name in ("runs", "artifacts", "objectives"):
        (root / name).mkdir(exist_ok=True)


def resolve_workspace() -> Workspace:
    """Resolve and return the Facktry workspace.

    Discovery order:
    1. ``FACKTRY_HOME`` env var → use its value directly as the workspace root.
    2. Walk cwd → parent chain looking for a ``.facktry/`` marker directory;
       the directory containing it becomes root.
    3. Create ``.facktry/`` in cwd as fallback; cwd becomes root.

    The result is deterministic: given the same ``cwd`` and ``env``, every caller gets the same root.
    """
    # 1. Environment override
    env_home = __import__("os").environ.get("FACKTRY_HOME")
    if env_home:
        candidate = Path(env_home).resolve()
        _ensure_marker_and_subdirs(candidate)
        return Workspace(root=candidate)

    # 2. Walk parents from cwd
    cwd = Path.cwd().resolve()
    for ancestor in [cwd] + list(cwd.parents):
        marker = ancestor / ".facktry"
        if marker.is_dir():
            return Workspace(root=ancestor)

    # 3. Create in cwd
    new_marker = cwd / ".facktry"
    new_marker.mkdir(exist_ok=True)
    _ensure_subdirs(cwd)
    return Workspace(root=cwd)


def _ensure_marker_and_subdirs(root: Path) -> None:
    """Create the .facktry marker subdir and standard subdirs under root.

    Idempotent — safe to call repeatedly or concurrently.
    """
    (root / ".facktry").mkdir(exist_ok=True)
    _ensure_subdirs(root)
