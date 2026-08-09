"""Durable, queryable, hash-verified store.

SQLite (WAL mode) is the sole source of truth for all internal state.
The filesystem holds only content-addressed blobs meant for external consumption,
append-only metrics (JSONL), objective bytes, and recipe-stack files.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import SerdeError, StoreError
from .hashing import canonical_json, hash_bytes, hash_obj
from .types import (
    AdmissionReport,
    Artifact,
    BudgetLedger,
    Decision,
    Defect,
    HumanInboxItem,
    MissionBrief,
    Recipe,
    RecipeStack,
    ReleaseTuple,
    Run,
    RunStatus,
)
from .workspace import Workspace

# ---------------------------------------------------------------------------
# SQLite schema
# ---------------------------------------------------------------------------

_SCHEMA_VERSION = 20260806

_INIT_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA busy_timeout=5000;

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', '%d');

CREATE TABLE IF NOT EXISTS mission_briefs (
    brief_id   TEXT    NOT NULL,
    version    INTEGER NOT NULL,
    brief_hash TEXT    NOT NULL,
    PRIMARY KEY (brief_id, version)
);

CREATE TABLE IF NOT EXISTS objectives (
    objective_id TEXT    PRIMARY KEY,
    obj_hash     TEXT    NOT NULL,
    frozen       BOOLEAN NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS runs (
    run_id         TEXT    PRIMARY KEY,
    objective_id   TEXT    NOT NULL,
    stage          TEXT    NOT NULL,
    status         TEXT    NOT NULL,
    run_bytes      BLOB    NOT NULL,
    created_at     TEXT    NOT NULL DEFAULT (strftime('%%Y-%%m-%%dT%%H:%%M:%%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_runs_objective ON runs(objective_id);
CREATE INDEX IF NOT EXISTS idx_runs_status  ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_stage   ON runs(stage);

CREATE TABLE IF NOT EXISTS lineage (
    child_run_id TEXT    NOT NULL,
    parent_run_id TEXT   NOT NULL,
    relation     TEXT    NOT NULL DEFAULT 'parent',
    UNIQUE(child_run_id, parent_run_id)
);

CREATE TABLE IF NOT EXISTS artifacts (
    sha256            TEXT    PRIMARY KEY,
    role              TEXT    NOT NULL,
    producer_run_id   TEXT    NOT NULL,
    disk_path         TEXT    NOT NULL,
    media_type        TEXT,
    created_at        TEXT    NOT NULL DEFAULT (strftime('%%Y-%%m-%%dT%%H:%%M:%%SZ','now'))
);

CREATE TABLE IF NOT EXISTS decisions (
    decision_id  TEXT    PRIMARY KEY,
    objective_id TEXT    NOT NULL,
    dec_bytes    BLOB    NOT NULL,
    created_at   TEXT    NOT NULL DEFAULT (strftime('%%Y-%%m-%%dT%%H:%%M:%%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_decisions_objective ON decisions(objective_id);

CREATE TABLE IF NOT EXISTS defects (
    defect_id    TEXT    NOT NULL,
    taxonomy     TEXT    NOT NULL,
    evidence     TEXT    NOT NULL,
    first_run_id TEXT    NOT NULL,
    last_run_id  TEXT    NOT NULL,
    interventions TEXT   NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'open',
    created_at   TEXT    NOT NULL DEFAULT (strftime('%%Y-%%m-%%dT%%H:%%M:%%SZ','now'))
);

CREATE TABLE IF NOT EXISTS inbox (
    item_id        TEXT    PRIMARY KEY,
    objective_id   TEXT    NOT NULL,
    gate_name      TEXT    NOT NULL,
    payload_ref    TEXT    NOT NULL,
    response_schema TEXT   NOT NULL,
    item_bytes     BLOB    NOT NULL,
    created_at     TEXT    NOT NULL DEFAULT (strftime('%%Y-%%m-%%dT%%H:%%M:%%SZ','now'))
);

CREATE TABLE IF NOT EXISTS budget_ledger (
    objective_id TEXT    PRIMARY KEY,
    ledger_bytes BLOB    NOT NULL
);

CREATE TABLE IF NOT EXISTS pinned_tuple (
    objective_id  TEXT    PRIMARY KEY,
    tuple_bytes   BLOB    NOT NULL
);

CREATE TABLE IF NOT EXISTS recipes (
    recipe_id       TEXT    NOT NULL,
    version         TEXT    NOT NULL,
    instruction_hash TEXT   NOT NULL,
    recipe_bytes    BLOB    NOT NULL,
    notes_head      TEXT,
    created_at      TEXT    NOT NULL DEFAULT (strftime('%%Y-%%m-%%dT%%H:%%M:%%SZ','now')),
    PRIMARY KEY (recipe_id, version)
);

CREATE TABLE IF NOT EXISTS recipe_notes (
    note_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id   TEXT    NOT NULL,
    version     TEXT    NOT NULL,
    note_bytes  BLOB    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%%Y-%%m-%%dT%%H:%%M:%%SZ','now'))
);

CREATE TABLE IF NOT EXISTS admissions (
    objective_id  TEXT    NOT NULL,
    report_hash   TEXT    NOT NULL,
    report_bytes  BLOB    NOT NULL,
    passed        BOOLEAN NOT NULL DEFAULT 1,
    created_at    TEXT    NOT NULL DEFAULT (strftime('%%Y-%%m-%%dT%%H:%%M:%%SZ','now')),
    UNIQUE(objective_id, report_hash)
);

CREATE TABLE IF NOT EXISTS recipe_stacks_db (
    stack_hash TEXT PRIMARY KEY,
    id         TEXT NOT NULL,
    stack_bytes BLOB NOT NULL
);

-- Supersession tracking: old_obj_id → new_obj_id
CREATE TABLE IF NOT EXISTS supersessions (
    superseded_id   TEXT    NOT NULL,
    superseding_id  TEXT    NOT NULL,
    UNIQUE(superseded_id)
);

-- Protection markers: which runs cannot be deleted
CREATE TABLE IF NOT EXISTS run_protection (
    run_id       TEXT    NOT NULL,
    reason       TEXT    NOT NULL,
    ref_id       TEXT    NOT NULL DEFAULT '',
    UNIQUE(run_id, reason)
);

-- Suite registry: id + hash -> on-disk path
CREATE TABLE IF NOT EXISTS suites (
    suite_id     TEXT    NOT NULL,
    suite_hash   TEXT    NOT NULL,
    path         TEXT    NOT NULL,
    UNIQUE(suite_id, suite_hash)
);
"""

# ---------------------------------------------------------------------------
# Helpers: atomic write, DB helpers
# ---------------------------------------------------------------------------


def _atomic_write_json(path: Path, data: Any) -> None:
    """Write canonical JSON to *path* atomically via temp+rename.

    On failure the previous content is preserved unmodified.
    """
    tmp = path.with_suffix(".tmp")
    try:
        with tmp.open("wb") as f:
            f.write(canonical_json(data))
        os.replace(str(tmp), str(path))
    except OSError:
        tmp.unlink(missing_ok=True)
        raise StoreError(f"Failed to atomically write {path}") from None


def _conn(ws: Workspace) -> sqlite3.Connection:
    """Open and initialize the workspace SQLite database.

    On schema-version bump the DB is recreated (safe for ephemeral workspaces).
    """
    path = str(ws.index)
    needs_recreate = False

    # Check existing schema version before exec
    try:
        probe = sqlite3.connect(path)
        cur = probe.execute(
            "SELECT value FROM meta WHERE key='schema_version'",
        ).fetchone()
        if cur is not None and int(cur[0]) != _SCHEMA_VERSION:
            needs_recreate = True
        probe.close()
    except (sqlite3.OperationalError, ValueError):
        needs_recreate = True  # brand-new or corrupted; init fresh

    if needs_recreate:
        import os
        if os.path.exists(path):
            os.unlink(path)

    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.executescript(_INIT_SQL % _SCHEMA_VERSION)
    return conn


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

class Store:
    """Primary persistence layer for Facktry.

    SQLite holds all internal state authoritatively. The filesystem stores
    only large blobs meant for external consumers and append-only metrics.
    """

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace
        # Eagerly open connection so schema is initialized immediately
        self._db = _conn(workspace)

    # ======================================================================
    # Artifacts
    # ======================================================================

    def register_artifact(
        self,
        source_path: Path | str,
        role: str,
        producer_run_id: str,
        *,
        expected_sha256: str | None = None,
        media_type: str | None = None,
    ) -> Artifact:
        """Hash a file and store it in the content-addressed blob area.

        Raises ``StoreError`` on hash mismatch or when *role* is
        ``private_raw`` (raw private bytes are forbidden).
        """
        path = Path(source_path)
        if role == "private_raw":
            raise StoreError("Artifact role 'private_raw' is forbidden")

        raw = path.read_bytes()
        sha = hash_bytes(raw)

        if expected_sha256 is not None and sha != expected_sha256:
            raise StoreError(
                f"Hash mismatch: expected {expected_sha256}, got {sha}"
            )

        dest_dir = self.workspace.artifacts / sha[:2]
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / sha

        if not dest.exists():
            shutil.copy2(str(path), str(dest))

        now = datetime.now(timezone.utc).isoformat()
        with self._db as conn:
            conn.execute(
                "INSERT OR REPLACE INTO artifacts "
                "(sha256, role, producer_run_id, disk_path, media_type, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [sha, role, producer_run_id, str(dest), media_type, now],
            )

        return Artifact(
            path=str(dest),
            sha256=sha,
            role=role,
            producer_run_id=producer_run_id,
            created_at=now,
            media_type=media_type,
        )

    def get_artifact(self, sha256: str, verify: bool = True) -> Artifact:
        """Retrieve an artifact by its SHA-256 digest.

        If *verify* is true the on-disk bytes are rehashed; raises
        ``StoreError`` on tamper detection.
        """
        row = self._db.execute(
            "SELECT sha256, role, producer_run_id, disk_path, media_type, created_at "
            "FROM artifacts WHERE sha256=?",
            [sha256],
        ).fetchone()
        if row is None:
            raise StoreError(f"Unknown artifact sha256={sha256}")

        disk = Path(row["disk_path"])
        if verify:
            actual = hash_bytes(disk.read_bytes())
            if actual != sha256:
                raise StoreError(f"Tampered artifact {sha256}: actual={actual}")

        return Artifact(
            path=row["disk_path"],
            sha256=row["sha256"],
            role=row["role"],
            producer_run_id=row["producer_run_id"],
            created_at=row["created_at"],
            media_type=row["media_type"],
        )

    # ======================================================================
    # Runs + lineage
    # ======================================================================

    def create_run(self, run: Run) -> Run:
        """Persist a new Run, writing both DB row and disk manifest."""
        d = run.to_dict()
        self._write_manifest(run.run_id, d)
        with self._db as conn:
            conn.execute(
                "INSERT OR REPLACE INTO runs (run_id, objective_id, stage, status, run_bytes) "
                "VALUES (?, ?, ?, ?, ?)",
                [run.run_id, run.objective_id, run.stage, run.status, canonical_json(d)],
            )
            # Register initial parents
            for p in run.parents:
                pid = p.get("run_id") or p.get("id")
                rel = p.get("relation", "parent")
                if pid:
                    conn.execute(
                        "INSERT OR IGNORE INTO lineage (child_run_id, parent_run_id, relation) "
                        "VALUES (?, ?, ?)",
                        [run.run_id, pid, rel],
                    )
        return run

    def update_run_status(self, run_id: str, status: RunStatus) -> None:
        """Atomically update a run's status, rewriting the manifest."""
        old_row = self._get_run_bytes(run_id)
        data = json.loads(old_row.decode())
        data["status"] = status.value
        manifest_path = self.workspace.runs / run_id / "manifest.json"
        try:
            _atomic_write_json(manifest_path, data)
        except StoreError:
            raise
        with self._db as conn:
            conn.execute(
                "UPDATE runs SET status=?, run_bytes=? WHERE run_id=?",
                [status.value, canonical_json(data), run_id],
            )

    def add_parent(self, child_run_id: str, parent_run_id: str, relation: str = "parent") -> None:
        """Append a lineage edge. Raises ``StoreError`` on duplicates."""
        with self._db as conn:
            existing = conn.execute(
                "SELECT 1 FROM lineage WHERE child_run_id=? AND parent_run_id=?",
                [child_run_id, parent_run_id],
            ).fetchone()
            if existing:
                raise StoreError(
                    f"Lineage edge ({child_run_id}, {parent_run_id}) already exists"
                )
            conn.execute(
                "INSERT INTO lineage (child_run_id, parent_run_id, relation) "
                "VALUES (?, ?, ?)",
                [child_run_id, parent_run_id, relation],
            )

    def get_run(self, run_id: str) -> Run | None:
        row = self._get_run_bytes(run_id)
        if row is None:
            return None
        return Run.from_dict(json.loads(row.decode()))

    def _get_run_bytes(self, run_id: str) -> bytes | None:
        r = self._db.execute(
            "SELECT run_bytes FROM runs WHERE run_id=?",
            [run_id],
        ).fetchone()
        return r[0] if r else None

    # ======================================================================
    # Metrics (JSONL append-only per run)
    # ======================================================================

    def append_metric(self, run_id: str, record: dict[str, Any]) -> None:
        """Append one JSON line to the run's metrics stream."""
        mp = self.workspace.runs / run_id / "metrics.jsonl"
        mp.parent.mkdir(parents=True, exist_ok=True)
        with open(mp, "a") as f:
            f.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")

    def tail_metrics(self, run_id: str, n: int) -> list[dict[str, Any]]:
        """Return the last *n* metric records from the run's metrics file."""
        mp = self.workspace.runs / run_id / "metrics.jsonl"
        if not mp.exists():
            return []
        lines = mp.read_text().splitlines()
        result = []
        for line in lines[-n:]:
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return result

    # ======================================================================
    # Mission Briefs
    # ======================================================================

    def _brief_path(self, brief_id: str, version: int) -> Path:
        p = self.workspace.mission_briefs / brief_id / f"v{version}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def save_mission_brief(self, brief: MissionBrief) -> MissionBrief:
        """Save an immutable version of a MissionBrief.

        Atomic write of canonical JSON to disk; indexes its hash in DB.
        The ``brief_hash`` field is always set from the actual content so
        tamper-verification on load is reliable.
        """
        d = brief.to_dict()
        now = datetime.now(timezone.utc).isoformat()
        d["created_at"] = now

        # Compute hash over everything EXCEPT derived brief_hash (like type.content_hash)
        payload_without_hash = {k: v for k, v in d.items() if k != "brief_hash"}
        h = hash_obj(payload_without_hash)
        d["brief_hash"] = h

        path = self._brief_path(brief.id, brief.version)
        try:
            _atomic_write_json(path, d)
        except StoreError:
            raise
        with self._db as conn:
            conn.execute(
                "INSERT OR REPLACE INTO mission_briefs "
                "(brief_id, version, brief_hash) VALUES (?, ?, ?)",
                [brief.id, brief.version, h],
            )

        return MissionBrief.from_dict(d)

    def _compute_brief_hash(self, data: dict[str, Any]) -> str:
        """Hash a brief payload excluding the derived ``brief_hash`` field.

        Matches how ``save_mission_brief`` computes the stored hash,
        so load-time verification is symmetric.
        """
        payload = {k: v for k, v in data.items() if k != "brief_hash"}
        return hash_obj(payload)

    def get_mission_brief(self, brief_id: str, version: int) -> MissionBrief:
        """Load brief from disk, verify content-hash against DB index."""
        path = self._brief_path(brief_id, version)
        raw = path.read_bytes()
        data = json.loads(raw.decode())
        row = self._db.execute(
            "SELECT brief_hash FROM mission_briefs WHERE brief_id=? AND version=?",
            [brief_id, version],
        ).fetchone()
        if row is None:
            raise StoreError(f"No mission brief {brief_id} v{version}")
        actual = self._compute_brief_hash(data)
        if actual != row["brief_hash"]:
            raise StoreError(
                f"MissionBrief tampered: expected {row['brief_hash']}, got {actual}"
            )
        return MissionBrief.from_dict(data)

    def list_mission_brief_versions(self, brief_id: str) -> list[MissionBrief]:
        rows = self._db.execute(
            "SELECT version FROM mission_briefs "
            "WHERE brief_id=? ORDER BY version ASC",
            [brief_id],
        ).fetchall()
        return [self.get_mission_brief(brief_id, r["version"]) for r in rows]

    def list_mission_briefs(self, objective_id: str | None = None) -> list[MissionBrief]:
        """List newest saved versions first."""
        rows = self._db.execute(
            "SELECT brief_id, MAX(version) AS mv FROM mission_briefs GROUP BY brief_id ORDER BY mv DESC"
        ).fetchall()
        return [
            self.get_mission_brief(r["brief_id"], r["mv"])
            for r in rows
        ]

    # ======================================================================
    # Objectives (bytes-level ops; lint/freeze in phase 03)
    # ======================================================================

    def get_objective(self, objective_id: str) -> Any:
        """Return a typed Objective instance loaded from the store."""
        from facktry.objective import load_objective
        return load_objective(self, objective_id)

    def save_objective(self, obj: Any, *, frozen: bool = True) -> None:
        """Save a typed Objective via canonical JSON and content hash."""
        d = obj.to_dict()
        b = canonical_json(d)
        h = hash_bytes(b)
        self.save_objective_bytes(obj.id, b, expected_hash=h, frozen=frozen)

    def save_objective_bytes(
        self,
        objective_id: str,
        obj_bytes: bytes,
        *,
        expected_hash: str | None = None,
        frozen: bool = True,
    ) -> None:
        """Write objective bytes atomically to disk; index hash in DB."""
        declared_hash = expected_hash or hash_bytes(obj_bytes)
        path = self.workspace.objectives / f"{objective_id}.json"
        try:
            _atomic_write_json(path, json.loads(obj_bytes.decode()))
        except StoreError:
            raise
        with self._db as conn:
            conn.execute(
                "INSERT OR REPLACE INTO objectives "
                "(objective_id, obj_hash, frozen) VALUES (?, ?, ?)",
                [objective_id, declared_hash, frozen],
            )

    def load_objective_bytes(
        self,
        objective_id: str,
        verify: bool = False,
    ) -> bytes | None:
        """Read objective bytes from disk; optionally verify against DB hash."""
        path = self.workspace.objectives / f"{objective_id}.json"
        if not path.exists():
            return None
        raw = path.read_bytes()
        if verify:
            row = self._db.execute(
                "SELECT obj_hash FROM objectives WHERE objective_id=?",
                [objective_id],
            ).fetchone()
            if row is None:
                raise StoreError(f"Unknown objective {objective_id}")
            actual = hash_obj(json.loads(raw.decode()))
            if actual != row["obj_hash"]:
                raise StoreError(
                    f"Hash mismatch for {objective_id}: {actual} != {row['obj_hash']}"
                )
        return raw


    def active_objectives(self) -> list[str]:
        rows = self._db.execute(
            "SELECT objective_id FROM objectives WHERE frozen=0 ORDER BY ROWID DESC"
        ).fetchall()
        return [r[0] for r in rows]

    def frozen_objectives(self) -> list[str]:
        rows = self._db.execute(
            "SELECT objective_id FROM objectives WHERE frozen=1 ORDER BY ROWID DESC"
        ).fetchall()
        return [r[0] for r in rows]

    # =====================================================================
    # Suites
    # =====================================================================

    def register_suite(self, suite_obj: Any) -> None:
        """Register a suite with atomic manifest write + hash verification.

        Same id + different content = separate directory entry, never overwrite.
        Dialogue suites must include at least one multi-turn case.
        """
        from facktry.errors import StoreError
        from facktry.hashing import hash_file, hash_obj

        suite_data = suite_obj.to_dict()
        computed_hash = suite_obj.content_hash()
        dir_name = f"{suite_obj.id}@{computed_hash}"
        target_dir = self.workspace.suites / dir_name
        target_path = target_dir / "suite.json"

        # Lint: dialogue=true requires multi-turn cases.
        metadata = suite_data.get("metadata", {})
        if metadata.get("dialogue") is True:
            has_multiturn = any(
                c.get("kind") == "multi_turn" for c in suite_data.get("cases", [])
            )
            if not has_multiturn:
                raise StoreError(
                    f"Dialogue suite {suite_obj.id} lacks multi-turn cases",
                )

        target_dir.mkdir(parents=True, exist_ok=True)
        try:
            _atomic_write_json(target_path, suite_data)
        except StoreError:
            raise

        with self._db as conn:
            conn.execute(
                "INSERT OR IGNORE INTO suites "
                "(suite_id, suite_hash, path) VALUES (?, ?, ?)",
                [suite_obj.id, computed_hash, str(target_path)],
            )

    def get_suite(self, suite_id: str, suite_hash: str) -> Any:
        """Retrieve a suite by id+hash; verifies hash on load."""
        obj = self.load_suite(suite_id, suite_hash, verify=True)
        return obj

    def load_suite(self, suite_id: str, suite_hash: str, *, verify: bool = False) -> Any:
        """Load suite from disk; optional hash verification.

        Raises ``StoreError`` on tampered bytes when verify=True.
        """
        from facktry.errors import StoreError
        from facktry.hashing import hash_obj
        from facktry.suite.types import Suite

        row = self._db.execute(
            "SELECT path FROM suites WHERE suite_id=? AND suite_hash=?",
            [suite_id, suite_hash],
        ).fetchone()
        if row is None:
            raise StoreError(f"Suite {suite_id}@{suite_hash[:8]}... not found")

        path_str = row[0]
        path_obj = Path(path_str)
        if not path_obj.exists():
            raise StoreError(f"Suite file missing at {path_str}")

        if verify:
            try:
                data_bytes = path_obj.read_bytes()
                loaded_data = json.loads(data_bytes)
                temp_suite = Suite.from_dict(loaded_data)
                computed = temp_suite.content_hash()
                if computed != suite_hash:
                    raise StoreError(
                        f"Suite {suite_id}@{suite_hash[:8]}... hash mismatch "
                        f"(expected={suite_hash[:12]}, got={computed[:12]})",
                    )
            except StoreError:
                raise
            except Exception as e:
                raise StoreError(
                    f"Suite {suite_id}@{suite_hash[:8]}... tampered or corrupt: {e}",
                ) from e

        try:
            suite_json = path_obj.read_text()
        except Exception as e:
            raise StoreError(f"Cannot read suite file: {e}") from e
        return Suite.from_dict(json.loads(suite_json))

    # ======================================================================
    # Decisions
    # ======================================================================

    def save_decision(self, decision: Decision) -> None:
        d = decision.to_dict()
        b = canonical_json(d)
        with self._db as conn:
            conn.execute(
                "INSERT OR REPLACE INTO decisions (decision_id, objective_id, dec_bytes) "
                "VALUES (?, ?, ?)",
                [decision.__class__.__name__ + "-" + decision.objective_id,
                 decision.objective_id, b],
            )

    def latest_decision(self, objective_id: str) -> Decision | None:
        row = self._db.execute(
            "SELECT dec_bytes FROM decisions WHERE objective_id=? "
            "ORDER BY created_at DESC LIMIT 1",
            [objective_id],
        ).fetchone()
        if row is None:
            return None
        return Decision.from_dict(json.loads(row["dec_bytes"].decode()))

    # ======================================================================
    # Defects
    # ======================================================================

    def save_defect(self, defect: Defect) -> None:
        d = defect.to_dict()
        b = canonical_json(d)
        with self._db as conn:
            conn.execute(
                "INSERT INTO defects (defect_id, taxonomy, evidence, first_run_id, "
                "last_run_id, interventions, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [d["id"], d["taxonomy"], json.dumps(d["evidence"]),
                 d["first_run_id"], d["last_run_id"],
                 json.dumps(d["interventions"]), d["status"]],
            )

    def open_defects(self) -> list[Defect]:
        rows = self._db.execute(
            "SELECT * FROM defects WHERE status='open' ORDER BY created_at DESC"
        ).fetchall()
        return [
            Defect.from_dict({
                "id": r["defect_id"],
                "taxonomy": r["taxonomy"],
                "evidence": json.loads(r["evidence"]),
                "first_run_id": r["first_run_id"],
                "last_run_id": r["last_run_id"],
                "interventions": json.loads(r["interventions"]),
                "status": r["status"],
            })
            for r in rows
        ]

    # ======================================================================
    # Inbox
    # ======================================================================

    def save_inbox_item(self, item: HumanInboxItem) -> None:
        d = item.to_dict()
        b = canonical_json(d)
        with self._db as conn:
            conn.execute(
                "INSERT OR REPLACE INTO inbox "
                "(item_id, objective_id, gate_name, payload_ref, response_schema, item_bytes) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [item.id, item.objective_id, item.gate_name,
                 item.payload_ref, json.dumps(item.response_schema), b],
            )

    def pending_inbox(self) -> list[HumanInboxItem]:
        rows = self._db.execute(
            "SELECT item_bytes FROM inbox ORDER BY created_at DESC"
        ).fetchall()
        result = []
        for r in rows:
            try:
                d = json.loads(r["item_bytes"].decode())
                if d.get("status") == "pending":
                    result.append(HumanInboxItem.from_dict(d))
            except (json.JSONDecodeError, SerdeError):
                continue
        return result

    # ======================================================================
    # Pinned production tuple
    # ======================================================================

    def pin_production_tuple(self, rt: ReleaseTuple, objective_id: str | None = "default") -> None:
        b = canonical_json(rt.to_dict())
        with self._db as conn:
            conn.execute(
                "INSERT OR REPLACE INTO pinned_tuple (objective_id, tuple_bytes) "
                "VALUES (?, ?)",
                [objective_id, b],
            )

    def pinned_production_tuple(self, objective_id: str | None = None) -> ReleaseTuple | None:
        if objective_id:
            oid = objective_id
        else:
            oid = "default"
        row = self._db.execute(
            "SELECT tuple_bytes FROM pinned_tuple WHERE objective_id=?",
            [oid],
        ).fetchone()
        if row is None:
            return None
        return ReleaseTuple.from_dict(json.loads(row["tuple_bytes"].decode()))

    # ======================================================================
    # Budget ledger
    # ======================================================================

    def seed_budget(
        self,
        objective_id: str,
        ledger_bytes: bytes,
    ) -> None:
        """Write initial BudgetLedger row for an objective.

        Called lazily on first charge_budget; transactional via context manager.
        """
        with self._db as conn:
            conn.execute(
                "INSERT OR REPLACE INTO budget_ledger (objective_id, ledger_bytes) VALUES (?, ?)",
                [objective_id, ledger_bytes],
            )

    def save_budget(
        self,
        objective_id: str,
        ledger_bytes: bytes,
    ) -> None:
        """Update (or upsert) the BudgetLedger for an objective."""
        with self._db as conn:
            conn.execute(
                "INSERT OR REPLACE INTO budget_ledger (objective_id, ledger_bytes) VALUES (?, ?)",
                [objective_id, ledger_bytes],
            )

    def load_budget(self, objective_id: str) -> BudgetLedger:
        """Load the BudgetLedger for an objective.

        Raises ``StoreError`` if not yet seeded.
        """
        row = self._db.execute(
            "SELECT ledger_bytes FROM budget_ledger WHERE objective_id=?",
            [objective_id],
        ).fetchone()
        if row is None:
            raise StoreError(f"No budget ledger for objective {objective_id}")
        return BudgetLedger.from_dict(json.loads(row[0].decode()))

    # ======================================================================
    # Recipes + stacks + notes
    # ======================================================================

    def save_recipe(self, recipe: Recipe) -> None:
        existing = self._db.execute(
            "SELECT 1 FROM recipes WHERE recipe_id=? AND version=?",
            [recipe.id, recipe.version],
        ).fetchone()
        if existing:
            raise StoreError(f"Recipe {recipe.id} v{recipe.version} already exists")
        b = canonical_json(recipe.to_dict())
        with self._db as conn:
            conn.execute(
                "INSERT INTO recipes (recipe_id, version, instruction_hash, recipe_bytes) "
                "VALUES (?, ?, ?, ?)",
                [recipe.id, recipe.version, recipe.instruction_hash, b],
            )

    def show_recipe(self, recipe_id: str, version: str) -> Recipe:
        row = self._db.execute(
            "SELECT recipe_bytes FROM recipes WHERE recipe_id=? AND version=?",
            [recipe_id, version],
        ).fetchone()
        if row is None:
            raise StoreError(f"No recipe {recipe_id} v{version}")
        return Recipe.from_dict(json.loads(row["recipe_bytes"].decode()))

    def append_recipe_note(
        self,
        recipe_id: str,
        version: str,
        note: dict[str, Any],
    ) -> Recipe:
        """Append a structured use-note to a recipe.

        The note does not change the instruction hash. Returns the original
        Recipe augmented with the updated notes_head.
        """
        note_bytes = canonical_json(note)
        with self._db as conn:
            conn.execute(
                "INSERT INTO recipe_notes (recipe_id, version, note_bytes) VALUES (?, ?, ?)",
                [recipe_id, version, note_bytes],
            )
        # Fetch the current recipe and update its notes_head
        row = self._db.execute(
            "SELECT recipe_bytes FROM recipes WHERE recipe_id=? AND version=?",
            [recipe_id, version],
        ).fetchone()
        if row is None:
            raise StoreError(f"No recipe {recipe_id} v{version}")
        recipe = Recipe.from_dict(json.loads(row["recipe_bytes"].decode()))
        return recipe

    def save_recipe_stack(self, stack: RecipeStack) -> None:
        d = stack.to_dict()
        _atomic_write_json(self.workspace.recipe_stacks / f"{stack.stack_hash}.json", d)
        # Also index in DB for queries
        with self._db as conn:
            conn.execute(
                "INSERT OR REPLACE INTO recipe_stacks_db (stack_hash, id, stack_bytes) "
                "VALUES (?, ?, ?)",
                [stack.stack_hash, stack.id, canonical_json(d)],
            )

    def load_recipe_stack(
        self,
        stack_hash: str,
        verify: bool = False,
    ) -> RecipeStack:
        path = self.workspace.recipe_stacks / f"{stack_hash}.json"
        raw = path.read_bytes()
        if verify:
            # Compare raw bytes against declared hash (avoids JSON parse on corrupted files)
            actual = hash_bytes(raw)
            if actual != stack_hash:
                raise StoreError(f"Tampered recipe stack {stack_hash}: {actual}")
        data = json.loads(raw.decode())
        return RecipeStack.from_dict(data)

    def list_recipes(self) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT recipe_id, version, instruction_hash FROM recipes ORDER BY ROWID DESC"
        ).fetchall()
        return [{"id": r[0], "version": r[1], "instruction_hash": r[2]} for r in rows]

    def list_recipe_stacks(self) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT stack_hash, id FROM recipe_stacks_db ORDER BY ROWID DESC"
        ).fetchall()
        return [{"hash": r[0], "id": r[1]} for r in rows]

    # ======================================================================
    # Admission reports
    # ======================================================================

    def save_admission_report(
        self,
        objective_id: str,
        report: AdmissionReport,
    ) -> None:
        d = report.to_dict()
        b = canonical_json(d)
        h = hash_bytes(b)
        with self._db as conn:
            conn.execute(
                "INSERT OR IGNORE INTO admissions (objective_id, report_hash, report_bytes, passed) "
                "VALUES (?, ?, ?, ?)",
                [objective_id, h, b, report.passed],
            )

    def latest_passing_admission(self, objective_id: str) -> AdmissionReport | None:
        row = self._db.execute(
            "SELECT report_bytes FROM admissions "
            "WHERE objective_id=? AND passed=1 "
            "ORDER BY created_at DESC LIMIT 1",
            [objective_id],
        ).fetchone()
        if row is None:
            return None
        return AdmissionReport.from_dict(json.loads(row["report_bytes"].decode()))

    # ======================================================================
    # Run deletion policy
    # ======================================================================

    def delete_run(self, run_id: str) -> None:
        """Delete a run unless it is protected by lineage or explicit markers.

        Protected when:
        - another run lists it as a parent (has children)
        - it was registered via ``protect_run`` (e.g., pinned release, decision subject)
        """
        # 1. Has children?
        if self.children_of(run_id):
            raise StoreError(f"Cannot delete run {run_id}: has_children")

        # 2. Explicitly protected?
        row = self._db.execute(
            "SELECT reason FROM run_protection WHERE run_id=?",
            [run_id],
        ).fetchone()
        if row:
            raise StoreError(f"Cannot delete run {run_id}: {row['reason']}")

        self._db.execute("DELETE FROM runs WHERE run_id=?", [run_id])
        self._db.execute("DELETE FROM lineage WHERE child_run_id=?", [run_id])
        self._db.execute("DELETE FROM lineage WHERE parent_run_id=?", [run_id])

        manifest_dir = self.workspace.runs / run_id
        if manifest_dir.exists():
            shutil.rmtree(str(manifest_dir))

    def protect_run(self, run_id: str, reason: str, ref_id: str | None = None) -> None:
        """Register that *run_id* must not be deleted."""
        with self._db as conn:
            conn.execute(
                "INSERT OR IGNORE INTO run_protection (run_id, reason, ref_id) "
                "VALUES (?, ?, ?)",
                [run_id, reason, ref_id or ""],
            )

    # ======================================================================
    # Query helpers
    # ======================================================================

    def runs_by(
        self,
        *,
        objective_id: str | None = None,
        status: str | None = None,
        stage: str | None = None,
    ) -> list[Run]:
        clauses = []
        params: list[Any] = []
        if objective_id:
            clauses.append("objective_id=?")
            params.append(objective_id)
        if status:
            clauses.append("status=?")
            params.append(status)
        if stage:
            clauses.append("stage=?")
            params.append(stage)
        where = " AND ".join(clauses) if clauses else "1=1"
        rows = self._db.execute(
            f"SELECT run_bytes FROM runs WHERE {where} ORDER BY ROWID DESC",
            params,
        ).fetchall()
        return [Run.from_dict(json.loads(r["run_bytes"].decode())) for r in rows]

    def parents_of(self, run_id: str) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT parent_run_id, relation FROM lineage WHERE child_run_id=?",
            [run_id],
        ).fetchall()
        return [{"run_id": r[0], "relation": r[1]} for r in rows]

    def children_of(self, run_id: str) -> list[dict[str, Any]]:
        rows = self._db.execute(
            "SELECT child_run_id, relation FROM lineage WHERE parent_run_id=?",
            [run_id],
        ).fetchall()
        return [{"run_id": r[0], "relation": r[1]} for r in rows]

    def query_snapshot(self, objective_id: str) -> dict[str, Any]:
        """Return a deterministic snapshot of store state for *objective_id*.

        Used by tests to verify rebuild_index restores equivalence.
        """
        return {
            "objectives": set(self.active_objectives() + self.frozen_objectives()),
            "runs": [(r.run_id, r.status, r.stage) for r in self.runs_by(objective_id=objective_id)],
            "briefs": [b.id for b in self.list_mission_briefs()],
            "decisions": [d.action if d else None for d in (self.latest_decision(objective_id),)],
            "defects": [d.id for d in self.open_defects()],
            "admission": self.latest_passing_admission(objective_id) is not None,
            "inbox_count": len(self.pending_inbox()),
            "recipes": [r["id"] for r in self.list_recipes()],
            "stacks": [r["id"] for r in self.list_recipe_stacks()],
        }

    # ======================================================================
    # Index rebuild
    # ======================================================================

    def rebuild_index(self) -> None:
        """Rebuild the SQLite index from scratch by re-executing schema init.

        After calling, the DB needs to be repopulated. This is intended as an
        escape hatch when the index corrupts — callers should call the seeding
        operations again.
        """
        old_conn = self._db
        try:
            old_conn.close()
        except sqlite3.ProgrammingError:
            pass
        # Remove the file so it starts fresh
        self.workspace.index.unlink(missing_ok=True)
        self._db = _conn(self.workspace)

    # ======================================================================
    # Internal: manifest I/O
    # ======================================================================

    def _write_manifest(self, run_id: str, data: dict[str, Any]) -> Path:
        """Write run.manifest.json atomically."""
        path = self.workspace.runs / run_id / "manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(path, data)
        return path

    # -----------------------------------------------------------------
    # Compatibility with conftest.seed_run which calls create_run directly
    # and also expects workspace property access patterns used by tests
    # -----------------------------------------------------------------

    @property
    def db(self) -> sqlite3.Connection:
        """Access to the underlying connection (for test fixtures)."""
        return self._db
