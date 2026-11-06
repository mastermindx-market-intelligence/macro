---
key: CS-V2-TERM-INTEGRATION-T0
question: >
  Masterplan task T0 (research/capital_structure/e2e_20261013/MASTERPLAN.md,
  acceptance rows A04, A08, A09) must integrate the existing direct document
  terms and the existing instrument-candidate compiler on accepted C0 inputs,
  keep the pre-instrument refusal and keep identities immutable. How do
  accepted inputs reach the candidate boundary, what identity does a
  candidate carry, which fact origins may mint, and what must T0 refuse?
answer: >
  engine/capital_structure/term_integration.py (version
  capital-structure-term-integration/1.0.0) composes the sealed compilers and
  replaces neither. integrate_candidate_terms(inputs: CapitalInputs, *,
  source_manifests, source_reader, generated_at, as_of,
  existing_candidate_terms=(), nominations=(), reference_pack=None) reads the
  document_terms generation bound in the C0 inputs, refuses a missing binding,
  derives each direct term's E0 fact origin from its sealed extraction record
  (deterministic and deferred are the canonical_extraction procedure; any
  other method is refused), refuses a reference pack that lets a
  non-canonical origin mint or stops a canonical one, runs
  compile_candidate_term_records and current_candidate_terms_as_of
  unchanged, and re-proves every candidate closed with
  assert_closed_candidate_term: exact closed authority block, no instrument
  identity, resolution or quantity key at any depth, candidate_term_id equal
  to the digest of its record, logical_candidate_term_id equal to the digest
  of its source slot. External proposals (llm_proposed_span,
  llm_interpretation, issuer_assertion, model_prose, an unknown origin, and a
  bare claim of canonical_extraction or adjudicated_gold) never enter the
  compile; each returns a TermRefusal with an explicit reason, and the
  candidate ledger digest is identical with or without them. The result is a
  CandidateIntegration carrying the full append-only ledger, the as_of view,
  the C0 instrument_candidate_terms GenerationBinding (support mirrored from
  the direct generation, artifact_sha256 over the as_of view), a C0
  CandidateBundle for I0, origins, refusals and a CalculationReceipt. An
  unsupported or unbuilt direct generation yields no candidates and says so;
  it is never read as an empty supported ledger.
rationale: >
  The candidate compiler already holds the identity law that A04 needs: the
  occurrence identity is a digest of the direct term's logical slot
  (manifest, fee-table row, term) plus the mapping version, with no clock and
  no legacy key, and the version identity is minted once and survives
  re-observation because the direct compiler itself returns identical rows
  for identical bytes. What was missing was the accepted-input boundary (C0
  bindings and support), the A09 origin check against the E0 reference pack,
  and a belt that refuses a candidate widened after compile. Building those
  around the sealed compilers keeps one identity law; a second compiler or a
  re-keyed projection would have created the resurrected-identity defect the
  W1 work removed. Joining a repeated exhibit across filings is identity
  resolution and belongs to I0 on explicit evidence, so T0 keeps both
  occurrences distinct even when their normalized values are identical.
alternatives:
  - option: Re-key candidates for downstream use by issuer, security title and term
    why_not: That is a fuzzy join by name; A08 forbids it and a later filing of the same exhibit would collapse into the earlier occurrence.
  - option: Let a nomination carrying canonical_extraction or adjudicated_gold enter the compile
    why_not: A canonical fact enters only through the sealed direct-term procedure or a reference-pack-pinned gold fixture; a claim of origin is not the procedure, so A09 would be decided by the proposer.
  - option: Rebuild the direct ledger and re-compile candidates from scratch on each run
    why_not: A rebuilt ledger mints new direct version ids; the candidate compiler fails closed against existing candidates instead of re-minting, which is the A04 behaviour T0 pins rather than works around.
  - option: Fork or widen the C0 contract key filter locally so prophet_authority passes
    why_not: The seat is the single writer of issuer_state_contracts.py; the exemption landed there as PR #9263 by name only, with the value pinned to literal false.
evidence:
  - engine/capital_structure/term_integration.py (integrate_candidate_terms, assert_closed_candidate_term, direct_term_origin, refuse_nomination)
  - tests/test_capital_structure_term_integration.py (A04 rerun, re-observation, clock independence, non-retroactivity and rebuilt-ledger refusal; A08 repeated exhibit in a second filing; A09 nominations, pack poisoning and tampered extraction; closed-boundary belt; support and binding discipline)
  - engine/capital_structure/instrument_candidates.py (logical_candidate_term_id_for, candidate_term_id_for, compile_candidate_term_records, current_candidate_terms_as_of)
  - config/capital_structure_reference_pack.v1.json fact_origins (canonical_extraction and adjudicated_gold true; the four non-canonical origins false)
  - PR #9263 (C0 exempts prophet_authority by name with value literal false, so compiled rows bind through CandidateBundle and CapitalInputs)
affects:
  - engine/capital_structure/term_integration.py
  - tests/test_capital_structure_term_integration.py
  - masterplan tasks I0 (consumes CandidateIntegration.candidate_bundle()), I1 and X0 (inherit the occurrence identity)
confidence: high
reversibility: easy
decided_by: opus-suborchestrator-o1-under-fable-meta-ceo-a9559a4c
decided_at: 2026-10-14
review_by: 2026-11-14
---

# T0: accepted-input candidate integration

The candidate boundary stays closed. T0 adds the accepted-input binding, the E0
fact-origin check and a post-compile closure belt around the sealed compilers, and
mints no instrument, quantity or join.
