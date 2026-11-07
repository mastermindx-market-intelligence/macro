---
workstream: WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
session: claude/ssd-cs-v2-i1a-supply-1dc9011d0b4abc77
model: opus
ended_because: ci_handoff
mission: >
  Masterplan task I1a (research/capital_structure/e2e_20261013/MASTERPLAN.md,
  acceptance rows A19, A23, A24, A25; deps C0, I0, B1): attach
  evidence-bound instrument economic terms to resolved instruments as of a
  point in time, and evaluate scenario supply (incremental shares,
  as-converted claims, resalable shares, issuer cash) under the frozen C0
  interface evaluate_supply(InstrumentSet, ShareBasis, ScenarioSpec) ->
  IssuerState, with no HTTP, LLM, collector or SEC request, and ship it
  through the ordinary chain.
state_before: >
  C0 froze EconomicTerm, Instrument, ScenarioSpec, ActionSelection,
  PriceAssumption and CorporateActionBasis, and named
  engine/capital_structure/supply_scenarios.py as the owner of
  evaluate_supply, but neither the attach module nor the supply evaluator
  existed. I0 resolved instruments with empty economic_terms, B1 selected a
  share basis, and nothing turned an exhibit term into an admitted
  instrument economic term or a scenario into supply.
changed:
  - path: engine/capital_structure/issuer_state_contracts.py
    what: >
      SPEC_I1 §1 C0 2.1.0 contract delta (commit 47f4c2af): EconomicTerm and
      the economic-term name, unit and flag vocabularies on Instrument.
  - path: contracts/capital_structure_state.v2.schema.json
    what: The matching JSON-schema delta for the C0 2.1.0 economic-term contract.
  - path: tests/test_capital_structure_issuer_state_contracts.py
    what: Enum pins only (3 lines); no other existing test was edited.
  - path: engine/capital_structure/instrument_economics.py
    what: >
      New module (capital_structure.instrument_economics.v1):
      validate_economic_term_record (closed
      capital_structure.instrument_economic_term.v1), validate_term_binding
      (closed capital_structure.instrument_term_binding.v1, adjudicated_gold
      only), attach_economic_terms (per instrument and name: one value
      admitted, same-effective distinct values one contradicted term, later
      effective wins with the rest superseded, deferred-only unknown; only
      outstanding/amended instruments receive terms; receipt with
      rule_digest over ECONOMIC_TERM_NAMES).
  - path: engine/capital_structure/supply_scenarios.py
    what: >
      New module (capital_structure.supply_scenarios.v1): evaluate_supply
      (the frozen 3-argument interface) and supply_trace (per-row trace with
      fraction), the SETTLEMENT_RULES table (warrant cash, cashless/net_share,
      pre_funded, conversion, resale), exact Decimal arithmetic floored to
      whole shares, A19 pre-split staleness, A25 notice and holder-cap
      execution limits that never shrink the claim, and components that are
      never summed.
  - path: tests/test_capital_structure_instrument_economics.py
    what: "New suite, 64 tests: the closed term and binding record validators and attach_economic_terms (SPEC_I1 §2-§3)."
  - path: tests/test_capital_structure_supply_scenarios.py
    what: "New suite, 100 tests: evaluate_supply and supply_trace, including A19, A23, A24, A25, the settlement rules, Unknown discipline, determinism and the never-summed guard (SPEC_I1 §4-§6)."
  - path: .github/ci/legacy-jobs.yml
    what: Registers both new suites in the capital-structure-intelligence step, directly after tests/test_capital_structure_funding.py.
  - path: agentos/decisions/DEC-CS-V2-SUPPLY-ECONOMIC-TERMS-I1.md
    what: The I1 decision record (frozen spec), with reversibility set to the schema enum value costly.
verified:
  - claim: "The eight I1 suites plus the capacity, capacity-joint and registration-integration suites pass on the merged content (origin/main 31f317d8 merged into 47f4c2af, plus the I1a files)."
    command: "python3.12 -m pytest -q -p no:cacheprovider tests/test_capital_structure_instrument_economics.py tests/test_capital_structure_supply_scenarios.py tests/test_capital_structure_issuer_state_contracts.py tests/test_capital_structure_instrument_resolution.py tests/test_capital_structure_share_basis.py tests/test_capital_structure_term_integration.py tests/test_capital_structure_funding.py tests/test_capital_structure_contracts.py tests/test_capital_structure_capacity.py tests/test_capital_structure_capacity_joint.py tests/test_capital_structure_registration_integration.py"
    result: "555 passed, 0 failed (64 instrument_economics, 100 supply_scenarios, 101 issuer_state_contracts, 41 instrument_resolution, 44 share_basis, 30 term_integration, 73 funding, 25 contracts, 34 capacity, 17 capacity_joint, 26 registration_integration)."
  - claim: The C0 interface-ownership test imports the real supply module and accepts its 3-parameter signature.
    command: python3.12 -m pytest tests/test_capital_structure_issuer_state_contracts.py -q
    result: "101 passed."
  - claim: An independent adversarial probe re-derives A19/A23/A24/A25 and the attach rules from the spec, not from the lane's tests.
    command: PYTHONPATH=. python3.12 <seat a9559a4c scratchpad>/i1/probe_i1a.py (scratch probe held by the seat, not committed)
    result: "109 checks, 0 FAIL."
  - claim: The new suites are registered and no test is left unrun.
    command: python3 scripts/audit_unrun_tests.py
    result: "Exit 0; both new suites are wired, and only pre-existing stale-baseline warnings for unrelated suites print."
  - claim: All twelve legacy packs validate after the registration edit.
    command: python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --pack-index N --pack-count 12 --validate-only, N = 0..11
    result: "Exit 0 for every index 0..11 and for the plain --validate-only form; capital-structure-intelligence sits in pack 8."
  - claim: Neither engine module uses float except in docstrings and refusal checks.
    command: grep -n float engine/capital_structure/instrument_economics.py engine/capital_structure/supply_scenarios.py
    result: 10 matching lines, every one a docstring or an isinstance refusal check.
  - claim: The Agent OS records validate.
    command: python3 scripts/agentos.py validate
    result: 0 errors.
unverified:
  - claim: Hosted ci.yml is green on the exact pushed head.
    what_would_verify: The ci.yml run for the pushed head concluding with every pack green (the Workers Builds X excluded).
  - claim: I1a is merged and landed on origin/main.
    what_would_verify: Squash-merge with --match-head-commit on concluded green, then a bare git fetch and a per-path blob comparison against origin/main.
unresolved:
  - >
    Expiry is not evaluated: an expired warrant still contributes supply
    until an expiry rule is specified (SPEC_I1 clarification D17).
  - >
    A selected action whose route is not a supply route yields a row with a
    null instrument_id, every component unknown and a route_not_supply
    Unknown, and makes incremental unknown (clarification D13); a
    contract decision may prefer refusing such a scenario outright.
  - >
    No extractor feeds term records yet; the I1b extractor (SPEC_I1 §8)
    produces canonical_extraction records, and bindings are owner-authored
    adjudicated_gold only.
  - >
    Nothing persists attached terms or supply state, and no daily.yml wiring
    exists; both need seat approval.
  - >
    The legacy-jobs.yml edit is a CI-authority change; one main ci.yml
    baseline is owed after merge, dispatched by the seat over a clear field.
next_actions:
  - I1b builds the deterministic exhibit extractor that emits capital_structure.instrument_economic_term.v1 records (SPEC_I1 §8).
  - X0 consumes evaluate_supply / supply_trace components and cash_effects without summing components.
do_not_redo:
  - Sum incremental, as_converted and resalable into one number; components are separate by contract.
  - Rescale a pre-split term by the split ratio; a term effective before the split date is stale and names an Unknown.
  - Treat resale as new shares or issuer cash; resale mints no shares and no cash.
  - Shrink a claim because a notice period or holder cap limits execution; the claim survives and only the incremental row is limited.
  - Use float anywhere in term values or supply arithmetic; Decimal only, floored to whole shares.
  - Let canonical_extraction bind a term to an instrument; only an adjudicated_gold binding attaches.
danger_areas:
  - decided_at governs binding visibility and effective_at governs application; both must be at or before as_of.
  - Contradiction is per (instrument, name, effective_at); a later effective value supersedes rather than contradicts.
  - After a split, every split-sensitive term (exercise_price, conversion_price, prefunded_residual_price, shares_per_instrument, instruments_outstanding) needs an effective_at on or after the split date; an undated one is stale by clarification D9, and the contract requires a date only for price and ratio names, so a producer that leaves instruments_outstanding undated blinds that instrument after any split.
  - The holder-cap bound floor((cap*E - pos)/(1 - cap)) needs an explicit holder_position UnknownResolution; without it the row is unknown, never unbounded.
decisions:
  - DEC:CS-V2-SUPPLY-ECONOMIC-TERMS-I1
---

# Capital Structure V2 — I1a instrument economics and supply handoff

engine.capital_structure.instrument_economics attaches owner-bound economic
terms to resolved instruments; engine.capital_structure.supply_scenarios
turns a scenario into separate supply components, with every gap a named
Unknown.
