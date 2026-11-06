---
workstream: WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
session: claude/cs-v2-i0-instrument-resolution
model: opus
ended_because: ci_handoff
mission: >
  Masterplan task I0 (research/capital_structure/e2e_20261013/MASTERPLAN.md,
  acceptance rows A04, A08, A09; deps T0 and C0): resolve supported
  series/tranche identity, supersession and retirement from explicit
  evidence behind the frozen C0 interface
  resolve_instruments(CandidateBundle, ResolutionInputs, as_of) ->
  InstrumentSet, keep ambiguous candidates unresolved, with no HTTP, LLM,
  collector or SEC request, and ship it through the ordinary chain.
state_before: >
  C0 froze the Instrument / InstrumentSet / ResolutionInputs contracts and
  named engine/capital_structure/instrument_resolution.py as the owner of
  resolve_instruments, but the module did not exist. T0 (PR #9270) made the
  closed candidate rows available as a C0 CandidateBundle through
  CandidateIntegration.candidate_bundle(). Nothing turned a candidate into
  an instrument, and no record type existed for an owner identity decision.
changed:
  - path: engine/capital_structure/instrument_resolution.py
    what: >
      New module (capital-structure-instrument-resolution/1.0.0):
      resolve_instruments (the frozen 3-argument interface),
      resolve_instrument_trace (same inputs plus an optional reference pack,
      returns the InstrumentSet with per-series outcomes, unresolved reasons,
      superseded terms, refused and pending decisions), build_decision,
      decision_id_for, instrument_id_for, and the closed decision schema
      capital_structure.instrument_resolution_decision.v1 with methods
      supported_identity, amendment_join and retirement. Edits no existing
      module and no C0 contract.
  - path: tests/test_capital_structure_instrument_resolution.py
    what: >
      41 tests: frozen interface arity; A08 repeated/amended exhibit (second
      filing derived in memory from the sealed fixture, so both copies are
      genuinely identical in title, classification and value) stays
      unresolved without a decision, a founding on one filing leaves the
      repeat unresolved, binding both copies is duplicate_current_term, and
      an amendment_join with explicit supersession pairs is the only join;
      ambiguity (missing or conflicting founding, inconsistent identity,
      cross-series claim, superseding an unbound term, invisible or unseen
      candidates, conflicting retirements, amendment after retirement, an amendment or
      retirement effective before its founding) makes
      the whole series unresolved with reasons; retirement keeps identity;
      pending decisions are never retroactive; A09 every non-canonical
      origin, canonical_extraction and an unknown origin are refused with no
      effect and a poisoned pack is refused; A04 ids are clock-free and
      stable across amendment and retirement, no legacy keys, outputs are
      deterministic and order independent; no quantity, score or unresolved
      Instrument is emitted; decisions are content-addressed and closed;
      the T0 closed-candidate boundary is re-proved at resolution.
  - path: .github/ci/legacy-jobs.yml
    what: Registers the new suite in the capital-structure-intelligence step next to the term-integration suite.
  - path: agentos/decisions/DEC-CS-V2-INSTRUMENT-RESOLUTION-I0.md
    what: The I0 decision record.
verified:
  - claim: The new suite passes against main's C0 contract with no overlay.
    command: python3.12 -m pytest tests/test_capital_structure_instrument_resolution.py -q
    result: 41 passed.
  - claim: The C0 interface-ownership test now imports the real module and accepts its signature.
    command: python3.12 -m pytest tests/test_capital_structure_issuer_state_contracts.py -q
    result: passed (INTERFACE_OWNERSHIP checks len(signature.parameters) == 3).
  - claim: The new suite is registered and no test is left unrun.
    command: python3 scripts/audit_unrun_tests.py
    result: exit 0.
  - claim: All twelve legacy packs validate after the registration edit.
    command: python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --pack-index N --pack-count 12 --validate-only, N = 0..11
    result: rc=0 for every pack.
  - claim: The Agent OS records validate.
    command: python3 scripts/agentos.py validate
    result: 0 errors.
unverified:
  - claim: Hosted ci.yml is green on the exact pushed head.
    what_would_verify: The ci.yml run for the pushed head concluding with every pack green (the Workers Builds X excluded).
  - claim: I0 is merged and landed on origin/main.
    what_would_verify: Squash-merge with --match-head-commit on concluded green, then a bare git fetch and a per-path blob comparison against origin/main.
unresolved:
  - >
    The frozen 3-argument interface carries no issuer id, so resolving an
    empty candidate bundle with no decisions raises (the issuer is
    underivable) rather than returning an empty set. A C0 delta adding an
    issuer to CandidateBundle or ResolutionInputs would let it return empty;
    request it from the seat if I1 or X0 needs it.
  - >
    Instrument status unresolved_candidate is never emitted, because an
    unresolved candidate has no kind or security class; unresolved
    candidates travel only in InstrumentSet.unresolved_candidate_ids. Using
    the status would need a C0 ruling on nullable kind and class.
  - >
    Correcting a wrong founding decision is unsupported: a second founding
    for the same series is a conflict and leaves the series unresolved. An
    explicit correction method is a later contract decision.
  - >
    Retirement binds no deregistration candidate (it cites evidence only).
  - >
    Nothing persists the InstrumentSet or the decision records yet, and no
    daily.yml wiring exists; both need seat approval.
  - >
    The legacy-jobs.yml edit is a CI-authority change; one main ci.yml
    baseline is owed after merge, dispatched by the seat over a clear field.
next_actions:
  - I1 and X0 consume InstrumentSet plus ResolutionTrace.series / unresolved / superseded; every visible candidate is in exactly one of bound, superseded or unresolved.
  - Owner decisions are authored with build_decision and stored with their content-addressed decision_id before any persistence lane is approved.
do_not_redo:
  - Join candidates by title, classification, strike, value or exhibit text; only an amendment_join decision with explicit supersession pairs joins.
  - Mint instrument identity from a candidate id or a clock; instrument_id is stable_id over issuer_id and the owner series_key only.
  - Let canonical_extraction or any non-canonical origin mint identity; only adjudicated_gold does, and only while the reference pack admits it.
  - Pick a winner among conflicting decisions; conflicts leave the series unresolved.
danger_areas:
  - decided_at governs visibility and effective_at governs application; a decision visible but not yet effective is pending and must stay non-retroactive.
  - The slot check reads term name, title and classification only to refuse two live copies of one term; never turn it into a join.
  - Resolution re-runs the T0 closed-candidate assertion on every row; a row that fails it raises rather than resolving.
prs: [9274]
---

# Capital Structure V2 — I0 instrument resolution handoff

engine.capital_structure.instrument_resolution turns closed candidate terms into
instruments only through owner decisions; anything ambiguous stays unresolved.
