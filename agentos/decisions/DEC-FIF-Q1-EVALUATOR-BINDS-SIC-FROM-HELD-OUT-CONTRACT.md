---
key: FIF-Q1-EVALUATOR-BINDS-SIC-FROM-HELD-OUT-CONTRACT
question: >
  Where does the Q1 held-out evaluator take the issuer SIC that specialist-pack
  applicability (PK04 revenue, PK11 bank, PK12 biotech) needs, when the staged
  per-filing SEC submissions witness carries no sic key?
answer: >
  From the committed held-out contract first. tests/fixtures/fundamental_forensics_held_out/held_out_contract.json
  carries a reviewed per-issuer sic and a sic_source witness block (capture path
  into tests/fixtures/fundamental_forensics/five_issuer_submissions/, SIC
  description) for all five issuers; the evaluator binds issuer_sic from the
  contract row keyed by canonical CIK with sic_source "held_out_contract", falls
  back to the staged witness ("sec_submissions") only when the contract has no
  digit SIC, and records the binding order in each report's provenance. No pack,
  label, seal, package manifest or stage file changes.
rationale: >
  In the first Q1 generation every trial carried sic_source=unbound, so PK04/PK11/
  PK12 abstained issuer_class_unknown on every filing and produced zero emissions:
  three packs were never measured for a reason that was neither a pack defect nor
  a label defect. The contract is already the evaluator's own reviewed input for
  entity identity; its SIC witness is the same public EDGAR submissions record the
  packs would read in production. Binding from it is the Q1 operator's own
  contract, which is why the change needs neither a pack lane nor a labeler.
alternatives:
  - option: Add a sic key to the staged sec_submissions_witness.json files
    why_not: The stage is seat-owned and read-only after capture; rewriting it would need a new capture lane for a value the committed contract already carries.
  - option: Let PK04/PK11/PK12 accept an issuer-class assertion from the package manifest
    why_not: Changes pack semantics and a frozen pack contract to work around an evaluator input gap; the A37 record names this as the non-preferred route.
evidence:
  - "scripts/fif_held_out_evaluate.py::_witness_sic reads witness['sic']; staged witnesses carry only acceptanceDateTime/accessionNumber/filingDate/form/primaryDocument/reportDate/source_path/source_url (verified on the ubuntu2 replica, 2026-10-31)"
  - "held_out_contract.json issuers: AAPL 3571 industrial, SNOW 7372 software, CAT 3531 industrial, BAC 6021 bank, GOOGL 7370 software, each with sic_source.capture_path"
  - "Build lane fif-evalsic-20261031-r2 (ubuntu0, base 594a7429) implements the binding plus the E1-3 duplicate-target visibility; independent fabric review follows before merge"
affects:
  - WS:FINANCIAL-INTELLIGENCE-FABRIC
  - scripts/fif_held_out_evaluate.py
  - tests/test_fundamental_forensics_q1_held_out_evaluate.py
confidence: high
reversibility: easy
decided_by: FIF Meta-CEO seat 96dc937a (Fable)
decided_at: 2026-10-31
---

The PK12/PK05 `form_outside_pack_forms` abstentions on labelled 10-Qs remain a
separate scope question for the packs' frozen contracts; this decision does not
touch them.
