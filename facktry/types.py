"""Core Facktry types.

Typed, self-validating Pydantic v2 models representing the ADR §5 domain model.
Types are inert data + hashing only — no lint, freeze, aggregation, or governance logic here.

Every type supports:
- ``to_dict()`` → canonical dict (keys exactly match JSON representation)
- ``from_dict(d)`` → typed instance (raises :class:`SerdeError` on bad input)
- ``content_hash()`` → SHA-256 hex over canonical JSON of payload (excluding derived hashes)
- ``==`` comparison inherited from Pydantic (structural equality).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field

# ── Errors ───────────────────────────────────────────────────────────────────

from .errors import SerdeError

# ── Enums ────────────────────────────────────────────────────────────────────


class RunStatus(StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    guarded = "guarded"
    blocked = "blocked"


class Severity(StrEnum):
    hard = "hard"
    soft = "soft"
    human = "human"
    diagnostic = "diagnostic"


class Channel(StrEnum):
    raw = "raw"
    guarded = "guarded"
    na = "n/a"


class DecisionAction(StrEnum):
    promote = "promote"
    hold = "hold"
    correct = "correct"
    abort = "abort"
    ask_human = "ask_human"


class InterventionClass(StrEnum):
    data = "data"
    mixture = "mixture"
    rubric = "rubric"
    hparam = "hparam"
    interface = "interface"
    stop = "stop"


class SourceClass(StrEnum):
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
    tuple_class = "tuple"
    decision = "decision"
    scorecard = "scorecard"
    admission = "admission"
    mission_brief = "mission_brief"
    recipe = "recipe"
    recipe_stack = "recipe_stack"
    recipe_evidence = "recipe_evidence"
    log = "log"


class DefectStatus(StrEnum):
    open = "open"
    closed = "closed"
    wont_fix = "wont_fix"


class InboxStatus(StrEnum):
    pending = "pending"
    answered = "answered"
    expired = "expired"


class Split(StrEnum):
    dev = "dev"
    seal = "seal"

# ── Base ─────────────────────────────────────────────────────────────────────


class HashableBase(BaseModel):
    """Base for all facktry types that participate in provenance or decisions."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=False,
        coerce_numbers_to_str=False,
    )

    # Derived/hash-only fields excluded from content_hash so they can be recomputed.
    _HASH_FIELD_NAMES: frozenset[str] = frozenset()

    def to_dict(self) -> dict[str, Any]:
        """Canonical dict matching JSON serialization shape."""
        return self.model_dump(mode="json", by_alias=True)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Self:
        """Validate and construct an instance; raises SerdeError on failure."""
        try:
            return cls.model_validate(d)
        except Exception as exc:
            raise SerdeError(str(exc)) from exc

    @property
    def store_dict(self) -> dict[str, Any]:
        """Alias for to_dict — used by store layer."""
        return self.to_dict()

    def content_hash(self) -> str:
        """SHA-256 hex over canonical JSON, excluding derived hash fields."""
        from .hashing import hash_obj

        exclude_fields = {f for f in type(self).model_fields.keys()
                          if f in self._HASH_FIELD_NAMES}
        return hash_obj(self.model_dump(mode="json", exclude=exclude_fields))

# ── Value objects ────────────────────────────────────────────────────────────


class TupleComponent(HashableBase):  # noqa: PYI043
    """A named, hashed component of a ReleaseTuple."""

    ref: str
    hash_val: str = Field(alias="hash")

    model_config = ConfigDict(frozen=True)


class BriefRef(HashableBase):  # noqa: PYI043
    """Immutable reference to a saved MissionBrief version."""

    id: str
    version: int
    brief_hash: str

    model_config = ConfigDict(frozen=True)

# ── Core types (ADR §5) ─────────────────────────────────────────────────────


class Gate(HashableBase):
    """A gate definition or evaluation result (ADR §5.5)."""

    name: str
    severity: Severity
    comparator: str
    threshold: float | int
    suite_ref: str | None = None
    checker_ref: str | None = None
    channel: Channel
    observed: float | int | None = None
    passed: bool | None = None
    evidence: list[str]


class GateResult(Gate):
    """Gate evaluation result; same schema as Gate (ADR §5.5)."""
    pass


class MissionBrief(HashableBase):  # noqa: PYI043
    """Saved, versioned intent dossier (ADR §5.0). Immutable after save."""

    model_config = ConfigDict(frozen=True)

    id: str
    version: int
    brief_hash: str
    parent_version: int | None = None
    operator_session_id: str | None = None
    raw_mission: str
    dossier: dict[str, Any]
    hard_gate_approvals: list[dict[str, Any]]
    research_notes: list[dict[str, Any]]
    recipe_considerations: list[dict[str, Any]]
    objective_ref: str | None = None
    created_at: str | None = None

    _HASH_FIELD_NAMES = frozenset({"brief_hash"})

    def supersede(self, **overrides: Any) -> MissionBrief:
        """Create a new version referencing this one via parent_version."""
        new_data = self.model_dump(mode="json")
        new_data.update(overrides)
        new_data["version"] = self.version + 1
        new_data["parent_version"] = self.version
        return self.__class__.from_dict(new_data)


class Objective(HashableBase):  # noqa: PYI043
    """Frozen mission contract (ADR §5.1). Immutable after freeze."""

    model_config = ConfigDict(frozen=True)

    id: str
    mission_brief: BriefRef
    intent: str
    deliverable: str
    gates: list[dict[str, Any]]
    constraints: dict[str, Any] | None = None
    budget: dict[str, Any] | None = None
    baselines: dict[str, Any] | None = None
    suites: dict[str, Any] | None = None
    dependence_keys: list[str] | None = None
    mixture: dict[str, Any] | None = None
    policy: dict[str, Any] | None = None
    interface: dict[str, Any] | None = None
    recipe_policy: dict[str, Any] | None = None
    supersedes: str | None = None


class ReleaseTuple(HashableBase):  # noqa: PYI043
    """The only shippable model identity (ADR §5.2)."""

    model_config = ConfigDict(frozen=True)

    base_model: TupleComponent | None = None
    adapter: TupleComponent | None = None
    tokenizer: TupleComponent
    chat_template: TupleComponent
    prompt_policy: TupleComponent
    tool_schema: TupleComponent
    decode: TupleComponent
    guards: TupleComponent
    recipe_stack: TupleComponent | None = None
    tuple_hash: str

    _HASH_FIELD_NAMES = frozenset({"tuple_hash"})

    @staticmethod
    def _extract_hash(field: Any) -> str | None:
        if field is None:
            return None
        if isinstance(field, str):
            return field
        try:
            return field.hash_val
        except AttributeError:
            return field.get("hash") if isinstance(field, dict) else None

    def compute_tuple_hash(self) -> str:
        """Hash the component hashes into a single content address."""
        from .hashing import hash_obj

        components = {
            "base_model": self._extract_hash(self.base_model),
            "adapter": self._extract_hash(self.adapter),
            "tokenizer": self._extract_hash(self.tokenizer),
            "chat_template": self._extract_hash(self.chat_template),
            "prompt_policy": self._extract_hash(self.prompt_policy),
            "tool_schema": self._extract_hash(self.tool_schema),
            "decode": self._extract_hash(self.decode),
            "guards": self._extract_hash(self.guards),
            "recipe_stack": self._extract_hash(self.recipe_stack),
        }
        return hash_obj(components)


class Run(HashableBase):
    """One attempt at one unit of work (ADR §5.3)."""

    run_id: str
    objective_id: str
    mission_brief: BriefRef
    stage: str
    status: RunStatus
    parents: list[dict[str, Any]]
    spec: dict[str, Any]
    code_hash: str
    env: dict[str, Any]
    hardware: dict[str, Any]
    inputs: list[Any]
    outputs: list[Any]
    guard_report: dict[str, Any] | None = None
    metrics_path: str
    recipe_stack: dict[str, Any] | None = None


class Artifact(HashableBase):  # noqa: PYI043
    """Content-addressed artifact reference (ADR §5.4)."""

    model_config = ConfigDict(frozen=True)

    path: str
    sha256: str
    role: str
    producer_run_id: str
    created_at: str
    media_type: str | None = None

    _HASH_FIELD_NAMES = frozenset({"sha256"})


class Scorecard(HashableBase):
    """Result of running a suite against one ReleaseTuple (ADR §5.6)."""

    suite_hash: str
    seeds: list[int]
    decode_hash: str
    subject_tuple_hash: str
    recipe_stack_hash: str | None = None
    dimensions: dict[str, float]
    raw_channel: dict[str, float] = Field(alias="raw")
    guarded_channel: dict[str, float] = Field(alias="guarded")
    findings: list[dict[str, Any]]
    slices: dict[str, Any]
    resources: dict[str, Any]

    # Legacy property names for backward compat with test code.
    @property
    def raw(self) -> dict[str, float]:
        return self.raw_channel

    @property
    def guarded(self) -> dict[str, float]:
        return self.guarded_channel


class Decision(HashableBase):
    """Aggregation result mapping evidence to an action (ADR §5.7)."""

    action: DecisionAction
    objective_id: str
    mission_brief_ref: BriefRef
    subject: dict[str, Any]
    gate_results: list[dict[str, Any]]
    intervention: dict[str, Any] | None = None
    human_requests: list[HumanInboxItem] = []
    dossier_ref: str
    created_at: str
    recipe_stack_ref: dict[str, Any] | None = None


class Defect(HashableBase):
    """Durable memory so the agent does not rediscover the same failure (ADR §5.8)."""

    id: str
    taxonomy: str
    evidence: list[str]
    first_run_id: str
    last_run_id: str
    interventions: list[dict[str, Any]]
    status: DefectStatus


class Policy(HashableBase):
    """Allow/deny map for agent capabilities (ADR §5.9)."""

    capabilities: dict[str, bool]


class BudgetLedger(HashableBase):
    """Remaining budget counters (ADR §5.9)."""

    wall_time: float | int
    gpu_hours: float | int
    judge_tokens: int
    smoke_runs: int
    scale_runs: int


class TrainCard(HashableBase):  # noqa: PYI043
    """Twin of every train checkpoint set (ADR §5.10)."""

    model_config = ConfigDict(frozen=True)

    objective_id: str
    run_id: str
    mission_brief: BriefRef
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
    reference_id: str | None = None
    best_checkpoint_ref: dict[str, Any] | None = None
    recipe_stack_hash: str
    recipe_adaptations: list[dict[str, Any]] = []


class MixtureSpec(HashableBase):  # noqa: PYI043
    """Distributional requirements for admitted mixtures (ADR §5.11)."""

    model_config = ConfigDict(frozen=True)

    dimensions: list[str]
    floors: dict[str, int]
    caps: dict[str, int]
    quotas: dict[str, int]


# TargetShape shares the identical schema with MixtureSpec per ADR §5.x.
TargetShape = MixtureSpec


class AdmissionReport(HashableBase):  # noqa: PYI043
    """Required output of every admit (ADR §5.12)."""

    model_config = ConfigDict(frozen=True)

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


class HumanInboxItem(HashableBase):
    """Pending human judgment request (ADR §5.13)."""

    id: str
    objective_id: str
    gate_name: str
    payload_ref: str
    response_schema: dict[str, Any]
    created_at: str
    age: float | int | None = None
    status: InboxStatus


class Recipe(HashableBase):  # noqa: PYI043
    """Versioned, evidence-backed specification for a named behavioral effect (ADR §5.14)."""

    model_config = ConfigDict(frozen=True)

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
    notes_head: str | None = None

    _HASH_FIELD_NAMES = frozenset({"instruction_hash", "notes_head"})


class RecipeStack(HashableBase):  # noqa: PYI043
    """Immutable composition for one objective iteration or run (ADR §5.14)."""

    model_config = ConfigDict(frozen=True)

    id: str
    recipes: list[dict[str, Any]]
    overrides: dict[str, Any]
    allocation: dict[str, float]
    conflict_decisions: list[Any]
    validation_plan: dict[str, Any]
    stack_hash: str

    _HASH_FIELD_NAMES = frozenset({"stack_hash"})
