# Phase 00 — Repository skeleton

| Field | Value |
|---|---|
| **Status** | [ ] |
| **Depends on** | nothing |
| **Checklist sections** | §0 |
| **ADR refs** | §13.4 (code quality), §7.1 (workspace discovery) |

## Goal

Create the installable `facktry` package, pytest scaffold, and shared workspace discovery.

## In scope

- `pyproject.toml` (package name `facktry`, `requires-python = ">=3.11"`, console script `facktry = "facktry.cli.main:main"`).
- Optional extras declared now so later phases don't fight packaging: `facktry[train]` (torch etc., unpinned placeholders allowed), `facktry[cli]` (`rich`), `facktry[dev]` (`pytest`).
- `facktry/__init__.py` exporting `__version__`.
- `facktry/workspace.py`: `resolve_workspace()` implementing `FACKTRY_HOME` → walk cwd/parents for `.facktry/` → create `.facktry/` in cwd. Returns a `Workspace` dataclass with `root` and the standard subpaths (`runs/`, `artifacts/`, `objectives/`, `index.sqlite3`). Creating missing subdirs is allowed here.
- `facktry/cli/main.py` minimal dispatcher that prints a "not yet implemented; see IMPLEMENTATION_CHECKLIST.md" message for live view. **Explicitly temporary** — phase 10 replaces it with the real monitor. Do not grow features here.
- `.gitignore`: `.facktry/`, `runs/`, `__pycache__`, `*.egg-info`, `.pytest_cache`.
- `README.md` pointing at `ADR.md`, `IMPLEMENTATION_CHECKLIST.md`, `docs/skills/`, `docs/recipes/`, and this directory.
- `tests/` with `conftest.py` providing a `tmp_workspace` fixture (uses `tmp_path` + `FACKTRY_HOME` override).

## Out of scope

- Any store/objective/govern logic (phases 02–04).
- Any real CLI rendering (phase 10).

## Fail-closed requirements

- `resolve_workspace()` must return the same path for agent and human processes given the same cwd/env; no extra flags.
- Workspace creation must be idempotent and safe to call concurrently (create-if-missing, no clobbering existing files).

## Tests

- `import facktry` works; `facktry.__version__` is a string.
- Workspace resolution: `FACKTRY_HOME` wins; parent-walk finds an ancestor `.facktry/`; fallback creates `.facktry/` in cwd; repeated calls don't error.
- Static guard test: no source file under `facktry/` imports from `reference_repos/` (scan with pathlib — cheap, permanent regression guard for ADR §13.5).

## Checklist updates

- Mark every item in checklist §0 `[x]` (including the reference-repository independence guard).
- Progress summary row 0 → `[x]` with UTC date.

## Definition of done

`pip install -e .` succeeds; the placeholder console script runs; and `pytest` passes.

## Handoff to phase 01

Phase 01 adds `facktry/hashing.py` and `facktry/types.py`. Do not pre-create them here beyond empty modules if imports demand it.
