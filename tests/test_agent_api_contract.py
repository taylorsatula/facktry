"""Cross-phase contract tests for the stable governed facade surface."""

import inspect

import pytest

pytestmark = pytest.mark.conformance


def _parameter_names(method):
    return [name for name in inspect.signature(method).parameters if name not in {"self", "cls"}]


def test_agent_api_uses_the_canonical_operation_names_and_signatures():
    from facktry.agent_api import AgentAPI

    expected_prefixes = {
        "pin_suites": ["objective_id", "suite_refs"],
        "generate_and_admit": ["objective_id", "spec"],
        "run_stage": ["stage_name", "objective_id", "spec"],
        "train_smoke": ["objective_id", "spec"],
        "train_scale": ["objective_id", "spec"],
        "select_checkpoint": ["objective_id", "spec"],
        "measure": ["objective_id", "spec"],
        "compare": ["objective_id", "spec"],
        "decide": ["objective_id"],
        "inbox_ingest": ["item_id", "response"],
        "yield_release": ["objective_id", "tuple_or_ref"],
    }
    for name, expected in expected_prefixes.items():
        assert _parameter_names(getattr(AgentAPI, name))[: len(expected)] == expected

    assert not hasattr(AgentAPI, "ingest_inbox")
    assert not hasattr(AgentAPI, "measure_and_compare")


def test_agent_api_exposes_every_documented_mutation_boundary():
    from facktry.agent_api import AgentAPI

    for name in (
        "save_mission_brief",
        "freeze_objective",
        "supersede_objective",
        "preflight",
        "compose_recipe_stack",
        "append_recipe_note",
        "pin_suites",
        "admit",
        "generate_and_admit",
        "run_stage",
        "train_smoke",
        "train_scale",
        "select_checkpoint",
        "measure",
        "compare",
        "decide",
        "inbox_ingest",
        "defects_close",
        "yield_release",
    ):
        assert callable(getattr(AgentAPI, name, None)), name


def test_agent_api_exposes_the_complete_shared_read_query_surface():
    from facktry.agent_api import AgentAPI

    for name in (
        "inbox_list",
        "query_objectives",
        "query_runs",
        "query_run",
        "query_decisions",
        "query_defects",
        "query_inbox",
        "query_budget",
        "query_pins",
        "query_metrics_tail",
    ):
        assert callable(getattr(AgentAPI, name, None)), name
