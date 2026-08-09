"""Admission module — fail-closed data gate before training.

Public API:
- admit(store, objective_id, rows, *, for_training=True) → AdmissionReport
- generate_and_admit(store, objective_id, spec) → AdmissionReport
- validate_scenario(scenario) → None (raises AdmitRejection on failure)
- merge_generation_parts(parts) → MergeResult
- GenerationPartManifest — typed manifest for parallel generation tracking
- DataRow — internal row model (exported for test fixtures)
- AdmitRejection — typed denial exception
"""

from ..errors import AdmitRejection
from ._row import DataRow, row_hash
from .core import (
    GenerationPartManifest,
    MergeResult,
    admit,
    generate_and_admit,
    merge_generation_parts,
    validate_scenario,
)

__all__ = [
    "admit",
    "generate_and_admit",
    "validate_scenario",
    "merge_generation_parts",
    "GenerationPartManifest",
    "MergeResult",
    "DataRow",
    "row_hash",
    "AdmitRejection",
]
