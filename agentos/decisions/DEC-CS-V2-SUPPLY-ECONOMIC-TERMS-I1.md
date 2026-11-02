---
key: CS-V2-SUPPLY-ECONOMIC-TERMS-I1
question: >
  Masterplan task I1 (research/capital_structure/e2e_20261013/MASTERPLAN.md
  §13; acceptance rows A19, A23, A24 and A25) must turn resolved instruments
  into supply and cash consequences: fixed-price, pre-funded and cashless
  warrant exercise, debt conversion, and resale of already outstanding shares.
  I0 resolves instrument identity but its Instrument record carries no
  economic terms (no exercise price, ratio, cap or notice period), T0 keeps
  term observations pre-instrument, and document_terms.py is sealed. Where do
  economic terms live, how do they reach an instrument without letting a
  model or a form mint them, and how is supply evaluated without summing
  unlike quantities?
answer: >
  Three layers, each with one owner. (1) C0 2.1.0 adds an EconomicTerm record
  and an optional Instrument.economic_terms tuple; an instrument with no terms
  serialises byte-identically to 2.0.0, so every existing digest holds. Two
  input families are registered: capital_structure.instrument_economic_term.v1
  (pre-instrument occurrences with exact decimals, byte-span evidence,
  extraction method and point-in-time fields, no identity keys) and
  capital_structure.instrument_term_binding.v1 (adjudicated-gold bindings of
  an occurrence to instrument_id_for(issuer_id, series_key), visible by
  decided_at and effective_at, with supersedes). (2)
  engine/capital_structure/instrument_economics.py attach_economic_terms
  admits only canonical_extraction and adjudicated_gold origins, attaches only
  to resolved outstanding or amended instruments, and turns disagreeing
  same-date values into one contradicted term rather than choosing. (3)
  engine/capital_structure/supply_scenarios.py evaluate_supply(instruments,
  basis, scenario) applies per-settlement rules (cash exercise issues n and
  raises n x K; cashless issues n(P-K)/P and raises nothing; pre-funded issues
  n and raises only the unpaid residual; conversion issues principal/C and
  raises nothing; resale issues nothing and raises nothing for the issuer) and
  fills the four C0 SupplyEnvelope components separately, never summing them.
  A pre-split term is stale unless a post-split term is bound (no universal
  split factor); notice periods and ownership caps limit what a scenario can
  execute while the full claim stays in as_converted_claims. Any missing,
  contradicted or formula term is a named Unknown, never 0 or unbounded. A
  deterministic warrant-term extractor (I1b) produces real occurrences from
  retained filing bytes as a separate lane; it defers on ambiguity and never
  reads a Rule 457(g) fee-table price as an exercise price.
rationale: >
  The errors I1 exists to prevent are additive and inferential: counting
  resale-registered shares as new supply or issuer cash (A23), treating a
  cashless or conversion exercise as if it raised cash, counting pre-funded
  money twice (A24), dropping a capped claim from the overhang (A25), or
  scaling every term by a split ratio (A19). Keeping terms as evidence-bound
  records attached to an already resolved identity means a model cannot mint a
  term (A09, L120, L444), and keeping the four components separate is the only
  way L78's "never sum into fully diluted" can be checked. Making
  economic_terms optional and omitted when empty keeps C0's frozen digests
  stable for every record already in flight.
alternatives:
  - option: Add the terms to I0's Instrument resolution directly
    why_not: I0 is identity only and accepted; terms change over time (resets,
      amendments) and need their own point-in-time and contradiction rules.
  - option: Extend the sealed document_terms.py parser
    why_not: It is sealed at 1.1.0; a new extractor emits a new record family.
  - option: Let S0 compute supply from raw term observations
    why_not: S0 is the assembler; supply rules would then live beside
      unrelated assembly code and be re-implemented by C2 and G0.
  - option: A resale ROUTE_KIND in FinancingScenario
    why_not: Resale is not an issuer action; making it selectable invites
      counting it as issuance or proceeds.
  - option: Apply the corporate-action ratio to every pre-split term
    why_not: A19 and L102; contracts adjust differently and the evidence must
      say so.
evidence:
  - research/capital_structure/e2e_20261013/MASTERPLAN.md lines 78, 86, 98, 100, 102, 120, 122, 150, 172, 444 and §15 rows A19, A23-A25 (PR #9115 @93c82c90)
  - engine/capital_structure/issuer_state_contracts.py (Instrument, InstrumentSet, FinancingScenario, ActionSelection, SupplyEnvelope, CashEffect, _plain)
  - contracts/capital_structure_state.v2.schema.json $defs.instrument
  - engine/capital_structure/instrument_resolution.py (instrument_id_for, IDENTITY_FACT_ORIGIN)
  - engine/capital_structure/term_integration.py (INSTRUMENT_IDENTITY_KEYS, direct_term_origin)
affects:
  - WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2
  - engine/capital_structure/issuer_state_contracts.py
  - contracts/capital_structure_state.v2.schema.json
  - engine/capital_structure/instrument_economics.py
  - engine/capital_structure/supply_scenarios.py
  - masterplan tasks I2, X0, C2 and S0 (consume these records; never re-derive supply)
confidence: high
reversibility: costly
decided_by: fable-meta-ceo-a9559a4c
decided_at: 2026-10-14
---

# Economic terms are evidence records; supply is four separate quantities (I1)

Instrument economic terms are canonical or gold records bound to an already
resolved instrument. Supply is evaluated per settlement kind into four
separate components and per-action cash effects, with named unknowns where
evidence is missing. Resale moves no shares and no issuer cash.
