---
workstream: WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
session: claude/cs-v2-t0-candidate-integration
model: opus
ended_because: ci_handoff
mission: >
  Masterplan task T0 (research/capital_structure/e2e_20261013/MASTERPLAN.md,
  acceptance rows A04, A08, A09; deps E0 and C0): integrate the existing
  direct document terms and the existing instrument-candidate compiler on
  accepted C0 inputs, keep the pre-instrument refusal and keep identities
  immutable, with no new collector, no HTTP, no LLM and no SEC request, and
  ship it through the ordinary chain.
state_before: >
  E0 (#9244, reference pack with typed fact_origins) and C0 (#9159, frozen
  issuer-state contracts) landed on main. The direct document-term compiler
  and the candidate compiler existed and were tested in isolation, but no
  code bound them to an accepted C0 input generation, checked a direct term's
  fact origin against the reference pack, or re-proved candidate closure
  after compile. A compiled candidate row could not enter a C0
  CandidateBundle or CapitalInputs because the C0 key filter rejected
  authority.prophet_authority; the seat fixed that in PR #9263.
changed:
  - path: engine/capital_structure/term_integration.py
    what: >
      New module (capital-structure-term-integration/1.0.0):
      integrate_candidate_terms on CapitalInputs, assert_closed_candidate_term,
      direct_term_origin, refuse_nomination, frozen CandidateIntegration,
      DirectTermOrigin and TermRefusal, CLOSED_CANDIDATE_AUTHORITY and
      INSTRUMENT_IDENTITY_KEYS. Reuses compile_candidate_term_records and
      current_candidate_terms_as_of unchanged; edits no existing module.
  - path: tests/test_capital_structure_term_integration.py
    what: >
      30 tests: closed projection; CandidateBundle and CapitalInputs admit
      the compiled rows and reject prophet_authority true; A04 rerun and
      re-observation create nothing and keep ids, occurrence ids are clock
      independent and never legacy, a later interpretation is not visible
      before its system time, a rebuilt direct ledger cannot re-mint; A08
      a repeated exhibit in a second filing (bytes derived in memory, fixture
      untouched) stays two occurrences with identical values; A09 every
      non-canonical origin, both canonical claims and an unknown origin are
      refused without changing the ledger digest, a poisoned or starved
      reference pack is refused, a non-canonical extraction method is refused;
      closed-boundary belt (widened authority with a re-hashed id, nested
      instrument identity keys, forged occurrence id, tampered value);
      unavailable and not_built support, missing binding, conflicting
      existing ledgers, determinism.
  - path: .github/ci/legacy-jobs.yml
    what: Registers the new suite in the capital-structure-intelligence step next to the instrument-candidate suite.
  - path: agentos/decisions/DEC-CS-V2-TERM-INTEGRATION-T0.md
    what: The T0 decision record.
verified:
  - claim: The new suite passes against the C0 contract carrying the #9263 exemption.
    command: python3.12 -m pytest tests/test_capital_structure_term_integration.py -q (issuer_state_contracts.py overlaid from origin/claude/cs-v2-c0-prophet-authority-key, then restored)
    result: 30 passed. Against the pre-#9263 contract the two tests that bind compiled rows through CandidateBundle/CapitalInputs fail with the prophet_authority ContractViolation, as expected.
  - claim: Neighbouring capital-structure suites are unaffected.
    command: python3.12 -m pytest tests/test_capital_structure_legacy_compat.py tests/test_capital_structure_reference_qualification.py -q
    result: 38 passed.
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
  - claim: T0 is merged and landed on origin/main.
    what_would_verify: Squash-merge with --match-head-commit on concluded green, then a bare git fetch and a per-path blob comparison against origin/main.
unresolved:
  - >
    Reference-pack gaps owed upstream of later waves and not closable in T0
    without an SEC source packet: held_out_pattern_witness,
    foreign_issuer_f3_witness and whk_replacement_issuer.
  - >
    The legacy-jobs.yml edit is a CI-authority change; one main ci.yml
    baseline is owed after merge, dispatched by the seat over a clear field.
  - >
    Nothing persists the CandidateIntegration ledger yet; T0 is a pure
    function over accepted inputs. Persisting it, and wiring it into
    daily.yml, needs seat approval.
next_actions:
  - I0 consumes CandidateIntegration.candidate_bundle() and resolves identity only from explicit owner decisions keyed on logical_candidate_term_id.
do_not_redo:
  - Re-key candidates by issuer, title, strike or value; the occurrence identity is the digest of the source slot.
  - Admit a nomination that merely claims canonical_extraction or adjudicated_gold.
  - Fork or widen the C0 key filter outside issuer_state_contracts.py; request any further delta from the seat.
danger_areas:
  - candidate_term_id includes point_in_time, so it is minted once; only a re-observation through compile_document_term_records with existing_observations keeps it. A rebuilt direct ledger is refused, not re-minted.
  - An unavailable or not_built integration has empty records; never persist those records over an existing candidate ledger.
prs: [9270]
---

# Capital Structure V2 — T0 term integration handoff

engine.capital_structure.term_integration is the only path from accepted direct terms
to closed candidate terms; it mints no instrument, quantity or join.
