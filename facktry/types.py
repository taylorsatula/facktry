"""Core Facktry types.

Typed, serializable, hashable dataclasses representing the ADR §5 domain model.
Types are inert data + hashing only — no lint, freeze, aggregation, or governance logic here.

Every type supports:
- ``to_dict()`` → canonical dict (keys exactly match JSON representation)
- ``from_dict(d)`` → typed instance (raises :class:`SerdeError` on bad input)
- ``==`` comparison inherited from dataclass (structural equality).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .errors import SerdeError

# ── Enums ────────────────────────────────────────────────────────────────────

class RunStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    guarded = "guarded"
    blocked = "blocked"


class Severity(str, Enum):
    hard = "hard"
    soft = "soft"
    human = "human"
    diagnostic = "diagnostic"


class Channel(str, Enum):
    raw = "raw"
    guarded = "guarded"
    na = "n/a"


class DecisionAction(str, Enum):
    promote = "promote"
    hold = "hold"
    correct = "correct"
    abort = "abort"
    ask_human = "ask_human"


class InterventionClass(str, Enum):
    data = "data"
    mixture = "mixture"
    rubric = "rubric"
    hparam = "hparam"
    interface = "interface"
    stop = "stop"


class SourceClass(str, Enum):
    public = "public"
    fictional = "fictional"
    private_redacted = "private_redacted"
    private_raw = "private_raw"
    synthetic = "synthetic"
    replay = "replay"
    preference = "preference"
    train = "train"
    dev = "dev"
    seal = "seal"
    report = "report"
    checkpoint = "checkpoint"
    tuple_ = "tuple"
    decision = "decision"
    scorecard = "scorecard"
    admission = "admission"
    mission_brief = "mission_brief"
    recipe = "recipe"
    recipe_stack = "recipe_stack"
    recipe_evidence = "recipe_evidence"
    log = "log"


class DefectStatus(str, Enum):
    open = "open"
    closed = "closed"
    wont_fix = "wont_fix"


class InboxStatus(str, Enum):
    pending = "pending"
    answered = "answered"
    expired = "expired"


class Split(str, Enum):
    dev = "dev"
    seal = "seal"

# ── Helpers ──────────────────────────────────────────────────────────────────


def _enum(enum_type, value):  # noqa: ANN
    """Parse a string into *enum_type*, raising :class:`SerdeError` on failure."""
    try:
        return enum_type(value)
    except ValueError as exc:
        raise SerdeError(f"Invalid {enum_type.__name__}: {value!r}") from exc


def _required(d, key, name=None):  # noqa: ANN
    """Extract a required key from *d*, raising :class:`SerdeError` if absent."""
    try:
        return d[key]
    except KeyError:
        raise SerdeError(f"Missing required field: {key}" if name is None else f"Missing required field in {name}: {key}")


# ── Types ────────────────────────────────────────────────────────────────────

@dataclass(eq=True)
class Gate:
    """A gate definition or evaluation result."""
    name: str
    severity: Severity
    comparator: str
    threshold: float | int
    suite_ref: str | None
    checker_ref: str | None
    channel: Channel
    observed: float | int | None
    passed: bool | None
    evidence: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "severity": self.severity.value,
            "comparator": self.comparator,
            "threshold": self.threshold,
            "suite_ref": self.suite_ref,
            "checker_ref": self.checker_ref,
            "channel": self.channel.value,
            "observed": self.observed,
            "passed": self.passed,
            "evidence": self.evidence,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Gate:
        return cls(
            name=_required(d, "name", "Gate"),
            severity=_enum(Severity, _required(d, "severity", "Gate")),
            comparator=_required(d, "comparator", "Gate"),
            threshold=_required(d, "threshold", "Gate"),
            suite_ref=d.get("suite_ref"),
            checker_ref=d.get("checker_ref"),
            channel=_enum(Channel, _required(d, "channel", "Gate")),
            observed=d.get("observed"),
            passed=d.get("passed"),
            evidence=_required(d, "evidence", "Gate"),
        )


# GateResult has the same schema as Gate (ADR §5 — identical fields represent
# both definition and evaluation result).
@dataclass(eq=True)
class GateResult(Gate):
    """Gate evaluation result; same schema as Gate."""
    pass


@dataclass(eq=True)
class MissionBrief:
    id: str
    version: int
    brief_hash: str
    parent_version: int | None
    operator_session_id: str | None
    raw_mission: str
    dossier: dict[str, Any]
    hard_gate_approvals: list[dict[str, Any]]
    research_notes: list[dict[str, Any]]
    recipe_considerations: list[dict[str, Any]]
    objective_ref: str | None
    created_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "brief_hash": self.brief_hash,
            "parent_version": self.parent_version,
            "operator_session_id": self.operator_session_id,
            "raw_mission": self.raw_mission,
            "dossier": self.dossier,
            "hard_gate_approvals": self.hard_gate_approvals,
            "research_notes": self.research_notes,
            "recipe_considerations": self.recipe_considerations,
            "objective_ref": self.objective_ref,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MissionBrief:
        return cls(
            id=_required(d, "id", "MissionBrief"),
            version=_required(d, "version", "MissionBrief"),
            brief_hash=_required(d, "brief_hash", "MissionBrief"),
            parent_version=d.get("parent_version"),
            operator_session_id=d.get("operator_session_id"),
            raw_mission=_required(d, "raw_mission", "MissionBrief"),
            dossier=_required(d, "dossier", "MissionBrief"),
            hard_gate_approvals=_required(d, "hard_gate_approvals", "MissionBrief"),
            research_notes=_required(d, "research_notes", "MissionBrief"),
            recipe_considerations=_required(d, "recipe_considerations", "MissionBrief"),
            objective_ref=d.get("objective_ref"),
            created_at=d.get("created_at"),
        )


@dataclass(eq=True)
class Objective:
    id: str
    mission_brief: dict[str, Any]
    intent: str
    deliverable: str
    gates: list[dict[str, Any]]
    constraints: dict[str, Any] | None
    budget: dict[str, Any] | None
    baselines: dict[str, Any] | None
    suites: dict[str, Any] | None
    dependence_keys: list[str] | None
    mixture: dict[str, Any] | None
    policy: dict[str, Any] | None
    interface: dict[str, Any] | None
    recipe_policy: dict[str, Any] | None
    supersedes: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mission_brief": self.mission_brief,
            "intent": self.intent,
            "deliverable": self.deliverable,
            "gates": self.gates,
            "constraints": self.constraints,
            "budget": self.budget,
            "baselines": self.baselines,
            "suites": self.suites,
            "dependence_keys": self.dependence_keys,
            "mixture": self.mixture,
            "policy": self.policy,
            "interface": self.interface,
            "recipe_policy": self.recipe_policy,
            "supersedes": self.supersedes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Objective:
        return cls(
            id=_required(d, "id", "Objective"),
            mission_brief=_required(d, "mission_brief", "Objective"),
            intent=_required(d, "intent", "Objective"),
            deliverable=_required(d, "deliverable", "Objective"),
            gates=_required(d, "gates", "Objective"),
            constraints=d.get("constraints"),
            budget=d.get("budget"),
            baselines=d.get("baselines"),
            suites=d.get("suites"),
            dependence_keys=d.get("dependence_keys"),
            mixture=d.get("mixture"),
            policy=d.get("policy"),
            interface=d.get("interface"),
            recipe_policy=d.get("recipe_policy"),
            supersedes=d.get("supersedes"),
        )


@dataclass(eq=True)
class ReleaseTuple:
    base_model: dict[str, Any] | None
    adapter: dict[str, Any] | None
    tokenizer: dict[str, Any] | None
    chat_template: str
    prompt_policy: dict[str, Any]
    tool_schema: dict[str, Any]
    decode: dict[str, Any]
    guards: dict[str, Any]
    recipe_stack: dict[str, Any]
    tuple_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_model": self.base_model,
            "adapter": self.adapter,
            "tokenizer": self.tokenizer,
            "chat_template": self.chat_template,
            "prompt_policy": self.prompt_policy,
            "tool_schema": self.tool_schema,
            "decode": self.decode,
            "guards": self.guards,
            "recipe_stack": self.recipe_stack,
            "tuple_hash": self.tuple_hash,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ReleaseTuple:
        return cls(
            base_model=d.get("base_model"),
            adapter=d.get("adapter"),
            tokenizer=_required(d, "tokenizer", "ReleaseTuple"),
            chat_template=_required(d, "chat_template", "ReleaseTuple"),
            prompt_policy=_required(d, "prompt_policy", "ReleaseTuple"),
            tool_schema=_required(d, "tool_schema", "ReleaseTuple"),
            decode=_required(d, "decode", "ReleaseTuple"),
            guards=_required(d, "guards", "ReleaseTuple"),
            recipe_stack=_required(d, "recipe_stack", "ReleaseTuple"),
            tuple_hash=_required(d, "tuple_hash", "ReleaseTuple"),
        )

    def compute_tuple_hash(self) -> str:
        """Hash the component hashes into a single content address."""
        from .hashing import hash_obj

        def _h(field):
            v = getattr(self, field)
            if v is None:
                return None
            if isinstance(v, str):
                return v
            return v.get("hash")

        components = {
            "base_model": _h("base_model"),
            "adapter": _h("adapter"),
            "tokenizer": _h("tokenizer"),
            "chat_template": _h("chat_template"),
            "prompt_policy": _h("prompt_policy"),
            "tool_schema": _h("tool_schema"),
            "decode": _h("decode"),
            "guards": _h("guards"),
            "recipe_stack": _h("recipe_stack"),
        }
        return hash_obj(components)


@dataclass(eq=True)
class Run:
    run_id: str
    objective_id: str
    mission_brief: dict[str, Any]
    stage: str
    status: RunStatus
    parents: list[dict[str, Any]]
    spec: dict[str, Any]
    code_hash: str
    env: dict[str, Any]
    hardware: dict[str, Any]
    inputs: list[Any]
    outputs: list[Any]
    guard_report: dict[str, Any] | None
    metrics_path: str
    recipe_stack: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "objective_id": self.objective_id,
            "mission_brief": self.mission_brief,
            "stage": self.stage,
            "status": self.status.value,
            "parents": self.parents,
            "spec": self.spec,
            "code_hash": self.code_hash,
            "env": self.env,
            "hardware": self.hardware,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "guard_report": self.guard_report,
            "metrics_path": self.metrics_path,
            "recipe_stack": self.recipe_stack,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Run:
        return cls(
            run_id=_required(d, "run_id", "Run"),
            objective_id=_required(d, "objective_id", "Run"),
            mission_brief=_required(d, "mission_brief", "Run"),
            stage=_required(d, "stage", "Run"),
            status=_enum(RunStatus, _required(d, "status", "Run")),
            parents=_required(d, "parents", "Run"),
            spec=_required(d, "spec", "Run"),
            code_hash=_required(d, "code_hash", "Run"),
            env=_required(d, "env", "Run"),
            hardware=_required(d, "hardware", "Run"),
            inputs=_required(d, "inputs", "Run"),
            outputs=_required(d, "outputs", "Run"),
            guard_report=d.get("guard_report"),
            metrics_path=_required(d, "metrics_path", "Run"),
            recipe_stack=d.get("recipe_stack"),
        )


@dataclass(eq=True)
class Artifact:
    path: str
    sha256: str
    role: str
    producer_run_id: str
    created_at: str
    media_type: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "role": self.role,
            "producer_run_id": self.producer_run_id,
            "created_at": self.created_at,
            "media_type": self.media_type,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Artifact:
        return cls(
            path=_required(d, "path", "Artifact"),
            sha256=_required(d, "sha256", "Artifact"),
            role=_required(d, "role", "Artifact"),
            producer_run_id=_required(d, "producer_run_id", "Artifact"),
            created_at=_required(d, "created_at", "Artifact"),
            media_type=d.get("media_type"),
        )


@dataclass(eq=True)
class Scorecard:
    suite_hash: str
    seeds: list[int]
    decode_hash: str
    subject_tuple_hash: str
    recipe_stack_hash: str
    dimensions: dict[str, float]
    raw: dict[str, float]
    guarded: dict[str, float]
    findings: list[dict[str, Any]]
    slices: dict[str, Any]
    resources: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite_hash": self.suite_hash,
            "seeds": self.seeds,
            "decode_hash": self.decode_hash,
            "subject_tuple_hash": self.subject_tuple_hash,
            "recipe_stack_hash": self.recipe_stack_hash,
            "dimensions": self.dimensions,
            "raw": self.raw,
            "guarded": self.guarded,
            "findings": self.findings,
            "slices": self.slices,
            "resources": self.resources,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Scorecard:
        return cls(
            suite_hash=_required(d, "suite_hash", "Scorecard"),
            seeds=_required(d, "seeds", "Scorecard"),
            decode_hash=_required(d, "decode_hash", "Scorecard"),
            subject_tuple_hash=_required(d, "subject_tuple_hash", "Scorecard"),
            recipe_stack_hash=_required(d, "recipe_stack_hash", "Scorecard"),
            dimensions=_required(d, "dimensions", "Scorecard"),
            raw=_required(d, "raw", "Scorecard"),
            guarded=_required(d, "guarded", "Scorecard"),
            findings=_required(d, "findings", "Scorecard"),
            slices=_required(d, "slices", "Scorecard"),
            resources=_required(d, "resources", "Scorecard"),
        )


@dataclass(eq=True)
class Decision:
    action: DecisionAction
    objective_id: str
    mission_brief_ref: dict[str, Any]
    subject: dict[str, Any]
    gate_results: list[dict[str, Any]]
    intervention: dict[str, Any] | None
    human_requests: list[dict[str, Any]]
    dossier_ref: str
    created_at: str
    recipe_stack_ref: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "objective_id": self.objective_id,
            "mission_brief_ref": self.mission_brief_ref,
            "subject": self.subject,
            "gate_results": self.gate_results,
            "intervention": self.intervention,
            "human_requests": self.human_requests,
            "dossier_ref": self.dossier_ref,
            "created_at": self.created_at,
            "recipe_stack_ref": self.recipe_stack_ref,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Decision:
        return cls(
            action=_enum(DecisionAction, _required(d, "action", "Decision")),
            objective_id=_required(d, "objective_id", "Decision"),
            mission_brief_ref=_required(d, "mission_brief_ref", "Decision"),
            subject=_required(d, "subject", "Decision"),
            gate_results=_required(d, "gate_results", "Decision"),
            intervention=d.get("intervention"),
            human_requests=_required(d, "human_requests", "Decision"),
            dossier_ref=_required(d, "dossier_ref", "Decision"),
            created_at=_required(d, "created_at", "Decision"),
            recipe_stack_ref=d.get("recipe_stack_ref"),
        )


@dataclass(eq=True)
class Defect:
    id: str
    taxonomy: str
    evidence: list[str]
    first_run_id: str
    last_run_id: str
    interventions: list[dict[str, Any]]
    status: DefectStatus

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "taxonomy": self.taxonomy,
            "evidence": self.evidence,
            "first_run_id": self.first_run_id,
            "last_run_id": self.last_run_id,
            "interventions": self.interventions,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Defect:
        return cls(
            id=_required(d, "id", "Defect"),
            taxonomy=_required(d, "taxonomy", "Defect"),
            evidence=_required(d, "evidence", "Defect"),
            first_run_id=_required(d, "first_run_id", "Defect"),
            last_run_id=_required(d, "last_run_id", "Defect"),
            interventions=_required(d, "interventions", "Defect"),
            status=_enum(DefectStatus, _required(d, "status", "Defect")),
        )


@dataclass(eq=True)
class Policy:
    capabilities: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {"capabilities": self.capabilities}

    @classmethod
    def from_dict(cls, d: dict) -> Policy:
        return cls(capabilities=_required(d, "capabilities", "Policy"))


@dataclass(eq=True)
class BudgetLedger:
    wall_time: float | int
    gpu_hours: float | int
    judge_tokens: int
    smoke_runs: int
    scale_runs: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "wall_time": self.wall_time,
            "gpu_hours": self.gpu_hours,
            "judge_tokens": self.judge_tokens,
            "smoke_runs": self.smoke_runs,
            "scale_runs": self.scale_runs,
        }

    @classmethod
    def from_dict(cls, d: dict) -> BudgetLedger:
        return cls(
            wall_time=_required(d, "wall_time", "BudgetLedger"),
            gpu_hours=_required(d, "gpu_hours", "BudgetLedger"),
            judge_tokens=_required(d, "judge_tokens", "BudgetLedger"),
            smoke_runs=_required(d, "smoke_runs", "BudgetLedger"),
            scale_runs=_required(d, "scale_runs", "BudgetLedger"),
        )


@dataclass(eq=True)
class TrainCard:
    objective_id: str
    run_id: str
    mission_brief: dict[str, Any]
    parent_tuple_hash: str
    admission_report_hash: str
    mixture_counts: dict[str, int]
    interface_hashes: dict[str, str]
    effective_examples: int
    optimizer_steps: int
    token_counts: dict[str, int]
    repeated_example_exposure: dict[str, int]
    target_length: dict[str, float | int]
    lr_schedule: dict[str, Any]
    seed: int
    peak_vram: int
    wall_time: float | int
    teacher_id: str
    reference_id: str | None
    best_checkpoint_ref: dict[str, Any] | None
    recipe_stack_hash: str
    recipe_adaptations: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "run_id": self.run_id,
            "mission_brief": self.mission_brief,
            "parent_tuple_hash": self.parent_tuple_hash,
            "admission_report_hash": self.admission_report_hash,
            "mixture_counts": self.mixture_counts,
            "interface_hashes": self.interface_hashes,
            "effective_examples": self.effective_examples,
            "optimizer_steps": self.optimizer_steps,
            "token_counts": self.token_counts,
            "repeated_example_exposure": self.repeated_example_exposure,
            "target_length": self.target_length,
            "lr_schedule": self.lr_schedule,
            "seed": self.seed,
            "peak_vram": self.peak_vram,
            "wall_time": self.wall_time,
            "teacher_id": self.teacher_id,
            "reference_id": self.reference_id,
            "best_checkpoint_ref": self.best_checkpoint_ref,
            "recipe_stack_hash": self.recipe_stack_hash,
            "recipe_adaptations": self.recipe_adaptations,
        }

    @classmethod
    def from_dict(cls, d: dict) -> TrainCard:
        return cls(
            objective_id=_required(d, "objective_id", "TrainCard"),
            run_id=_required(d, "run_id", "TrainCard"),
            mission_brief=_required(d, "mission_brief", "TrainCard"),
            parent_tuple_hash=_required(d, "parent_tuple_hash", "TrainCard"),
            admission_report_hash=_required(d, "admission_report_hash", "TrainCard"),
            mixture_counts=_required(d, "mixture_counts", "TrainCard"),
            interface_hashes=_required(d, "interface_hashes", "TrainCard"),
            effective_examples=_required(d, "effective_examples", "TrainCard"),
            optimizer_steps=_required(d, "optimizer_steps", "TrainCard"),
            token_counts=_required(d, "token_counts", "TrainCard"),
            repeated_example_exposure=_required(d, "repeated_example_exposure", "TrainCard"),
            target_length=_required(d, "target_length", "TrainCard"),
            lr_schedule=_required(d, "lr_schedule", "TrainCard"),
            seed=_required(d, "seed", "TrainCard"),
            peak_vram=_required(d, "peak_vram", "TrainCard"),
            wall_time=_required(d, "wall_time", "TrainCard"),
            teacher_id=_required(d, "teacher_id", "TrainCard"),
            reference_id=d.get("reference_id"),
            best_checkpoint_ref=d.get("best_checkpoint_ref"),
            recipe_stack_hash=_required(d, "recipe_stack_hash", "TrainCard"),
            recipe_adaptations=_required(d, "recipe_adaptations", "TrainCard"),
        )


@dataclass(eq=True)
class MixtureSpec:
    dimensions: list[str]
    floors: dict[str, int]
    caps: dict[str, int]
    quotas: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimensions": self.dimensions,
            "floors": self.floors,
            "caps": self.caps,
            "quotas": self.quotas,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MixtureSpec:
        return cls(
            dimensions=_required(d, "dimensions", "MixtureSpec"),
            floors=_required(d, "floors", "MixtureSpec"),
            caps=_required(d, "caps", "MixtureSpec"),
            quotas=_required(d, "quotas", "MixtureSpec"),
        )


# TargetShape shares the identical schema with MixtureSpec per ADR §5.x.
TargetShape = MixtureSpec


@dataclass(eq=True)
class AdmissionReport:
    input_artifacts: list[str]
    keep_count: int
    reject_count: int
    reject_reasons: dict[str, int]
    overlap_matrix: dict[str, int | float]
    near_dupes: dict[str, float]
    template_families: dict[str, int]
    mixture_deltas: dict[str, Any]
    teacher_id: str
    transformation_policy_id: str
    seeds: list[int]
    suite_hash: str
    passed: bool
    gate_results: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_artifacts": self.input_artifacts,
            "keep_count": self.keep_count,
            "reject_count": self.reject_count,
            "reject_reasons": self.reject_reasons,
            "overlap_matrix": self.overlap_matrix,
            "near_dupes": self.near_dupes,
            "template_families": self.template_families,
            "mixture_deltas": self.mixture_deltas,
            "teacher_id": self.teacher_id,
            "transformation_policy_id": self.transformation_policy_id,
            "seeds": self.seeds,
            "suite_hash": self.suite_hash,
            "passed": self.passed,
            "gate_results": self.gate_results,
        }

    @classmethod
    def from_dict(cls, d: dict) -> AdmissionReport:
        return cls(
            input_artifacts=_required(d, "input_artifacts", "AdmissionReport"),
            keep_count=_required(d, "keep_count", "AdmissionReport"),
            reject_count=_required(d, "reject_count", "AdmissionReport"),
            reject_reasons=_required(d, "reject_reasons", "AdmissionReport"),
            overlap_matrix=_required(d, "overlap_matrix", "AdmissionReport"),
            near_dupes=_required(d, "near_dupes", "AdmissionReport"),
            template_families=_required(d, "template_families", "AdmissionReport"),
            mixture_deltas=_required(d, "mixture_deltas", "AdmissionReport"),
            teacher_id=_required(d, "teacher_id", "AdmissionReport"),
            transformation_policy_id=_required(d, "transformation_policy_id", "AdmissionReport"),
            seeds=_required(d, "seeds", "AdmissionReport"),
            suite_hash=_required(d, "suite_hash", "AdmissionReport"),
            passed=_required(d, "passed", "AdmissionReport"),
            gate_results=_required(d, "gate_results", "AdmissionReport"),
        )


@dataclass(eq=True)
class HumanInboxItem:
    id: str
    objective_id: str
    gate_name: str
    payload_ref: str
    response_schema: dict[str, Any]
    created_at: str
    age: int | float | None
    status: InboxStatus

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "objective_id": self.objective_id,
            "gate_name": self.gate_name,
            "payload_ref": self.payload_ref,
            "response_schema": self.response_schema,
            "created_at": self.created_at,
            "age": self.age,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, d: dict) -> HumanInboxItem:
        return cls(
            id=_required(d, "id", "HumanInboxItem"),
            objective_id=_required(d, "objective_id", "HumanInboxItem"),
            gate_name=_required(d, "gate_name", "HumanInboxItem"),
            payload_ref=_required(d, "payload_ref", "HumanInboxItem"),
            response_schema=_required(d, "response_schema", "HumanInboxItem"),
            created_at=_required(d, "created_at", "HumanInboxItem"),
            age=d.get("age"),
            status=_enum(InboxStatus, _required(d, "status", "HumanInboxItem")),
        )


@dataclass(eq=True)
class Recipe:
    id: str
    version: str
    title: str
    status: str
    effects: list[dict[str, Any]]
    scope: dict[str, Any]
    requires: list[Any]
    conflicts: list[Any]
    mechanism: str
    ingredients: dict[str, Any]
    procedure: list[str]
    tradeoffs: list[str]
    failure_modes: list[str]
    evidence: list[dict[str, Any]]
    tested_uses: list[dict[str, Any]]
    interactions: dict[str, Any]
    provenance: dict[str, Any]
    instruction_hash: str
    notes_head: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "title": self.title,
            "status": self.status,
            "effects": self.effects,
            "scope": self.scope,
            "requires": self.requires,
            "conflicts": self.conflicts,
            "mechanism": self.mechanism,
            "ingredients": self.ingredients,
            "procedure": self.procedure,
            "tradeoffs": self.tradeoffs,
            "failure_modes": self.failure_modes,
            "evidence": self.evidence,
            "tested_uses": self.tested_uses,
            "interactions": self.interactions,
            "provenance": self.provenance,
            "instruction_hash": self.instruction_hash,
            "notes_head": self.notes_head,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Recipe:
        return cls(
            id=_required(d, "id", "Recipe"),
            version=_required(d, "version", "Recipe"),
            title=_required(d, "title", "Recipe"),
            status=_required(d, "status", "Recipe"),
            effects=_required(d, "effects", "Recipe"),
            scope=_required(d, "scope", "Recipe"),
            requires=_required(d, "requires", "Recipe"),
            conflicts=_required(d, "conflicts", "Recipe"),
            mechanism=_required(d, "mechanism", "Recipe"),
            ingredients=_required(d, "ingredients", "Recipe"),
            procedure=_required(d, "procedure", "Recipe"),
            tradeoffs=_required(d, "tradeoffs", "Recipe"),
            failure_modes=_required(d, "failure_modes", "Recipe"),
            evidence=_required(d, "evidence", "Recipe"),
            tested_uses=_required(d, "tested_uses", "Recipe"),
            interactions=_required(d, "interactions", "Recipe"),
            provenance=_required(d, "provenance", "Recipe"),
            instruction_hash=_required(d, "instruction_hash", "Recipe"),
            notes_head=d.get("notes_head"),
        )


@dataclass(eq=True)
class RecipeStack:
    id: str
    recipes: list[dict[str, Any]]
    overrides: dict[str, Any]
    allocation: dict[str, float]
    conflict_decisions: list[Any]
    validation_plan: dict[str, Any]
    stack_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "recipes": self.recipes,
            "overrides": self.overrides,
            "allocation": self.allocation,
            "conflict_decisions": self.conflict_decisions,
            "validation_plan": self.validation_plan,
            "stack_hash": self.stack_hash,
        }

    @classmethod
    def from_dict(cls, d: dict) -> RecipeStack:
        return cls(
            id=_required(d, "id", "RecipeStack"),
            recipes=_required(d, "recipes", "RecipeStack"),
            overrides=_required(d, "overrides", "RecipeStack"),
            allocation=_required(d, "allocation", "RecipeStack"),
            conflict_decisions=_required(d, "conflict_decisions", "RecipeStack"),
            validation_plan=_required(d, "validation_plan", "RecipeStack"),
            stack_hash=_required(d, "stack_hash", "RecipeStack"),
        )
