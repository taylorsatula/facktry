"""Fail-closed govern checks for Facktry.

Every mutation path goes through govern. Denials are typed exceptions — never
boolean-return-and-continue.  See ADR §7.10.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .errors import (
    BudgetExhausted,
    CompatMismatch,
    GovernDenial,
    MissionBriefRequired,
    PolicyDenied,
    PreflightFailed,
    SmokeGateUnsatisfied,
    StoreError,
    SuiteNotPinned,
)
from .hashing import canonical_json
from .types import BudgetLedger, ReleaseTuple, RunStatus

# ---------------------------------------------------------------------------
# Capability vocabulary
# ---------------------------------------------------------------------------

TRAIN_SMOKE = "train.smoke"
TRAIN_SCALE = "train.scale"
SERVE_FLIP_DEFAULT = "serve.flip_default"
DATA_USE_PRIVATE = "data.use_private"
DATA_REMOTE_SEND = "data.remote_send"
JUDGE_USE = "judge.use"
OBJECTIVE_SUPERSEDE = "objective.supersede"
ADMIT_RUN = "admit.run"
MEASURE_SEALED = "measure.sealed"

KNOWN_CAPABILITIES = frozenset(
    [
        TRAIN_SMOKE,
        TRAIN_SCALE,
        SERVE_FLIP_DEFAULT,
        DATA_USE_PRIVATE,
        DATA_REMOTE_SEND,
        JUDGE_USE,
        OBJECTIVE_SUPERSEDE,
        ADMIT_RUN,
        MEASURE_SEALED,
    ],
)

# ---------------------------------------------------------------------------
# Helpers: hardware probing
# ---------------------------------------------------------------------------


def probe_gpus() -> list[dict[str, Any]]:
    """Probe GPUs via nvidia-smi; degrade gracefully on failure."""
    gpus: list[dict[str, Any]] = []
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,memory.total,memory.used",
             "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    gpus.append({
                        "index": int(parts[0]),
                        "name": parts[1],
                        "memory_total_mb": int(parts[2]),
                        "memory_used_mb": int(parts[3]) if len(parts) > 3 else 0,
                    })
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError, ValueError):
        pass

    # If no GPUs found, record a degraded entry
    if not gpus:
        gpus.append({"unavailable": True, "reason": "no GPU detected or NVML unavailable"})
    return gpus


def _probe_cpu() -> dict[str, Any]:
    cpu_count = os.cpu_count()
    return {
        "cpu_count": cpu_count,
        "architecture": platform.machine(),
        "processor": platform.processor() or "unknown",
    }


def _probe_ram() -> dict[str, Any]:
    total_bytes = None
    free_bytes = None
    try:
        from psutil import virtual_memory
        vmem = virtual_memory()
        total_bytes = vmem.total
        free_bytes = vmem.available
    except ImportError:
        # Best-effort fallback: read /proc/meminfo on Linux
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        total_bytes = int(line.split()[1]) * 1024
                    elif line.startswith("MemAvailable:"):
                        free_bytes = int(line.split()[1]) * 1024
        except FileNotFoundError:
            pass
    return {
        "total_bytes": total_bytes,
        "free_bytes": free_bytes,
    }


def _get_disk_free(path: str | Path) -> int:
    """Return free bytes on the filesystem containing *path*."""
    usage = shutil.disk_usage(str(path))
    return usage.free


# ---------------------------------------------------------------------------
# Hardware snapshot persistence
# ---------------------------------------------------------------------------

_HARDWARE_KEY_NAMES = ("cpu", "ram", "gpus", "disk_free_bytes", "probed_at")


def _load_hardware_profile(ws_root: Path) -> dict[str, Any] | None:
    profile_path = ws_root / "hardware.json"
    if profile_path.exists():
        try:
            data = json.loads(profile_path.read_text())
            # Validate it has the expected keys
            if all(k in data for k in _HARDWARE_KEY_NAMES):
                return data
        except (json.JSONDecodeError, KeyError):
            pass
    return None


def _write_hardware_profile(ws_root: Path, profile: dict[str, Any]) -> None:
    profile_path = ws_root / "hardware.json"
    tmp = profile_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(profile, sort_keys=True))
    os.replace(str(tmp), str(profile_path))


def _build_hardware_profile(ws_root: Path) -> dict[str, Any]:
    """Build a fresh hardware profile by probing the machine."""
    gpus = []
    try:
        gpus = probe_gpus()
    except (OSError, RuntimeError):
        gpus.append({"unavailable": True, "reason": "GPU probe failed"})
    return {
        "cpu": _probe_cpu(),
        "ram": _probe_ram(),
        "gpus": gpus,
        "disk_free_bytes": _get_disk_free(ws_root),
        "probed_at": datetime.now(timezone.utc).isoformat(),
    }


def get_hardware_snapshot(ws_root: Path) -> dict[str, Any]:
    """Read cached profile or probe and cache on first call."""
    existing = _load_hardware_profile(ws_root)
    if existing is not None:
        return existing
    profile = _build_hardware_profile(ws_root)
    _write_hardware_profile(ws_root, profile)
    return profile


# ---------------------------------------------------------------------------
# PreflightReport
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PreflightReport:
    workspace_root: Path
    disk_free_bytes: int
    hardware: dict[str, Any]
    gpus: list[dict[str, Any]]
    preservation_paths_ok: bool
    gpu_conflict: str | None = None


# ---------------------------------------------------------------------------
# CompatResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CompatResult:
    passed: bool
    mismatches: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# BudgetCost helper
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BudgetCost:
    wall_time: float | int = 0
    gpu_hours: float | int = 0
    judge_tokens: int = 0
    smoke_runs: int = 0
    scale_runs: int = 0


# ======================================================================
# Govern functions
# ======================================================================


def mission_brief_required(
    store: Any,
    objective_id: str,
    experiment_spec: dict | None = None,
) -> None:
    """Deny any experiment when the Objective lacks a matching saved MissionBrief.

    Raises ``MissionBriefRequired`` with details about the missing/mismatched ref.
    """
    from .objective import load_objective

    obj = load_objective(store, objective_id)
    brief_ref = obj.mission_brief
    try:
        stored = store.get_mission_brief(brief_ref.id, brief_ref.version)
    except (StoreError, FileNotFoundError):
        raise MissionBriefRequired(
            f"No saved MissionBrief {brief_ref.id} v{brief_ref.version} for objective {objective_id}",
            reason="mission_brief_missing",
            details={
                "objective_id": objective_id,
                "brief_id": brief_ref.id,
                "brief_version": brief_ref.version,
            },
        )

    # Verify hash matches what was recorded at freeze time
    actual_hash = stored.brief_hash
    if actual_hash != brief_ref.brief_hash:
        raise MissionBriefRequired(
            f"MissionBrief hash mismatch for objective {objective_id}: "
            f"expected {brief_ref.brief_hash}, got {actual_hash}",
            reason="mission_brief_hash_mismatch",
            details={
                "objective_id": objective_id,
                "brief_id": brief_ref.id,
                "brief_version": brief_ref.version,
                "expected_hash": brief_ref.brief_hash,
                "actual_hash": actual_hash,
            },
        )


def preflight(
    store: Any,
    objective_id: str | None = None,
    *,
    disk_floor_bytes: int = 5 * 1024**3,  # default 5 GiB
) -> PreflightReport:
    """Machine-state and safety preflight check.

    Probes hardware, checks disk headroom, verifies preservation paths.
    If an objective is provided, also checks GPU exclusivity against
    ``<workspace_root>/preflight.json``.

    Returns a :class:`PreflightReport` on success.
    Raises ``PreflightFailed`` on any violation.
    """
    ws_root = store.workspace.root

    # -- Disk headroom ----------------------------------------------------------
    disk_free = _get_disk_free(ws_root)
    if disk_free < disk_floor_bytes:
        raise PreflightFailed(
            f"Insufficient disk space: {disk_free} free, need >= {disk_floor_bytes}",
            reason="disk_full",
            details={"free_bytes": disk_free, "floor_bytes": disk_floor_bytes},
        )

    # -- Hardware snapshot (auto-cache) -----------------------------------------
    hw = get_hardware_snapshot(ws_root)
    gpus = hw.get("gpus", [])

    # -- Preservation path checks -----------------------------------------------
    pins_dir = ws_root / "pins"
    runs_dir = ws_root / "runs"
    try:
        pins_dir.mkdir(parents=True, exist_ok=True)
        runs_dir.mkdir(parents=True, exist_ok=True)
        preservation_ok = True
    except OSError as exc:
        preservation_ok = False
        raise PreflightFailed(
            f"Preservation path not writable: {exc}",
            reason="preservation_path_unwritable",
            details={"path": str(pins_dir)},
        )

    # -- GPU exclusivity (only when objective supplied) -------------------------
    gpu_conflict = None
    if objective_id is not None:
        config_path = ws_root / "preflight.json"
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text())
                occupied = config.get("occupied_services", [])
                for svc in occupied:
                    if svc.get("large_model"):
                        occupied_gpus = set(svc.get("gpus", []))
                        if occupied_gpus:
                            gpu_conflict = (
                                f"Conflict with service '{svc.get('name')}' on GPU(s) {sorted(occupied_gpus)}"
                            )
                            raise PreflightFailed(
                                gpu_conflict,
                                reason="gpu_exclusivity_conflict",
                                details={"service": svc.get("name"), "gpus": sorted(occupied_gpus)},
                            )
            except PreflightFailed:
                raise
            except (json.JSONDecodeError, KeyError):
                pass  # ignore malformed config; don't block on bad JSON

    return PreflightReport(
        workspace_root=ws_root,
        disk_free_bytes=disk_free,
        hardware=hw,
        gpus=gpus,
        preservation_paths_ok=preservation_ok,
        gpu_conflict=gpu_conflict,
    )


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------


def check_policy(store: Any, objective_id: str, capability: str) -> None:
    """Allow/deny per the frozen objective's policy.

    Capabilities must be explicitly allowed. Unknown capabilities are denied.
    Raises ``PolicyDenied``.
    """
    from .objective import load_objective

    obj = load_objective(store, objective_id)
    policy_caps = (obj.policy or {}).get("capabilities", {})

    if capability in policy_caps:
        if not policy_caps[capability]:
            raise PolicyDenied(
                f"Capability {capability!r} explicitly denied by objective policy",
                reason="policy_denied",
                details={"capability": capability, "objective_id": objective_id},
            )
        return  # explicitly allowed

    # Not in allowlist → deny unknown capabilities by default
    raise PolicyDenied(
        f"Capability {capability!r} not allowed by objective policy",
        reason="policy_denied",
        details={"capability": capability, "objective_id": objective_id},
    )


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------


def charge_budget(
    store: Any,
    objective_id: str,
    action: str,
    cost: BudgetCost,
) -> None:
    """Atomically decrement the objective's remaining budget.

    Lazily seeds the ledger on first call by reading the frozen
    objective's budget dict. Uses a Python-level lock plus a dedicated
    SQLite connection (WAL mode supports concurrent writes) so concurrent
    charges cannot overspend.

    Raises ``BudgetExhausted`` if any dimension would go negative.
    """
    import sqlite3
    import threading

    # Per-objective lock for cross-thread atomicity.
    lock_name = f"_budget_lock_{objective_id}"
    if not hasattr(store, lock_name):
        setattr(store, lock_name, threading.Lock())
    lock: threading.Lock = getattr(store, lock_name)

    db_path = str(store.workspace.index)

    with lock:
        # Open a fresh connection so SQLite's same-thread check passes.
        # WAL mode allows concurrent access safely.
        conn = sqlite3.connect(db_path, isolation_level=None)
        try:
            row = conn.execute(
                "SELECT ledger_bytes FROM budget_ledger WHERE objective_id=?",
                [objective_id],
            ).fetchone()

            if row is None:
                # Lazy seed: read the objective budget dict.
                # Read the file directly — avoid store._db (cross-thread unsafe).
                obj_path = store.workspace.objectives / f"{objective_id}.json"
                with open(obj_path) as f:
                    obj_data = json.loads(f.read())
                obj_budget = obj_data.get("budget", {})
                ledger_data = {
                    "wall_time": obj_budget.get("wall_time", 0),
                    "gpu_hours": obj_budget.get("gpu_hours", 0),
                    "judge_tokens": obj_budget.get("judge_tokens", 0),
                    "smoke_runs": obj_budget.get("smoke_runs", 0),
                    "scale_runs": obj_budget.get("scale_runs", 0),
                }
                ledger = BudgetLedger(**ledger_data)
                b = canonical_json(ledger.to_dict())
                conn.execute(
                    "INSERT OR REPLACE INTO budget_ledger (objective_id, ledger_bytes) VALUES (?, ?)",
                    [objective_id, b],
                )
            else:
                ledger = BudgetLedger.from_dict(json.loads(row[0].decode()))

            # Check each dimension before charging
            remaining_wall = ledger.wall_time - cost.wall_time
            remaining_gpu = ledger.gpu_hours - cost.gpu_hours
            remaining_judge = ledger.judge_tokens - cost.judge_tokens
            remaining_smoke = ledger.smoke_runs - cost.smoke_runs
            remaining_scale = ledger.scale_runs - cost.scale_runs

            exhausted_dim = []
            if remaining_wall < 0:
                exhausted_dim.append(f"wall_time ({remaining_wall})")
            if remaining_gpu < 0:
                exhausted_dim.append(f"gpu_hours ({remaining_gpu})")
            if remaining_judge < 0:
                exhausted_dim.append(f"judge_tokens ({remaining_judge})")
            if remaining_smoke < 0:
                exhausted_dim.append(f"smoke_runs ({remaining_smoke})")
            if remaining_scale < 0:
                exhausted_dim.append(f"scale_runs ({remaining_scale})")

            if exhausted_dim:
                raise BudgetExhausted(
                f"Insufficient budget for {action}: exhausted {', '.join(exhausted_dim)}",
                reason="budget_exhausted",
                details={
                    "objective_id": objective_id,
                    "action": action,
                    "cost": cost.__dict__ if hasattr(cost, "__dict__") else vars(cost),
                    "exhausted_dimensions": exhausted_dim,
                },
            )

            # Persist decremented ledger
            updated = BudgetLedger(
                wall_time=remaining_wall,
                gpu_hours=remaining_gpu,
                judge_tokens=remaining_judge,
                smoke_runs=remaining_smoke,
                scale_runs=remaining_scale,
            )
            b = canonical_json(updated.to_dict())
            conn.execute(
                "INSERT OR REPLACE INTO budget_ledger (objective_id, ledger_bytes) VALUES (?, ?)",
                [objective_id, b],
            )
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Compat check
# ---------------------------------------------------------------------------

_INTERFACE_COMPONENTS = frozenset([
    "tokenizer", "chat_template", "prompt_policy",
    "tool_schema", "decode", "guards",
])


def compat_check(
    a: ReleaseTuple,
    b: ReleaseTuple,
    allowed_diffs: frozenset[str] = frozenset(),
) -> CompatResult:
    """Compare interface component hashes between two ReleaseTuples.

    Passes when all interface components match except those named in
    *allowed_diffs* (e.g., ``{'adapter'}`` for train-vs-base compare).

    Returns :class:`CompatResult(passed, mismatches)`. Use
    ``require_compat(a, b)`` for the exception-raising variant.
    """
    def _tuple_hash(tc):   
        if tc is None:
            return None
        if isinstance(tc, dict):
            return tc.get("hash") or tc.get("hash_val")
        return tc.hash_val if hasattr(tc, "hash_val") else None

    mismatches = []
    for comp in sorted(_INTERFACE_COMPONENTS):
        if comp in allowed_diffs:
            continue
        h_a = _tuple_hash(getattr(a, comp))
        h_b = _tuple_hash(getattr(b, comp))
        if h_a != h_b:
            mismatches.append(comp)

    return CompatResult(passed=len(mismatches) == 0, mismatches=mismatches)


def require_compat(
    a: ReleaseTuple,
    b: ReleaseTuple,
    allowed_diffs: frozenset[str] = frozenset(),
) -> None:
    result = compat_check(a, b, allowed_diffs=allowed_diffs)
    if not result.passed:
        raise CompatMismatch(
            f"Interface drift on: {', '.join(result.mismatches)}",
            reason="compat_mismatch",
            details={"mismatches": result.mismatches},
        )


# ---------------------------------------------------------------------------
# Smoke then scale
# ---------------------------------------------------------------------------


def smoke_then_scale(
    store: Any,
    objective_id: str,
    scale_spec: dict[str, Any],
) -> None:
    """Deny train_scale unless smoke prerequisites are met.

    Implemented checks:
    - Linked smoke run exists with status completed
    - Admission report hash matches (or explicit declared-delta artifact present)
    - Memory envelope within tolerance

    Deferred (wired up in Phases 8+11 integration):
    - Smoke Decision permits scale (stubbed as ``SmokeGateUnsatisfied``)

    Raises ``SmokeGateUnsatisfied`` for each unmet condition.
    """
    smoke_run_id = scale_spec.get("smoke_run_id")

    # -- Check linked smoke run exists and is completed -------------------------
    smoke_run = store.get_run(smoke_run_id)
    if smoke_run is None:
        raise SmokeGateUnsatisfied(
            f"No linked smoke run {smoke_run_id!r} found",
            reason="smoke_run_not_found",
            details={"smoke_run_id": smoke_run_id},
        )
    if smoke_run.status != RunStatus.completed:
        raise SmokeGateUnsatisfied(
            f"Smoke run {smoke_run_id} status is {smoke_run.status.value}, need completed",
            reason="smoke_not_completed",
            details={"smoke_run_id": smoke_run_id, "status": smoke_run.status.value},
        )

    # -- Check admission report hash compatibility ------------------------------
    spec_admission_hash = scale_spec.get("admission_report_hash")
    if spec_admission_hash:
        latest_passing = store.latest_passing_admission(objective_id)
        if latest_passing is None:
            raise SmokeGateUnsatisfied(
                "No passing admission report for objective",
                reason="no_passing_admission",
                details={"objective_id": objective_id},
            )
        # The spec's admission hash must match the latest passing one
        latest_hash = latest_passing.content_hash() if hasattr(latest_passing, "content_hash") else None
        if spec_admission_hash != scale_spec.get("admission_report_hash"):
            raise SmokeGateUnsatisfied(
                f"Admission report hash mismatch: spec={spec_admission_hash}",
                reason="admission_hash_mismatch",
                details={"spec_hash": spec_admission_hash},
            )
        elif latest_hash and spec_admission_hash != latest_hash:
            raise SmokeGateUnsatisfied(
                f"Admission report hash mismatch: spec={spec_admission_hash}, latest_passing={latest_hash}",
                reason="admission_hash_mismatch",
                details={"spec_hash": spec_admission_hash, "latest_hash": latest_hash},
            )

    # -- Check memory envelope within tolerance ---------------------------------
    mem_envelope = scale_spec.get("memory_envelope", {})
    if mem_envelope:
        peak_vram = mem_envelope.get("peak_vram_mb")
        available_vram = mem_envelope.get("available_vram_mb")
        if peak_vram is not None and available_vram is not None:
            tolerance_pct = mem_envelope.get("tolerance_percent", 20)
            max_allowed = available_vram * (1 + tolerance_pct / 100)
            if peak_vram > max_allowed:
                raise SmokeGateUnsatisfied(
                    f"Memory envelope exceeded: peak {peak_vram} MB > "
                    f"{max_allowed:.0f} MB ({tolerance_pct}% tolerance)",
                    reason="memory_envelope_exceeded",
                    details={"peak_vram": peak_vram, "max_allowed": max_allowed},
                )

    # -- Deferred: Decision permits scale ---
    # Wire up when Phase 8 decide module exists. Stub raises to prevent silent pass.
    raise SmokeGateUnsatisfied(
        "Decision-permits-scale check deferred until Phase 8/11 integration",
        reason="decision_not_yet_available",
        details={"objective_id": objective_id, "smoke_run_id": smoke_run_id},
    )


# ---------------------------------------------------------------------------
# Suite pin required
# ---------------------------------------------------------------------------


def suite_pin_required(store: Any, objective_id: str) -> None:
    """Deny generate/admit-for-train when sealed suite hash is not frozen.

    Raises ``SuiteNotPinned``.
    """
    from .objective import load_objective

    obj = load_objective(store, objective_id)
    suites = obj.suites or {}
    seal_suite = suites.get("seal") or {}
    seal_hash = seal_suite.get("hash")

    if not seal_hash:
        raise SuiteNotPinned(
            f"Sealed suite not pinned for objective {objective_id}",
            reason="suite_not_pinned",
            details={"objective_id": objective_id},
        )
