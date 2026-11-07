# Swing Confluence Recipe Workbench — Implementation Plan

**Goal:** Make a change of timeframe, indicator family, holding ruler or cost assumption a saved, reproducible research configuration rather than a rebuilt environment.

**Architecture:** A small, non-executing consumer of the existing Strategy Lab / Technical Opportunity / Temporal Grain owners. The first slice compiles a strict JSON recipe into deterministic candidate identities, explicit planned-look counts, clock arithmetic diagnostics and unresolved owner requirements. It neither evaluates returns nor admits data. Source/data/clock and evaluator qualification remain with the incumbents.

**Spec:** DESIGN_AND_RESEARCH_PROTOCOL.md in this directory.
**Stack:** Python standard library; pytest for tests. No new service, data store, calendar, signal registry, event ledger, evaluator, renderer, background worker or production integration.

## Scope and files

Create `scripts/research/run_toi_swing_plan.py`, `tests/test_toi_swing_plan.py`, and this directory's recipe, design/protocol and verification report. Do not change `engine/lab.py`, #6803, #7094, #7107, their workstreams, production data or CI/control policies.

## Task 1 — Deterministic research-plan compilation

1. Write tests for the frozen recipe's 720 configurations, 2,160 cost scenarios and conservative 8,640 paired comparisons; verify RED against a minimal unimplemented entrypoint.
2. Implement `compile_recipe(recipe: dict, *, include_cases: bool = False) -> dict` and strict JSON loading. Return DRAFT_NOT_REGISTERED, outcome execution unavailable, all authority false, and the exact outstanding owner dependencies. A populated reference is an assertion, never a permission grant.
3. Reject duplicate keys, nonfinite JSON, booleans masquerading as numbers, unknown fields, invalid clocks, duplicate values, impossible primary cost selection and an over-budget cross-product before allocating cases. No dynamic imports/eval/network or TrialLedger writes.
4. Verify order-invariant identities and changed-semantic-input sensitivity. Report 120m/180m terminal-bucket arithmetic from an explicitly supplied 390-minute example, not a new exchange calendar or chart-parity claim.
5. Provide a bounded default CLI summary and explicit artifact-output option; test malformed input, stdout purity and no outcome-run option.

## Task 2 — Protocol and verification

1. Preserve source pins and unresolved upstream PRs; document separate leader-pullback and range-reversal hypotheses, fixed baselines, holding rulers and calendar-time validation.
2. Finish a primary-source literature assessment of rates, scheduled news and auction mechanisms. Label the single-name swing link as an untested extension, not an established trading effect.
3. Run the full local test surface and a real CLI plan compilation twice. Preserve deterministic digests and verify all no-execution/no-authority fields.
4. Publish only owned source/recipes/docs and non-market verification evidence on the isolated consumer branch. Open a draft PR; read back the exact head and file set. No merge or deployment.

## Review focus

The highest-risk boundaries are semantic clock identity versus nominal minutes; empty/duplicate candidate axes; configurable fields being mistaken for owner admission; understated search counts; and a correct planner being mistaken for a tested strategy. Each must have a negative test or an explicit non-executable boundary. Source acquisition for native Temporal Grain tests is separate from this planner's standard-library tests; report unavailable native proof rather than fabricating it.
