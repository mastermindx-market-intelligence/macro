---
key: FIF-Q1-EVALUATOR-ENVELOPE-SIC-SOURCE-FOLLOWS-PRODUCTION-RESOLVER
question: >
  The second Q1 held-out generation produced zero predictions because the
  evaluator (after #10310) passes its SIC binding-route label
  "held_out_contract" into PackInput.sic_source and the frozen pack-envelope
  contract refuses it (applicability.sic_source enum: sec_submissions, dei,
  unbound, null). Widen the frozen enum, or change the evaluator?
answer: >
  Change the evaluator; never the frozen envelope. The evaluator separates the
  binding ROUTE from the envelope SOURCE exactly as the production coverage
  resolver already does (engine/fundamental_forensics/coverage_manifest.py,
  _SIC_SOURCE_RESOLVED = "sec_submissions"): a SIC bound from a held-out
  contract issuer row — whose sic_source.capture_path is the issuer's captured
  SEC submissions document — rides in the envelope as "sec_submissions"; an
  unbound SIC rides as "unbound". The report note records both sic_binding
  (held_out_contract | sec_submissions | unbound) and sic_source (the envelope
  value). An end-to-end test runs the real produce_pack with a contract-bound
  SIC and asserts the envelope validates. This is a seat defect repair of
  #10310 with its own independent review; it amends
  DEC:FIF-Q1-SECOND-GENERATION-SCOPE only in that the repaired evaluator lands
  on main before the generation-two lane re-runs — the lane still never edits
  the evaluator, the labels, the seal or the 0.80 floor.
rationale: >
  The envelope contract is a shipped production surface consumed by the API and
  Excel layers; widening its closed vocabulary for a research-side route label
  would change the production contract to describe where a research harness
  looked, not where the SIC came from. The held-out contract's SIC provenance is
  the same kind of document the production resolver labels sec_submissions, so
  the production label is the truthful envelope value and the route belongs in
  the evaluator's own report. The vacuous zero-prediction run was correctly not
  committed as a measurement.
alternatives:
  - option: Extend the frozen enum with held_out_contract
    why_not: Edits a FROZEN production contract to carry a research-harness route label; every consumer would see a value that does not name a source document.
  - option: Pass sic_source=None with the bound SIC
    why_not: Hides real provenance; null is reserved for packs that never bound a SIC.
  - option: Let the lane patch the evaluator inside the generation-two run
    why_not: DEC:FIF-Q1-SECOND-GENERATION-SCOPE forbids the measuring lane from editing the evaluator; a repair must land on main under its own review first.
evidence:
  - "Lane fif-heldout-eval2-20261031-r2 return: every produce_pack raised SpecialistPackError 'invalid pack result: applicability.sic_source: held_out_contract is not one of [sec_submissions, dei, unbound, None]'; 55/55 pairs refused; nothing committed"
  - "contracts/specialist_pack_result.v1.schema.json line 116 (closed enum, unchanged since #8964)"
  - "engine/fundamental_forensics/coverage_manifest.py lines 198-207 (production resolver labels a contract-resolved SIC sec_submissions)"
  - "tests/fixtures/fundamental_forensics_held_out/held_out_contract.json issuer rows: sic + sic_source.capture_path = tests/fixtures/fundamental_forensics/five_issuer_submissions/CIK<10>.json"
affects:
  - WS:FINANCIAL-INTELLIGENCE-FABRIC
  - scripts/fif_held_out_evaluate.py
  - research/financial_intelligence_fabric/reports/q1_held_out_20261031_g2/
confidence: high
reversibility: easy
decided_by: "FIF Meta-CEO seat 96dc937a (Fable)"
decided_at: 2026-10-31
related:
  - DEC:FIF-Q1-EVALUATOR-BINDS-SIC-FROM-HELD-OUT-CONTRACT-20261031
  - DEC:FIF-Q1-SECOND-GENERATION-SCOPE
  - DEC:FIF-PACK-PATTERN-REPINS-ARE-DIGEST-ONLY
---
