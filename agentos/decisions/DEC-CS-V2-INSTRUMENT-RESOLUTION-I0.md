---
key: CS-V2-INSTRUMENT-RESOLUTION-I0
question: >
  Masterplan task I0 (research/capital_structure/e2e_20261013/MASTERPLAN.md,
  acceptance rows A04, A08, A09; deps T0 and C0) must resolve supported
  series/tranche identity, supersession and retirement from explicit
  evidence while ambiguous candidates remain unresolved, behind the frozen C0
  interface resolve_instruments(CandidateBundle, ResolutionInputs, as_of) ->
  InstrumentSet. What mints an instrument, what is its identity, what joins
  a repeated or amended exhibit, and what does ambiguity produce?
answer: >
  engine/capital_structure/instrument_resolution.py (version
  capital-structure-instrument-resolution/1.0.0). Only an owner decision
  record (schema capital_structure.instrument_resolution_decision.v1, closed
  key set, decision_id = stable_id("instrument-decision", every other field))
  mints, amends or retires. Three methods: supported_identity founds one
  owner-assigned series_key and binds named logical_candidate_term_ids;
  amendment_join binds named later terms and supersedes named bound terms by
  explicit {superseded, by} pairs; retirement retires the series and binds
  nothing. instrument_id = stable_id("instrument", {issuer_id, series_key}),
  so it is clock-free and survives re-observation, correction, amendment and
  retirement. Only fact_origin adjudicated_gold may mint, and only while the
  E0 reference pack lets it; the four non-canonical origins,
  canonical_extraction (a parser reads terms, it does not adjudicate
  identity) and unknown origins are refused with explicit reasons and have
  no effect. A decision is visible when decided_at <= as_of and applies when
  effective_at <= as_of; a visible but not effective decision is pending and
  never retroactive. Any ambiguity (missing or conflicting founding,
  inconsistent class/kind, conflicting retirements, an amendment after
  retirement, an amendment or retirement effective before the founding, a candidate not visible or not observed, a candidate claimed
  by two series, re-binding a bound term, superseding an unbound term, or
  two current terms in the same term/title/classification slot) leaves the
  whole series unresolved; there is no partial or best-guess identity.
  Unresolved candidates are listed in InstrumentSet.unresolved_candidate_ids
  with reasons in ResolutionTrace, are never Instrument records, and never
  carry a quantity (outstanding stays None for every instrument in I0).
  Every visible candidate lands in exactly one of bound, superseded or
  unresolved.
rationale: >
  A08 forbids joining by name, strike or exhibit text, and the T0 boundary
  already proves a repeated exhibit in a later filing is genuinely identical
  in title, classification and value. Any resolver that reads candidate
  values would join it, so this one reads no values: identity, joins and
  supersession come only from adjudicated records naming occurrence ids.
  The slot check reads the term/title/classification slot only to refuse
  (two live copies of one term), never to join. Keying identity on an
  owner-assigned series key rather than on a candidate id keeps A04 exact:
  correcting or superseding a candidate never re-mints the instrument.
  Refusing canonical_extraction as an identity origin keeps the E0 pack law
  (canonical facts) separate from identity adjudication (an owner act).
alternatives:
  - option: Auto-join candidates with equal normalized title, classification and value across filings
    why_not: That is the A08 fuzzy join; the repeated-exhibit test proves both copies are byte-similar and must stay distinct until a decision binds or supersedes them.
  - option: Pick a winner among conflicting foundings by latest decided_at
    why_not: A silent override hides the conflict; an owner correction needs its own explicit supersession record, which a later contract ruling can add.
  - option: Emit unresolved candidates as Instrument records with status unresolved_candidate
    why_not: The C0 Instrument requires kind and security_class_id, which an unresolved candidate does not have; inventing them would mint facts. The C0 unresolved_candidate_ids list carries them instead.
  - option: Let canonical_extraction decisions mint identity
    why_not: The pack makes canonical_extraction a fact origin for terms; identity is an adjudication, so only adjudicated_gold mints.
evidence:
  - engine/capital_structure/instrument_resolution.py (resolve_instruments, resolve_instrument_trace, build_decision, decision_id_for, instrument_id_for)
  - tests/test_capital_structure_instrument_resolution.py (41 tests; repeated/amended exhibit from the sealed fee-table fixture with a second filing derived in memory)
  - engine/capital_structure/issuer_state_contracts.py (CandidateBundle, ResolutionInputs, Instrument, InstrumentSet, INTERFACE_OWNERSHIP)
  - config/capital_structure_reference_pack.v1.json fact_origins
  - DEC:CS-V2-TERM-INTEGRATION-T0
affects:
  - engine/capital_structure/instrument_resolution.py
  - tests/test_capital_structure_instrument_resolution.py
  - masterplan tasks I1 and X0 (consume InstrumentSet and the occurrence-to-instrument partition)
confidence: high
reversibility: easy
decided_by: opus-suborchestrator-o3-under-fable-meta-ceo-a9559a4c
decided_at: 2026-10-14
review_by: 2026-11-14
---
