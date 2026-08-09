"""Internal DataRow model for admission checks.

Not exported as ontology — used internally within the admit pipeline.
"""

from __future__ import annotations

from pydantic import BaseModel

from ..errors import SerdeError
from ..hashing import hash_obj
from ..types import SourceClass

# ── DataRow ───────────────────────────────────────────────────────────────

HASH_FIELDS = frozenset({"row_hash"})

VALID_SPLITS = frozenset({"train", "dev", "seal"})


class DataRow(BaseModel):
    """One row in an admitted dataset. Internal to admit pipeline."""

    model_config = {"extra": "forbid"}

    row_id: str
    split: str = "train"
    # Visible input given to the model (serialized prompt). Approach B.
    visible_input: dict[str, object]
    target: str
    dependence_keys: dict[str, str]
    source_class: SourceClass | None = None
    teacher_id: str | None = None
    labels: list[object] = []
    tags: list[object] = []
    transformation_policy_id: str = ""
    provenance_refs: list[str] = []
    generator_context: dict[str, object] | None = None
    row_hash: str = ""

    def _text_of_messages(self) -> str:
        """Extract concatenated text from role-content messages."""
        msgs = self.visible_input.get("messages", [])
        parts = []
        for m in msgs:
            content = m.get("content", "") if isinstance(m, dict) else ""
            if content:
                parts.append(str(content))
        return " ".join(parts)

    @classmethod
    def from_dict(cls, d: dict) -> "DataRow":
        try:
            return cls.model_validate(d)
        except Exception as exc:
            raise SerdeError(str(exc)) from exc


def row_hash(row: DataRow) -> str:
    """Deterministic hash over the row payload excluding derived row_hash."""
    exclude_fields = HASH_FIELDS & set(type(row).model_fields.keys())
    return hash_obj(row.model_dump(mode="json", exclude=exclude_fields))
