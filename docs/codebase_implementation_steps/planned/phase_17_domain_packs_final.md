# Phase 17 — Domain packs, skills pass 2, final conformance sweep

| Field | Value |
|---|---|
| **Status** | [ ] |
| **Depends on** | Phases 00–16 |
| **Checklist sections** | §16, §17 (skills pass 2), §17.1 (recipes), §18 (full audit), §19 (success criteria) |
| **ADR refs** | §5.0/§7.0 (MissionBrief/elicit), §5.14/§7.17 (recipes), §7.15 (domain packs), §7.16 (skills), §13.3, §14, §18 (closing rule) |

## Goal

Complete domain-pack registration, align skills and recipes with implemented contracts, and audit conformance to the ADR.

## Part A — Domain pack mechanism (`facktry/domains/`)

- `DomainPack` protocol: name, elicitation branches/required brief sections, schemas/controlled vocabs, generators/filters/labelers/stratifiers, suite case providers, domain oracles, prompt policies/tool schemas, optional stage implementations.
- Explicit registry: `register_domain(pack)` / `get_domain(name)`. **Core never imports a concrete domain's rules** — packs import core, not vice versa. Test: scanning core modules finds no import of any registered pack module.
- `run_stage` (facade from phase 09) now dispatches to registered domain stages: stage name resolved via registry, executed inside a proper governed `Run`.
- Ship `facktry/domains/_template/`: skeleton pack (empty schemas, `suites/` dir, README explaining what a pack supplies) — a starting point, not a working domain. No real domain until a real objective exists (ADR §13.2 item 12).

## Part B — Skills pass 2 (`docs/skills/`)

- Re-read every `docs/skills/*/SKILL.md`, including `docs/skills/elicit-mission/SKILL.md`. Update all call examples to the **real** `agent_api` signatures, result envelope shape, and error taxonomy as implemented. Remove any API names that don't exist; add any that do and are missing.
- Skills remain documentation, not runtime: no skill may instruct bypassing govern/admit/smoke/measure. Add a line to `docs/skills/README.md` stating the canonical `agent_api` module path.

## Part C — Recipe catalog and composition (`recipes/`)

- Re-read `docs/recipes/_template/RECIPE.md` and every curated `docs/recipes/*/RECIPE.md` against ADR §5.14/§7.17.
- Parse/lint required effect, mechanism, ingredient, compatibility, tradeoff, validation, evidence, provenance, and notes sections.
- Implement immutable recipe instruction versions plus append-only structured `## Recipe Notes`; notes must carry later-use context and evidence refs without changing the instruction hash.
- Implement `recommend_recipes` using target effects, Objective constraints, open defects, notes, and prior outcomes; return ranked read-only candidates.
- Implement `RecipeStack` composition with exact versions, ordering, overrides, allocations, conflict decisions, and validation plan. Refuse incompatible or Objective-disallowed stacks.
- Append a structured use note after every governed attempt, including failures and non-promotions, without changing the instruction hash.
- Test that recipe application expands into the ordinary governed control loop and cannot weaken hard gates or treat notes as measured evidence; verify later recommendations can use accumulated notes.

## Part D — Conformance sweep (the ADR §14 checklist, verified)

Verify each ADR §14 success criterion and record evidence:

1. Complete adaptive elicitation and save a hashed MissionBrief with intent, success case, research pointers, and individual hard-gate approvals; then freeze the hashed objective with gates/budget/baselines/suites — demo via test/fixture, cite test names.
2. Agent iterates data+train under budget without per-step human ops — scripted end-to-end loop test (fake backends) running control-loop steps 1–9 from ADR §8 in order.
3. Hard enforced / soft can't promote alone / diagnostic can't select — cite phase 08/12 tests.
4. Sealed blind + paired compare — cite phase 07 tests.
5. Human inbox + CLI pressure — cite phase 09/10 tests.
6. Pinned ReleaseTuple + reproducible dossier — yield_release + dossier hash reproduction test.
7. Bare `facktry` situational awareness — cite phase 10 tests.
8. Curated recipes compose into governed, measured, hashed `RecipeStack`s with append-only use notes; cite recipe parser/composition/governance tests.
9. Ancestors hash-unchanged after corrective trains — cite phase 11 test.
10. **§13.3 / checklist §18: run the entire mandatory test list and check every row green in one pytest run.** Any missing → implement now, do not waive silently.
11. Every objective and experiment traces to an immutable MissionBrief containing intent, success case, research pointers, and hard-gate approvals.

Also sweep ADR §12 (out of scope): confirm none of the excluded subsystems crept into core. Confirm recipes remain declarative effect specifications, not an ungoverned workflow engine.

### End-to-end loop test
`tests/test_control_loop_e2e.py`: elicit fixture → save MissionBrief → freeze objective (fake suites/backends) → preflight → pin_suites → generate_and_admit → train_smoke → decide(allows scale) → train_scale → select_checkpoint → measure/compare (base/candidate) → decide → human promote via inbox ingest → yield_release. Assert: every transition governed (attempt freeze/experiment without a brief or out-of-order step → typed denial), all artifacts hash-registered, dossier exists, ancestors unchanged, final tuple pinned.

## Fail-closed requirements

- Waivers (`[-]`) only with written reasons in the checklist; the sweep must not manufacture green.

## Tests

- Registry isolation (no core→domain import).
- `run_stage` dispatch to a fixture pack stage inside a governed run.
- Recipe parser, recommendation, note append, stack conflict, recipe-feedback, and recipe-governance tests.
- Control-loop E2E above.
- Final full-suite run clean.

## Checklist updates

- §16 all `[x]`; §17 pass-2 rows `[x]`; §17.1 recipe rows `[x]`; **every §18 row `[x]`**; §19 rows `[x]` with one-line evidence citations; all Progress summary rows `[x]`; "Last global review" date bumped.

## Definition of done

Facktry is complete for its stated purpose per ADR §14, with the checklist fully and honestly green. Update the phase index in this directory's README (all `[x]`).
